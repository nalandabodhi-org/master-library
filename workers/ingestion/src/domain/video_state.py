ALLOWED_TRANSITIONS = {
    "draft": {"ready_for_ingest"},
    "ready_for_ingest": {"ingesting", "error"},
    "ingesting": {"processing", "ready_to_stream", "error"},
    "processing": {"ready_to_stream", "error"},
    "ready_to_stream": set(),
    "error": {"ready_for_ingest"},
}


def transition_video_state(current: str, next_state: str) -> str:
    allowed = ALLOWED_TRANSITIONS.get(current)
    if allowed is None:
        raise ValueError(f"Invalid transition: {current} -> {next_state}")

    if current == next_state:
        return current

    if next_state not in allowed:
        raise ValueError(f"Invalid transition: {current} -> {next_state}")
    return next_state
