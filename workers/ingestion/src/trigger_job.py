from src.domain.video_record import VideoRecord


def assert_eligible_for_ingest(record: VideoRecord) -> None:
    if record.sync_status != "ready_for_ingest":
        raise ValueError("Video is not ready_for_ingest")
    if not record.slug:
        raise ValueError("Video missing slug")
    if not record.primary_asset.get("r2Key"):
        raise ValueError("Video missing primary source asset")


async def run_trigger_job(env) -> dict:
    """Scan Airtable for ready_for_ingest records, validate, claim, and publish."""
    from src.airtable_client import (
        read_airtable_records,
        build_airtable_claim_payload,
        update_airtable_record,
        build_airtable_error_payload,
    )
    from src.eligibility import assert_eligible_for_ingest, normalize_video_record
    from src.publication_flow import execute_publication_flow
    from src.config import require_env

    base_id = require_env(env, "AIRTABLE_BASE_ID")
    table_name = require_env(env, "AIRTABLE_TABLE_NAME")
    api_token = require_env(env, "AIRTABLE_API_TOKEN")
    account_id = require_env(env, "CLOUDFLARE_ACCOUNT_ID")
    stream_api_token = require_env(env, "CLOUDFLARE_STREAM_API_TOKEN")
    r2_region = require_env(env, "R2_REGION")

    # Scan for ready_for_ingest records
    query = "filterByFormula={%22Sync Status%22}=%22ready_for_ingest%22"
    records = await read_airtable_records(
        base_id, table_name, api_token, query=query, page_size=100
    )

    scanned = 0
    for raw_record in records:
        scanned += 1
        try:
            record = normalize_video_record(raw_record)
            assert_eligible_for_ingest(record)
        except ValueError as exc:
            # Validation failure — mark error and move on
            try:
                error_payload = build_airtable_error_payload(str(exc))
                await update_airtable_record(
                    base_id, table_name, raw_record["id"], api_token, error_payload
                )
            except Exception:
                pass
            continue

        # Claim the record (set to ingesting)
        try:
            claim_payload = build_airtable_claim_payload(
                raw_record["id"], "ingesting"
            )
            await update_airtable_record(
                base_id, table_name, raw_record["id"], api_token, claim_payload
            )
        except Exception as exc:
            continue

        # Build R2 URL from the asset key
        r2_key = record.primary_asset.get("r2Key", "")
        source_url = f"https://{r2_key}.{r2_region}.cdn.r2.cloudflarestorage.com"

        # Execute publication flow
        result = await execute_publication_flow(
            record,
            source_url,
            stream_request=None,
            api_token=stream_api_token,
            base_id=base_id,
            table_name=table_name,
            account_id=account_id,
        )

        if not result.get("success"):
            # Write error back to Airtable
            try:
                error_payload = build_airtable_error_payload(
                    result.get("error", "Unknown error")
                )
                await update_airtable_record(
                    base_id, table_name, raw_record["id"], api_token, error_payload
                )
            except Exception:
                pass

    return {"scanned": scanned}
