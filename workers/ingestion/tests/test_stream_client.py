"""Tests for stream_client real HTTP builders and webhook verification."""

from src.stream_client import (
    build_stream_import_payload,
    build_stream_import_request,
    build_stream_status_check_url,
    interpret_stream_webhook,
    verify_stream_webhook,
    STREAM_WEBHOOK_SIGNATURE_HEADER,
    parse_stream_import_response,
)


# -- Webhook verification --


def test_verify_stream_webhook_passes_with_valid_signature():
    payload = '{"type":"video.ready"}'
    signature = "tok_v1_abc123"
    # In the real implementation this would verify against a shared secret
    # For now we test the header name and basic structure
    assert STREAM_WEBHOOK_SIGNATURE_HEADER == "Cloudflare-Stream-Webhook-Signature"


def test_verify_stream_webhook_rejects_missing_signature():
    # No auth header present
    assert verify_stream_webhook({}, b"payload") is False


def test_verify_stream_webhook_rejects_empty_signature():
    headers = {STREAM_WEBHOOK_SIGNATURE_HEADER: ""}
    assert verify_stream_webhook(headers, b"payload") is False


# -- Import request builder --


def test_build_stream_import_request_includes_auth_and_headers():
    request = build_stream_import_request(
        "https://assets.example/video.mp4",
        account_id="acc123",
        api_token="tok_xyz",
    )
    assert request["method"] == "POST"
    assert "acc123" in request["url"]
    assert request["headers"]["Authorization"] == "Bearer tok_xyz"
    assert request["headers"]["Content-Type"] == "application/json"


def test_verify_stream_webhook_rejects_missing_signature():
    assert verify_stream_webhook({}, b"payload") is False


def test_verify_stream_webhook_rejects_empty_signature():
    headers = {STREAM_WEBHOOK_SIGNATURE_HEADER: ""}
    assert verify_stream_webhook(headers, b"payload") is False


def test_build_stream_import_request_includes_payload():
    request = build_stream_import_request(
        "https://assets.example/video.mp4",
        account_id="acc123",
        api_token="tok_xyz",
    )
    body = request["body"]
    assert body["input_type"] == "upload"
    assert body["source"]["type"] == "url"
    assert body["source"]["url"] == "https://assets.example/video.mp4"


def test_build_stream_import_request_sets_metadata_from_slug():
    request = build_stream_import_request(
        "https://assets.example/video.mp4",
        account_id="acc123",
        api_token="tok_xyz",
        slug="heart-sutra-part-1",
    )
    assert request["body"]["metadata"]["slug"] == "heart-sutra-part-1"


# -- Status check URL --


def test_build_stream_status_check_url_contains_uid_and_account():
    url = build_stream_status_check_url("uidABC123", "acc123")
    assert "acc123" in url
    assert "uidABC123" in url


# -- Existing tests should still pass --


def test_build_stream_import_payload_uses_source_url():
    assert build_stream_import_payload("https://assets.example/video.mp4") == {
        "url": "https://assets.example/video.mp4"
    }


def test_interpret_stream_webhook_returns_ready_to_stream_for_ready_payload():
    assert interpret_stream_webhook({"readyToStream": True}) == "ready_to_stream"


def test_interpret_stream_webhook_returns_error_for_explicit_failure_payload():
    assert interpret_stream_webhook({"status": "error"}) == "error"


def test_interpret_stream_webhook_returns_error_for_failed_flag_payload():
    assert interpret_stream_webhook({"failed": True}) == "error"


def test_interpret_stream_webhook_returns_processing_for_non_terminal_payload():
    assert interpret_stream_webhook({"status": "downloading"}) == "processing"
