"""Airtable API helpers for reading Video records and updating sync fields.

All URL builders and payload constructors are pure functions so they can be
unit-tested without hitting the network.  HTTP helpers use the Cloudflare
Workers `fetch()` global.
"""

import json
from urllib.parse import quote_plus

from src.lib.operator_errors import to_operator_error

# Field names used across every Airtable read/write
AIRTABLE_FIELDS = [
    "Sync Status",
    "Last Sync Error",
    "Cloudflare UID",
    "Cloudflare Play URL",
    "Cloudflare iframe URL",
    "Slug",
    "Assets",
    "Ready to Stream At",
]


# ------------------------------------------------------------------
# URL builders (pure)
# ------------------------------------------------------------------


def build_airtable_read_url(
    base_id: str,
    table_name: str,
    query: str = "",
) -> str:
    """Build an Airtable list-records GET URL.

    Parameters
    ----------
    base_id : str
        Airtable base ID (e.g. ``appTINXOFORMANATION``).
    table_name : str
        Airtable table/view name (will be URL-encoded).
    query : str, optional
        URL-encoded query string (e.g. ``filterByFormula=...``).

    Examples
    --------
    >>> url = build_airtable_read_url("app123", "Videos",
    ...                               "filterByFormula={Sync Status}='ready'")
    >>> "app123" in url and "Videos" in url
    True
    """
    encoded_table = quote_plus(table_name)
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}"
    if query:
        url += f"?{query}"
    return url


def build_airtable_update_record_url(
    base_id: str,
    table_name: str,
    record_id: str,
) -> str:
    """Build an Airtable patch-record URL for a specific record."""
    encoded_table = quote_plus(table_name)
    return f"https://api.airtable.com/v0/{base_id}/{encoded_table}/{record_id}"


# ------------------------------------------------------------------
# Payload builders (pure)
# ------------------------------------------------------------------


def build_airtable_status_patch(status: str, error: str | None = None) -> dict:
    """Return a minimal flat dict for status/last error fields.

    Unlike other payload builders this returns a flat dict (no ``fields`` wrapper)
    so it can be merged into a larger ``{"fields": {...}}`` patch at call-site.
    """
    return {
        "Sync Status": status,
        "Last Sync Error": to_operator_error(error) if error else "",
    }


def build_airtable_claim_payload(record_id: str, new_status: str) -> dict:
    """Payload for claiming a record (transitioning to ``ingesting``)."""
    return {
        "fields": {
            "Sync Status": new_status,
            "Last Sync Error": "",
        }
    }


def build_airtable_playback_update_payload(
    cloudflare_uid: str,
    playback_url: str,
    iframe_url: str,
    sync_status: str = "ready_to_stream",
    ready_to_stream_at: str = "",
) -> dict:
    """Payload written by the webhook handler when Stream confirms readiness."""
    fields: dict[str, str] = {
        "Cloudflare UID": cloudflare_uid,
        "Cloudflare Play URL": playback_url,
        "Cloudflare iframe URL": iframe_url,
        "Sync Status": sync_status,
    }
    if ready_to_stream_at:
        fields["Ready to Stream At"] = ready_to_stream_at
    return {"fields": fields}


def build_airtable_error_payload(message: str) -> dict:
    """Payload for marking a record as errored with a short operator message."""
    return {
        "fields": {
            "Sync Status": "error",
            "Last Sync Error": to_operator_error(message),
        }
    }


# ------------------------------------------------------------------
# HTTP helpers (use Cloudflare Workers `fetch` global)
# ------------------------------------------------------------------


def _build_airtable_headers(api_token: str) -> dict:
    """Build common Airtable request headers."""
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }


