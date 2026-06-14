"""Cloudflare Stream API helpers for creating imports and verifying webhooks.

All URL builders and request constructors are pure functions so they can be
unit-tested without hitting the network.  At call-site these are executed
using the Cloudflare Workers `fetch()` global.
"""

from urllib.parse import quote

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

STREAM_API_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}"
STREAM_WEBHOOK_SIGNATURE_HEADER = "Cloudflare-Stream-Webhook-Signature"

# ------------------------------------------------------------------
# Existing helpers (kept for backward compatibility)
# ------------------------------------------------------------------


def build_stream_import_payload(source_url: str) -> dict:
    """Build a minimal JSON body for a Stream import (used by handoff tests)."""
    return {"url": source_url}


def interpret_stream_webhook(payload: dict) -> str:
    """Interpret a Stream webhook or status response and return the canonical state.

    Returns one of: ``ready_to_stream``, ``processing``, ``error``.
    """
    if payload.get("readyToStream"):
        return "ready_to_stream"
    if payload.get("failed"):
        return "error"
    if payload.get("status") in {"error", "failed"}:
        return "error"
    return "processing"


def parse_stream_import_response(response: dict) -> dict:
    """Parse a Cloudflare Stream API response and return a standardized result.

    Parameters
    ----------
    response : dict
        The JSON response from the Stream import API call.

    Returns
    -------
    dict
        Keys: ``success``, ``cloudflare_uid`` (optional), ``stream_status`` (optional),
        ``error`` (optional), ``playback_url`` (optional).
    """
    if "errors" in response or response.get("success") is False:
        errors = response.get("errors", [])
        error_messages = "; ".join(
            err.get("message", str(err)) for err in errors
        )
        return {
            "success": False,
            "error": error_messages or "Stream import failed",
        }

    result = response.get("result", {})
    uid = result.get("uid", "")
    status = result.get("status", "unknown")
    playback = result.get("playback", {})
    playback_href = playback.get("href", "") if isinstance(playback, dict) else ""

    return {
        "success": True,
        "cloudflare_uid": uid,
        "stream_status": status,
        "playback_url": playback_href,
    }


# ------------------------------------------------------------------
# New HTTP request builders (pure)
# ------------------------------------------------------------------


def build_stream_import_request(
    source_url: str,
    *,
    account_id: str,
    api_token: str,
    slug: str = "",
) -> dict:
    """Build a complete HTTP request dict for creating a Stream import.

    The returned dict can be consumed by a thin ``fetch()`` adapter::

        import json
        req = build_stream_import_request(...)
        resp = fetch(req["url"], {
            "method": req["method"],
            "headers": req["headers"],
            "body": req["body_json"],
        })

    Parameters
    ----------
    source_url : str
        The R2-hosted video URL to import.
    account_id : str
        The Cloudflare account ID.
    api_token : str
        A Cloudflare API token with Stream write permissions.
    slug : str, optional
        Optional slug for metadata (used in Airtable lookup).

    Returns
    -------
    dict
        Keys: ``method``, ``url``, ``headers``, ``body`` (the JSON dict),
        ``body_json`` (the serialised string).
    """
    body = {
        "input_type": "upload",
        "source": {
            "type": "url",
            "url": source_url,
        },
    }
    if slug:
        body["metadata"] = {"slug": slug}

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    return {
        "method": "POST",
        "url": STREAM_API_BASE.format(account_id=account_id) + "/video",
        "headers": headers,
        "body": body,
        "body_json": __body_json(body),
    }


def build_stream_status_check_url(uid: str, account_id: str) -> str:
    """Build the URL for checking a specific Stream import's status.

    Parameters
    ----------
    uid : str
        The Cloudflare Stream UID.
    account_id : str
        The Cloudflare account ID.

    Returns
    -------
    str
        Full URL for the status check GET request.
    """
    encoded_uid = quote(uid, safe="")
    return STREAM_API_BASE.format(account_id=account_id) + f"/video/{encoded_uid}"


# ------------------------------------------------------------------
# Webhook verification
# ------------------------------------------------------------------


def verify_stream_webhook(
    headers: dict,
    body: bytes,
    secret: str = "",
) -> bool:
    """Verify the authenticity of a Cloudflare Stream webhook.

    Cloudflare Stream sends webhook signatures in the
    ``Cloudflare-Stream-Webhook-Signature`` header.

    For the MVP we check that:
    1. The signature header is present and non-empty.
    2. (Extended) If a ``secret`` is provided, verify the HMAC signature.

    Parameters
    ----------
    headers : dict
        The request headers from the incoming webhook.
    body : bytes
        The raw request body.
    secret : str, optional
        A shared secret if configured for HMAC verification.

    Returns
    -------
    bool
        True if the webhook is considered authentic.
    """
    signature = headers.get(STREAM_WEBHOOK_SIGNATURE_HEADER, "")
    if not signature:
        return False

    # MVP: header present check.
    # Extended: HMAC-SHA256(body, secret) == signature when secret is provided.
    if secret:
        import hmac
        import hashlib

        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False

    return True


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def __body_json(body: dict) -> str:
    """Serialise a body dict to JSON (local import to avoid stdlib at top-level)."""
    import json
    return json.dumps(body)
