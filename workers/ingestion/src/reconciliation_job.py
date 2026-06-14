from src.domain.video_state import transition_video_state
from src.stream_client import interpret_stream_webhook


def reconcile_state(current_status: str, stream_state: dict) -> str:
    next_status = interpret_stream_webhook(stream_state)
    if current_status == "ingesting" and next_status == "ready_to_stream":
        current_status = transition_video_state(current_status, "processing")
    return transition_video_state(current_status, next_status)


async def run_reconciliation_job() -> dict:
    return {"scanned": 0}
