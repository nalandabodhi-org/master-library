"""Tests for publication_flow - R2 URL to Stream import."""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from src.publication_flow import (
    execute_publication_flow,
    parse_stream_import_response,
    build_stream_import_request,
)


@dataclass
class FakeConfig:
    CLOUDFLARE_ACCOUNT_ID: str = "acc123"
    CLOUDFLARE_STREAM_API_TOKEN: str = "stream_token"


class FakeRecord:
    def __init__(self, record_id="rec123", slug="test-video", primary_asset=None):
        self.record_id = record_id
        self.slug = slug
        self.primary_asset = primary_asset or {"r2Key": "videos/test.mp4"}


class FakeStreamClient:
    def __init__(self, response=None):
        self.calls = []
        self.response = response or {
            "result": {
                "uid": "stream_uid_123",
                "status": "processing",
                "playback": {"href": "https://iframe.videodelivery.net/stream_uid_123"},
                "upload_url": "https://upload.stream.com/v1/uid123",
            }
        }

    async def create_import(self, source_url, request):
        self.calls.append((source_url, request))
        return self.response


class FakeAirtableClient:
    def __init__(self):
        self.updated = {}

    async def update_record(self, base_id, table_name, record_id, token, patch):
        self.updated[record_id] = patch
        return {"id": record_id, "fields": {"Cloudflare UID": "uid_123"}}


# -- build_stream_import_request --


def test_build_stream_import_request_uses_r2_url():
    """Should construct a Stream import request with the R2 source URL."""
    request = build_stream_import_request(
        "https://acc123.r2.cloudflarestorage.com/v1/public/videos/test.mp4",
        account_id="acc123",
        api_token="tok",
        slug="test-video",
    )

    assert request["method"] == "POST"
    assert "acc123" in request["url"]
    assert "stream/copy" in request["url"]
    assert request["headers"]["Authorization"] == "Bearer tok"
    assert request["headers"]["Content-Type"] == "application/json"
    assert request["body"]["url"] == "https://acc123.r2.cloudflarestorage.com/v1/public/videos/test.mp4"


def test_build_stream_import_request_includes_slug_metadata():
    """Should include the video slug in the request metadata."""
    request = build_stream_import_request(
        "https://acc123.r2.cloudflarestorage.com/v1/videos/test.mp4",
        account_id="acc123",
        api_token="tok",
        slug="heart-sutra",
    )

    assert request["body"]["meta"]["slug"] == "heart-sutra"


# -- parse_stream_import_response --


def test_parse_stream_import_response_extract_uid():
    """Should extract the Stream UID from a successful response."""
    response = {
        "result": {
            "uid": "stream_uid_123",
            "status": "processing",
        }
    }

    result = parse_stream_import_response(response)

    assert result["success"] is True
    assert result["cloudflare_uid"] == "stream_uid_123"
    assert result["stream_status"] == "processing"


def test_parse_stream_import_response_handles_error():
    """Should return failure when Stream API responds with error."""
    response = {
        "errors": [{"message": "Invalid source URL"}],
    }

    result = parse_stream_import_response(response)

    assert result["success"] is False
    assert "Invalid source URL" in result["error"]


# -- execute_publication_flow --


@pytest.mark.asyncio
async def test_execute_publication_flow_calls_stream_api():
    """Should create a Stream import and write cloudflare_uid to Airtable."""
    fake_stream = FakeStreamClient()
    fake_at = FakeAirtableClient()
    record = FakeRecord(record_id="rec123", slug="test-video")

    result = await execute_publication_flow(
        record,
        "https://acc123.r2.cloudflarestorage.com/v1/videos/test.mp4",
        {},  # stream_request (not used since we mock stream_client)
        "airtable_token",
        "appBase",
        "Videos",
        "acc123",
        stream_client=fake_stream,
        airtable_client=fake_at,
    )

    assert result["success"] is True
    assert result["cloudflare_uid"] == "stream_uid_123"
    assert "rec123" in fake_at.updated


@pytest.mark.asyncio
async def test_execute_publication_flow_returns_error_on_stream_failure():
    """Should return failure when Stream API rejects the import."""
    fake_stream = FakeStreamClient(
        response={
            "errors": [{"message": "Invalid source URL"}],
        }
    )

    result = await execute_publication_flow(
        FakeRecord(),
        "https://invalid.url/video.mp4",
        {},
        "tok",
        "appBase",
        "Videos",
        "acc123",
        stream_client=fake_stream,
    )

    assert result["success"] is False
    assert "Invalid source URL" in result["error"]
