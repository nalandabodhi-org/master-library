from workers import Response, WorkerEntrypoint

from src.reconciliation_job import run_reconciliation_job
from src.trigger_job import run_trigger_job
from src.webhook_handler import handle_webhook_payload


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url
        if url.endswith("/webhooks/stream"):
            payload = await request.json()
            result = handle_webhook_payload(payload)
            return Response.json(result)

        return Response("Not found", status=404)

    async def scheduled(self, controller, env, ctx):
        if controller.cron == "*/5 * * * *":
            await run_trigger_job()
            return

        if controller.cron == "*/15 * * * *":
            await run_reconciliation_job()
            return
