from src.webhook_handler import handle_webhook_payload


def test_handle_webhook_payload_marks_ready_to_stream():
    assert handle_webhook_payload({"readyToStream": True}) == {
        "next_status": "ready_to_stream"
    }
