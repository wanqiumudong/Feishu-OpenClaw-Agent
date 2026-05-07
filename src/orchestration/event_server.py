from typing import Any

from config import Settings
from distribution.card_renderer import render_feishu_card
from distribution.sdk_distributor import FeishuSdkDistributor
from orchestration.runtime import AgentRuntime


def normalize_event(payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("event", payload)
    message = event.get("message", {})
    content = message.get("content") or event.get("text") or payload.get("text") or ""
    return {
        "event_type": payload.get("type") or payload.get("event_type") or event.get("event_type") or "mock.message",
        "chat_id": message.get("chat_id") or payload.get("chat_id", ""),
        "user_id": event.get("sender", {}).get("sender_id", {}).get("open_id", "") if isinstance(event.get("sender"), dict) else "",
        "text": str(content),
    }


def workflow_from_event(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    text = event.get("text", "")
    if "会前" in text or "背景包" in text:
        return "pre_meeting", {"event": "go_no_go_review"}
    if "会后" in text or "行动项" in text:
        return "post_meeting", {"minutes": "go_no_go_minutes"}
    if "对账" in text or "推进表" in text:
        return "reconcile", {}
    if "全局" in text or "主题" in text:
        return "graphrag_global", {"question": text or "项目当前主要主题和风险是什么？"}
    return "graphrag_local", {"question": text or "Go/No-Go 灰度发布有哪些阻塞？"}


def handle_mock_event(settings: Settings, runtime: AgentRuntime, payload: dict[str, Any]) -> dict[str, Any]:
    event = normalize_event(payload)
    workflow, workflow_payload = workflow_from_event(event)
    trace = runtime.execute(workflow, workflow_payload)
    card = render_feishu_card(workflow, trace.output_markdown, [], title=f"MeetingFlow {workflow}")
    delivery = FeishuSdkDistributor(settings).send_card(card)
    return {
        "event": event,
        "workflow": workflow,
        "run_id": trace.run_id,
        "tool_calls": len(trace.tool_calls),
        "card_valid": delivery.ok,
        "dry_run": delivery.dry_run,
    }
