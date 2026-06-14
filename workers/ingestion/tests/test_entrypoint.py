import asyncio
from types import SimpleNamespace

from workers import Response, WorkerEntrypoint

import src.entry as entry
from src.entry import Default


class FakeRequest:
    def __init__(self, url, payload=None, headers=None):
        self.url = url
        self._payload = payload
        self.headers = headers or {}

    async def json(self):
        return self._payload

    async def bytes(self):
        """Return the raw body bytes (used by HMAC verification)."""
        import json
        return json.dumps(self._payload).encode()


class FakeResponse:
    def __init__(self, body=None, status=200):
        self.body = body
        self.status = status
        self.kind = "plain"

    @staticmethod
    def json(body):
        response = FakeResponse(body=body, status=200)
        response.kind = "json"
        return response


def test_default_entrypoint_exposes_worker_handlers():
    assert Default.__bases__ == (WorkerEntrypoint,)
    assert Response.__module__ == "workers._workers"
    assert WorkerEntrypoint.__module__ == "workers._workers"
    assert hasattr(Default, "fetch")
    assert hasattr(Default, "scheduled")


def test_entrypoint_class_name_is_default():
    assert Default.__name__ == "Default"


def test_fetch_routes_stream_webhook_payload_to_handler(monkeypatch):
    payload = {"type": "video.ready"}
    handled_payloads = []

    def fake_handle_webhook_payload(body, env=None):
        handled_payloads.append(body)
        return {"next_status": "ready_to_stream"}

    # Also fake verify_stream_webhook to always pass
    def fake_verify(headers, body, secret=None):
        return True

    monkeypatch.setattr(entry, "Response", FakeResponse)
    monkeypatch.setattr(entry, "handle_webhook_payload", fake_handle_webhook_payload, raising=False)
    monkeypatch.setattr(entry, "verify_stream_webhook", fake_verify, raising=False)

    response = asyncio.run(
        Default.__new__(Default).fetch(FakeRequest("https://example.com/webhooks/stream", payload))
    )

    assert handled_payloads == [payload]
    assert response.kind == "json"
    assert response.body == {"next_status": "ready_to_stream"}
    assert response.status == 200


def test_fetch_returns_not_found_for_unknown_paths(monkeypatch):
    monkeypatch.setattr(entry, "Response", FakeResponse)

    response = asyncio.run(Default.__new__(Default).fetch(FakeRequest("https://example.com/other")))

    assert response.kind == "plain"
    assert response.body == "Not found"
    assert response.status == 404


def test_scheduled_routes_five_minute_cron_to_trigger_job(monkeypatch):
    calls = []

    async def fake_run_trigger_job(env=None):
        calls.append("trigger")

    monkeypatch.setattr(entry, "run_trigger_job", fake_run_trigger_job, raising=False)

    asyncio.run(
        Default.__new__(Default).scheduled(SimpleNamespace(cron="*/5 * * * *"), None, None)
    )

    assert calls == ["trigger"]


def test_scheduled_routes_fifteen_minute_cron_to_reconciliation_job(monkeypatch):
    calls = []

    async def fake_run_reconciliation_job(env=None):
        calls.append("reconciliation")

    monkeypatch.setattr(entry, "run_reconciliation_job", fake_run_reconciliation_job, raising=False)

    asyncio.run(
        Default.__new__(Default).scheduled(SimpleNamespace(cron="*/15 * * * *"), None, None)
    )

    assert calls == ["reconciliation"]
