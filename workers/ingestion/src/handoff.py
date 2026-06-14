def build_handoff_payload(record: dict) -> dict:
    required_fields = ("id", "slug", "cloudflare_uid", "sync_status", "ready_to_stream_at")
    for field in required_fields:
        if not record.get(field):
            raise ValueError(f"Handoff record missing required field: {field}")

    if not record.get("cloudflare_iframe_url"):
        raise ValueError("Handoff record missing required field: cloudflare_iframe_url")

    if record["sync_status"] != "ready_to_stream":
        raise ValueError("Cannot emit handoff before ready_to_stream")

    return {
        "record_id": record["id"],
        "slug": record["slug"],
        "cloudflare_uid": record["cloudflare_uid"],
        "cloudflare_iframe_url": record["cloudflare_iframe_url"],
        "ready_to_stream_at": record["ready_to_stream_at"],
        "status": record["sync_status"],
    }
