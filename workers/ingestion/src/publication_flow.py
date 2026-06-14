"""Publication flow - R2 URL to Cloudflare Stream import.

This module orchestrates creating a Stream import from an R2-sourced video,
parsing the response, and writing the ``cloudflare_uid`` and initial status
back to Airtable.

HTTP calls use the global ``fetch`` from Cloudflare Workers by default, but
accept an ``http_client`` parameter for test injection.
"""

import json
from urllib.parse import quote_plus

from src import stream_client as stream_client_mod


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _dispatch_http(
    url: str,
    options: dict,
    http_client: object = None,
) -> object:
    """Dispatch an HTTP request via the global ``fetch`` or an injectable client.

    Parameters
    ----------
    url : str
        Request URL.
    options : dict
        Request options (method, headers, body).
    http_client : optional
        An object with ``async def request(url, options)`` for testing.

    Returns
    -------
    object
        Response object with ``.ok``, ``.text()``, ``.json()``.
    """
    if http_client is not None:
        return http_client.request(url, options)
    return fetch(url, options)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def build_stream_import_request(
    source_url: str,
    *,
    account_id: str,
    api_token: str,
    slug: str = "",
) -> dict:
    """Build a Stream import request dict (delegates to stream_client).

    Kept here for backwards compatibility with existing tests that import
    directly from publication_flow.
    """
    return stream_client_mod.build_stream_import_request(
        source_url,
        account_id=account_id,
        api_token=api_token,
        slug=slug,
    )


parse_stream_import_response = stream_client_mod.parse_stream_import_response


async def execute_publication_flow(
    record,
    source_url: str,
    stream_request: dict | None,
    api_token: str,
    base_id: str,
    table_name: str,
    account_id: str,
    stream_client=None,
    airtable_client=None,
    http_client=None,
) -> dict:
    """Execute the full publication flow for a single video record.

    Steps:
    1. Create Stream import via HTTP POST
    2. Parse the Stream response
    3. Write ``cloudflare_uid`` and ``processing`` status to Airtable

    Parameters
    ----------
    record : VideoRecord or dict
        The validated video record being published.
    source_url : str
        The R2-hosted video URL.
    stream_request : dict | None
        Pre-built Stream import request (from ``build_stream_import_request``).
        Pass ``None`` to have this function build it.
    api_token : str
        Airtable API token (and Stream token if stream_client is None).
    base_id : str
        Airtable base ID.
    table_name : str
        Airtable table name.
    account_id : str
        Cloudflare account ID.
    stream_client : optional
        A Stream client with ``async def create_import(source_url, request)``
        for testing.
    airtable_client : optional
        An Airtable client with
        ``async def update_record(base_id, table, record_id, token, patch)``
        for testing.
    http_client : optional
        An injectable HTTP client for testing. If provided, takes precedence
        over both ``stream_client`` and the global ``fetch``.

    Returns
    -------
    dict
        Keys: ``success``, ``cloudflare_uid`` (on success),
        ``error`` (on failure).
    """
    # Step 1: Build or use provided Stream import request
    slug = (
        getattr(record, "slug", None)
        if hasattr(record, "slug")
        else record.get("slug", "")
    )
    if stream_request is None:
        request = build_stream_import_request(
            source_url,
            account_id=account_id,
            api_token=api_token,
            slug=slug,
        )
    else:
        request = stream_request

    # Step 2: Create Stream import
    if stream_client is not None:
        # Use injected stream client
        stream_response = await stream_client.create_import(source_url, request)
    else:
        # Direct HTTP call (Cloudflare Workers global fetch)
        resp = await _dispatch_http(request["url"], {
            "method": request["method"],
            "headers": request["headers"],
            "body": request.get("body_json", json.dumps(request.get("body", {}))),
        }, http_client=http_client)

        if not resp.ok:
            body = await resp.text()
            return {
                "success": False,
                "error": f"Stream import request failed ({resp.status}): {body}",
            }

        stream_response = await resp.json()

    # Step 3: Parse response
    parsed = parse_stream_import_response(stream_response)
    if not parsed["success"]:
        return parsed

    # Step 4: Write cloudflare_uid and processing status to Airtable
    if hasattr(record, "record_id"):
        record_id = record.record_id
    else:
        record_id = record.get("id", "unknown")

    if airtable_client is not None:
        # Use injected airtable client
        try:
            patch = {
                "fields": {
                    "Cloudflare UID": parsed["cloudflare_uid"],
                    "Sync Status": "processing",
                    "Last Sync Error": "",
                }
            }
            await airtable_client.update_record(
                base_id, table_name, record_id, api_token, patch
            )
        except Exception as exc:
            return {
                "success": False,
                "error": f"Airtable write failed: {exc}",
            }
    else:
        # Direct Airtable API call (Cloudflare Workers global fetch)
        encoded_table = quote_plus(table_name)
        url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}/{record_id}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        patch = {
            "fields": {
                "Cloudflare UID": parsed["cloudflare_uid"],
                "Sync Status": "processing",
                "Last Sync Error": "",
            }
        }

        resp = await _dispatch_http(url, {
            "method": "PATCH",
            "headers": headers,
            "body": json.dumps(patch),
        }, http_client=http_client)

        if not resp.ok:
            body = await resp.text()
            return {
                "success": False,
                "error": f"Airtable update failed ({resp.status}): {body}",
            }

    return {
        "success": True,
        "cloudflare_uid": parsed["cloudflare_uid"],
        "stream_status": parsed.get("stream_status", "processing"),
    }
