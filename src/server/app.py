from fastapi import FastAPI, Request

from config import Settings
from orchestration.runtime import AgentRuntime
from providers.mock_provider import MockProvider
from server.event_handler import handle_feishu_event


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.default()
    app = FastAPI(title="MeetingFlow Agent Bot", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        runtime = AgentRuntime(app_settings, MockProvider(app_settings))
        inspection = runtime.inspect()
        return {
            "status": "ok",
            "provider": app_settings.provider,
            "dry_run": app_settings.dry_run or not app_settings.real_write,
            "registered_workflows": inspection["workflows"],
            "registered_tools": inspection["tools"],
        }

    @app.post("/feishu/events")
    async def feishu_events(request: Request) -> dict:
        payload = await request.json()
        headers = {key.lower(): value for key, value in request.headers.items()}
        return handle_feishu_event(payload, headers, app_settings)

    @app.post("/internal/run")
    async def internal_run(request: Request) -> dict:
        payload = await request.json()
        runtime = AgentRuntime(app_settings, MockProvider(app_settings))
        workflow = str(payload.get("workflow") or "graphrag_local")
        workflow_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        trace = runtime.execute(workflow, workflow_payload)
        return {
            "run_id": trace.run_id,
            "workflow": trace.workflow,
            "tool_calls": len(trace.tool_calls),
            "dry_run": trace.dry_run,
        }

    return app