def _build_read_url_with_params(
    base_id: str,
    table_name: str,
    query: str = "",
    page_size: int = 100,
    use_fields: bool = True,
) -> str:
    """Build a read URL with ``page_size`` and ``AIRTABLE_FIELDS`` applied.

    Parameters
    ----------
    base_id : str
        Airtable base ID.
    table_name : str
        Table name.
    query : str, optional
        URL-encoded filter/query string.
    page_size : int, optional
        Records per page (default 100).
    use_fields : bool
        Whether to append ``fields[]`` query params.

    Returns
    -------
    str
        Fully-qualified GET URL.
    """
    parts = []
    if query:
        parts.append(query)

    # Design 11: Honour page_size
    if page_size:
        parts.append(f"pageSize={page_size}")

    # Design 11: Apply AIRTABLE_FIELDS
    if use_fields:
        for field in AIRTABLE_FIELDS:
            parts.append(f"fields[]={field.replace(' ', '+')}")

    query_string = "&".join(parts) if parts else ""
    return build_airtable_read_url(base_id, table_name, query_string)


async def read_airtable_records(
    base_id: str,
    table_name: str,
    api_token: str,
    query: str = "",
    page_size: int = 100,
) -> list[dict]:
    """Read records from Airtable, handling pagination internally.

    Parameters
    ----------
    base_id : str
        Airtable base ID.
    table_name : str
        Table name to read from.
    api_token : str
        Airtable API token.
    query : str, optional
        URL-encoded filter/query string.
    page_size : int, optional
        Max records per page (default 100, max 100).

    Returns
    -------
    list[dict]
        List of Airtable record dicts (each with ``id`` and ``fields``).
    """
    all_records: list[dict] = []
    # Design 11: Use helper that honours page_size + AIRTABLE_FIELDS
    url = _build_read_url_with_params(base_id, table_name, query, page_size)

    while url:
        resp = await fetch(url, {
            "method": "GET",
            "headers": _build_airtable_headers(api_token),
        })

        if not resp.ok:
            body = await resp.text()
            raise RuntimeError(
                f"Airtable read failed ({resp.status}): {body}"
            )

        data = await resp.json()
        all_records.extend(data.get("records", []))

        # Pagination
        url = ""
        if "offset" in data:
            # Bug 2: Compute separator from base_url (not from empty url)
            separator = "&" if "?" in url else "?"
            base_url = build_airtable_read_url(base_id, table_name, query)
            url = f"{base_url}{separator}offset={data['offset']}"

    return all_records


async def update_airtable_record(
    base_id: str,
    table_name: str,
    record_id: str,
    api_token: str,
    patch_fields: dict,
) -> dict:
    """Update an Airtable record with the given fields patch.

    Parameters
    ----------
    base_id : str
        Airtable base ID.
    table_name : str
        Table name.
    record_id : str
        The Airtable record ID (e.g. ``rec123``).
    api_token : str
        Airtable API token.
    patch_fields : dict
        The ``{"fields": {...}}`` payload to send.

    Returns
    -------
    dict
        The JSON response from Airtable (the updated record).
    """
    url = build_airtable_update_record_url(base_id, table_name, record_id)
    resp = await fetch(url, {
        "method": "PATCH",
        "headers": _build_airtable_headers(api_token),
        "body": json.dumps(patch_fields),
    })

    if not resp.ok:
        body = await resp.text()
        raise RuntimeError(
            f"Airtable update failed for {record_id} ({resp.status}): {body}"
        )

    return await resp.json()


async def update_airtable_sync_status(
    base_id: str,
    table_name: str,
    record_id: str,
    api_token: str,
    status: str,
    error: str | None = None,
) -> dict:
    """Convenience method to update only the Sync Status and Last Sync Error fields.

    Parameters
    ----------
    base_id : str
        Airtable base ID.
    table_name : str
        Table name.
    record_id : str
        The Airtable record ID.
    api_token : str
        Airtable API token.
    status : str
        New Sync Status value.
    error : str, optional
        Optional error message to write to Last Sync Error.

    Returns
    -------
    dict
        The JSON response from Airtable.
    """
    patch = build_airtable_status_patch(status, error)
    return await update_airtable_record(
        base_id, table_name, record_id, api_token,
        {"fields": patch}
    )
