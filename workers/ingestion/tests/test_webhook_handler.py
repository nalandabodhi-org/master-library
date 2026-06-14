"""Tests for the webhook handler."""

import asyncio

from src.webhook_handler import handle_webhook_payload


def test_handle_webhook_payload_marks_ready_to_stream():
    """Webhook with readyToStream should return ready_to_stream."""
    # handle_webhook_payload is now async (Stub 9)
    result = asyncio.run(handle_webhook_payload({"readyToStream": True}))
    assert result == {"next_status": "ready_to_stream"}


def test_handle_webhook_payload_marks_processing():
    """Webhook without readyToStream should return processing."""
    result = asyncio.run(handle_webhook_payload({"status": "downloading"}))
    assert result == {"next_status": "processing"}


def test_handle_webhook_payload_marks_error():
    """Webhook with failed flag should return error."""
    result = asyncio.run(handle_webhook_payload({"failed": True}))
    assert result == {"next_status": "error"}
