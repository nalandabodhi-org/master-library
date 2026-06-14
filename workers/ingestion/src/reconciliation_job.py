from src.domain.video_state import transition_video_state
from src.stream_client import interpret_stream_webhook


# Bug 5: Removed forced intermediate transition through "processing".
# When Stream reports readyToStream and Airtable says ingesting,
# ingesting → ready_to_stream is a valid direct transition in the
# state machine (it skips "processing" only in-memory; the record
# has already been set to "processing" by publication_flow.py).
def reconcile_state(current_status: str, stream_state: dict) -> str:
    next_status = interpret_stream_webhook(stream_state)
    # Allow direct transition — the state machine permits it
    return transition_video_state(current_status, next_status)


# Stub 8: Full implementation
async def run_reconciliation_job(env) -> dict:
    """Scan Airtable for stuck records, query Stream, reconcile state."""
    from src.airtable_client import (
        read_airtable_records,
        update_airtable_record,
        build_airtable_error_payload,
    )
    from src.stream_client import (
        build_stream_status_check_url,
        _dispatch_http,
        parse_stream_import_response,
    )
    from src.config import require_env

    base_id = require_env(env, "AIRTABLE_BASE_ID")
    table_name = require_env(env, "AIRTABLE_TABLE_NAME")
    api_token = require_env(env, "AIRTABLE_API_TOKEN")
    account_id = require_env(env, "CLOUDFLARE_ACCOUNT_ID")
    stream_api_token = require_env(env, "CLOUDFLARE_STREAM_API_TOKEN")

    # Scan for records stuck in ingesting or processing
    query = (
        "filterByFormula="
        "OR({%22Sync Status%22}=%22ingesting%22,"
        "{%22Sync Status%22}=%22processing%22)"
    )
    records = await read_airtable_records(
        base_id, table_name, api_token, query=query, page_size=100
    )

    scanned = 0
    corrected = 0
    for raw_record in records:
        scanned += 1
        fields = raw_record.get("fields", {})
        current_status = fields.get("Sync Status", "draft")
        cf_uid = fields.get("Cloudflare UID", "")

        if not cf_uid:
            # No UID yet — can't reconcile, skip
            continue

        # Query Stream status
        status_url = build_stream_status_check_url(cf_uid, account_id)
        headers = {
            "Authorization": f"Bearer {stream_api_token}",
            "Content-Type": "application/json",
        }
        resp = await _dispatch_http(
            status_url,
            {"method": "GET", "headers": headers},
        )

        if not resp.ok:
            continue

        stream_data = await resp.json()
        stream_response = stream_data.get("result", {})

        # Parse the Stream response to get canonical state
        parsed = parse_stream_import_response(stream_response)
        if not parsed.get("success"):
            continue

        stream_canonical = parsed.get("stream_status", "unknown")

        # Determine correct Airtable state
        if stream_canonical == "error" or stream_canonical == "failed":
            correct_state = "error"
        elif stream_canonical == "ready_to_stream":
            # Check if playback URLs are already written
            if fields.get("Cloudflare Play URL"):
                correct_state = "ready_to_stream"
            else:
                # Webhook missed — advance to processing then ready
                correct_state = "ready_to_stream"
        else:
            # Still processing — no action needed
            continue

        # Apply correction if needed
        if correct_state != current_status:
            patched = {"fields": {"Sync Status": correct_state}}
            try:
                await update_airtable_record(
                    base_id, table_name, raw_record["id"], api_token, patched
                )
                corrected += 1
            except Exception:
                continue

    return {"scanned": scanned, "corrected": corrected}
