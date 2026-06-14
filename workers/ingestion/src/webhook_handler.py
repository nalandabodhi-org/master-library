from src.stream_client import interpret_stream_webhook


def handle_webhook_payload(payload: dict) -> dict:
    return {"next_status": interpret_stream_webhook(payload)}
