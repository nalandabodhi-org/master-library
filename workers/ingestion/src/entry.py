"""Entry point for the ingestion Cloudflare Worker.

Routes scheduled cron jobs and the webhook HTTP endpoint.
"""

from workers import Response, WorkerEntrypoint

from src.reconciliation_job import run_reconciliation_job
from src.trigger_job import run_trigger_job
from src.webhook_handler import handle_webhook_payload
from src.stream_client import verify_stream_webhook


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url

        if url.endswith("/webhooks/stream"):
            # Bug 4: Verify webhook signature before processing
            raw_body = await request.bytes()
            # env is available on the worker instance
            if not verify_stream_webhook(
                dict(request.headers),
                raw_body,
                getattr(self, "env", None),
            ):
                return Response("Unauthorized", status=401)

            import json
            payload = json.loads(raw_body)
            result = handle_webhook_payload(payload, env=getattr(self, "env", None))
            return Response.json(result)

        return Response("Not found", status=404)

    async def scheduled(self, controller, env, ctx):
        # Stub 6: env is now passed to jobs
        if controller.cron == "*/5 * * * *":
            await run_trigger_job(env)
            return

        if controller.cron == "*/15 * * * *":
            await run_reconciliation_job(env)
            return
