"""Tests for airtable_client HTTP request builders and field mapping."""

from src.airtable_client import (
    build_airtable_status_patch,
    build_airtable_read_url,
    build_airtable_update_record_url,
    build_airtable_claim_payload,
    build_airtable_playback_update_payload,
    build_airtable_error_payload,
    AIRTABLE_FIELDS,
)


# -- URL builders --


def test_build_airtable_read_url_uses_base_id_and_table():
    url = build_airtable_read_url(
        "appTINXOFORMANATION",
        "Videos",
        "filterByFormula={Sync Status}='ready_for_ingest'",
    )
    assert "appTINXOFORMANATION" in url
    assert "Videos" in url
    assert "filterByFormula" in url


def test_build_airtable_read_url_with_empty_query():
    url = build_airtable_read_url("app123", "Videos")
    assert "app123" in url
    assert "Videos" in url
    assert "?" not in url


def test_build_airtable_read_url_encodes_table_name():
    url = build_airtable_read_url("app123", "Video Records", "filter=foo")
    assert "Video+Records" in url


def test_build_airtable_update_record_url_includes_record_id():
    url = build_airtable_update_record_url("app123", "Videos", "recAAA")
    assert "recAAA" in url
    assert "app123" in url
    assert "Videos" in url


# -- Field constants --


def test_airtable_fields_contains_expected_keys():
    assert "Sync Status" in AIRTABLE_FIELDS
    assert "Last Sync Error" in AIRTABLE_FIELDS
    assert "Cloudflare UID" in AIRTABLE_FIELDS


# -- Payload builders --


def test_build_airtable_status_patch_only_status():
    patch = build_airtable_status_patch("ingesting")
    assert patch == {"Sync Status": "ingesting", "Last Sync Error": ""}


def test_build_airtable_status_patch_with_error():
    patch = build_airtable_status_patch("error", "missing slug")
    assert patch == {
        "Sync Status": "error",
        "Last Sync Error": "missing slug",
    }


def test_build_airtable_status_patch_truncates_long_errors():
    patch = build_airtable_status_patch("error", "x" * 300)
    assert len(patch["Last Sync Error"]) == 200


def test_build_airtable_claim_payload():
    payload = build_airtable_claim_payload("rec123", "ingesting")
    assert payload == {
        "fields": {
            "Sync Status": "ingesting",
            "Last Sync Error": "",
        }
    }


def test_build_airtable_playback_update_payload():
    payload = build_airtable_playback_update_payload(
        cloudflare_uid="uidABC",
        playback_url="https://example.com/play/uidABC",
        iframe_url="https://iframe.example.com/embed/uidABC",
        sync_status="ready_to_stream",
        ready_to_stream_at="2026-06-07T12:00:00Z",
    )
    assert payload["fields"]["Cloudflare UID"] == "uidABC"
    assert payload["fields"]["Cloudflare Play URL"] == "https://example.com/play/uidABC"
    assert payload["fields"]["Cloudflare iframe URL"] == "https://iframe.example.com/embed/uidABC"
    assert payload["fields"]["Sync Status"] == "ready_to_stream"
    assert payload["fields"]["Ready to Stream At"] == "2026-06-07T12:00:00Z"


def test_build_airtable_playback_update_payload_without_optional_fields():
    payload = build_airtable_playback_update_payload(
        cloudflare_uid="uidABC",
        playback_url="https://example.com/play/uidABC",
        iframe_url="https://iframe.example.com/embed/uidABC",
    )
    assert "Ready to Stream At" not in payload["fields"]


def test_build_airtable_error_payload():
    payload = build_airtable_error_payload("Stream import rejected")
    assert payload["fields"]["Sync Status"] == "error"
    assert payload["fields"]["Last Sync Error"] == "Stream import rejected"
