import pytest

from src.handoff import build_handoff_payload


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (
            {
                "id": "rec123",
                "slug": "heart-sutra-part-1",
                "cloudflare_uid": "uid123",
                "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
                "ready_to_stream_at": "2026-06-07T12:00:00Z",
            },
            "sync_status",
        ),
        (
            {
                "slug": "heart-sutra-part-1",
                "cloudflare_uid": "uid123",
                "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
                "ready_to_stream_at": "2026-06-07T12:00:00Z",
                "sync_status": "ready_to_stream",
            },
            "id",
        ),
        (
            {
                "id": "rec123",
                "cloudflare_uid": "uid123",
                "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
                "ready_to_stream_at": "2026-06-07T12:00:00Z",
                "sync_status": "ready_to_stream",
            },
            "slug",
        ),
        (
            {
                "id": "rec123",
                "slug": "heart-sutra-part-1",
                "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
                "ready_to_stream_at": "2026-06-07T12:00:00Z",
                "sync_status": "ready_to_stream",
            },
            "cloudflare_uid",
        ),
        (
            {
                "id": "rec123",
                "slug": "heart-sutra-part-1",
                "cloudflare_uid": "uid123",
                "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
                "sync_status": "ready_to_stream",
            },
            "ready_to_stream_at",
        ),
    ],
)
def test_build_handoff_payload_requires_required_fields(record, message):
    with pytest.raises(ValueError, match=message):
        build_handoff_payload(record)


def test_build_handoff_payload_requires_playback_reference_url():
    with pytest.raises(ValueError, match="cloudflare_iframe_url"):
        build_handoff_payload(
            {
                "id": "rec123",
                "slug": "heart-sutra-part-1",
                "cloudflare_uid": "uid123",
                "ready_to_stream_at": "2026-06-07T12:00:00Z",
                "sync_status": "ready_to_stream",
            }
        )


def test_build_handoff_payload_requires_ready_to_stream():
    with pytest.raises(ValueError, match="ready_to_stream"):
        build_handoff_payload(
            {
                "id": "rec123",
                "slug": "heart-sutra-part-1",
                "cloudflare_uid": "uid123",
                "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
                "ready_to_stream_at": "2026-06-07T12:00:00Z",
                "sync_status": "processing",
            }
        )


def test_build_handoff_payload_returns_expected_fields():
    payload = build_handoff_payload(
        {
            "id": "rec123",
            "slug": "heart-sutra-part-1",
            "cloudflare_uid": "uid123",
            "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
            "ready_to_stream_at": "2026-06-07T12:00:00Z",
            "sync_status": "ready_to_stream",
        }
    )

    assert payload == {
        "record_id": "rec123",
        "slug": "heart-sutra-part-1",
        "cloudflare_uid": "uid123",
        "cloudflare_iframe_url": "https://iframe.videodelivery.net/uid123",
        "ready_to_stream_at": "2026-06-07T12:00:00Z",
        "status": "ready_to_stream",
    }
