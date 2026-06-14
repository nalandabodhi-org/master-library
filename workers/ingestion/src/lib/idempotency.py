def build_ingest_lock_key(record_id: str) -> str:
    return f"video:{record_id}:ingest"
