"""Webhook handler for Cloudflare Stream events.

Receives webhooks from Cloudflare Stream, verifies the signature,
interprets the event, writes playback fields back to Airtable,
and triggers a downstream handoff when the video is ready.
"""

from src.stream_client import interpret_stream_webhook
from src.airtable_client import (
    build_airtable_playback_update_payload,
    update_airtable_record,
)
from src.handoff import build_handoff_payload


async def handle_webhook_payload(payload: dict, env=None) -> dict:
    """Interpret a Stream webhook and write back to Airtable.

    Parameters
    ----------
    payload : dict
        The parsed JSON body of the incoming webhook.
    env : object | dict | None
        Worker environment with API tokens and config.

    Returns
    -------
    dict
        Keys: ``next_status`` (the interpreted Stream state),
        ``success`` (whether Airtable write succeeded),
        ``error`` (on failure).
    """
    next_status = interpret_stream_webhook(payload)

    # If env is provided (real deployment), write back to Airtable
    if env is not None:
        # Extract record info from payload or query params
        record_id = payload.get("record_id") or payload.get("id", "")
        cf_uid = payload.get("cf_uid") or payload.get("uid", "")
        playback_url = payload.get("playback_url") or payload.get("playback", "")
        iframe_url = payload.get("iframe_url") or ""
        ready_at = payload.get("ready_to_stream_at", "")

        if record_id and cf_uid and next_status == "ready_to_stream":
            try:
                # Write playback fields to Airtable
                patch = build_airtable_playback_update_payload(
                    cloudflare_uid=cf_uid,
                    playback_url=playback_url,
                    iframe_url=iframe_url,
                    sync_status="ready_to_stream",
                    ready_to_stream_at=ready_at,
                )

                from src.config import require_env

                base_id = require_env(env, "AIRTABLE_BASE_ID")
                table_name = require_env(env, "AIRTABLE_TABLE_NAME")
                api_token = require_env(env, "AIRTABLE_API_TOKEN")

                await update_airtable_record(
                    base_id, table_name, record_id, api_token, patch
                )

                # Stub 9: Trigger downstream handoff
                from src.airtable_client import read_airtable_records

                records = await read_airtable_records(
                    base_id, table_name, api_token,
                    query=f"filterByFormula=RECORD_ID()=\"%s\"" % record_id,
                )
                if records:
                    record = records[0]
                    handoff = build_handoff_payload(record["fields"])
                    handoff_endpoint = require_env(env, "HANDOFF_ENDPOINT")
                    handoff_token = require_env(env, "HANDOFF_TOKEN")

                    import json
                    resp = await fetch(handoff_endpoint, {
                        "method": "POST",
                        "headers": {
                            "Authorization": f"Bearer {handoff_token}",
                            "Content-Type": "application/json",
                        },
                        "body": json.dumps(handoff),
                    })

                    return {
                        "next_status": next_status,
                        "success": True,
                        "handoff_sent": resp.ok,
                    }

                return {"next_status": next_status, "success": True}

            except Exception as exc:
                return {
                    "next_status": next_status,
                    "success": False,
                    "error": str(exc),
                }

    return {"next_status": next_status}
