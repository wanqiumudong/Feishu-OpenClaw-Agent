import json
import re
from dataclasses import asdict
from typing import Any

from config import Settings
from distribution.card_renderer import render_feishu_card
from distribution.sdk_distributor import FeishuSdkDistributor
from orchestration.runtime import AgentRuntime
from providers.lark_cli_provider import LarkCliProvider
from providers.mock_provider import MockProvider
from server.message_router import route_message


def handle_feishu_event(payload: dict[str, Any], headers: dict[str, str], settings: Settings) -> dict[str, Any]:
    challenge = payload.get("challenge")
    if isinstance(challenge, str) and challenge:
        return {"challenge": challenge}

    event_type = _event_type(payload)
    if event_type != "im.message.receive_v1":
        return {"status": "ignored", "event_type": event_type}

    event = _message_event(payload)
    routed = route_message(event["text"])
    runtime = AgentRuntime(settings, _build_provider(settings))
    trace = runtime.execute(routed.workflow, routed.payload)
    distributor = FeishuSdkDistributor(settings)

    reply_style = "text" if settings.reply_mode == "text" else routed.reply_style
    if reply_style == "card":
        card = render_feishu_card(routed.workflow, trace.output_markdown, [], title=f"MeetingFlow {routed.workflow}")
        delivery = distributor.send_card_to_chat(event["chat_id"], card)
    else:
        delivery = distributor.send_text(event["chat_id"], trace.output_markdown)

    return _mask_payload(
        {
            "status": "ok",
            "event_type": event_type,
            "workflow": routed.workflow,
            "reply_style": reply_style,
            "run_id": trace.run_id,
            "tool_calls": len(trace.tool_calls),
            "delivery": asdict(delivery),
        }
    )


def _event_type(payload: dict[str, Any]) -> str:
    header = payload.get("header")
    if isinstance(header, dict):
        value = header.get("event_type")
        if isinstance(value, str):
            return value
    value = payload.get("type") or payload.get("event_type")
    return value if isinstance(value, str) else ""


def _message_event(payload: dict[str, Any]) -> dict[str, str]:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    content = _content_text(message.get("content") or event.get("text") or payload.get("text") or "")
    sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
    sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
    return {
        "chat_id": str(message.get("chat_id") or payload.get("chat_id") or ""),
        "message_id": str(message.get("message_id") or payload.get("message_id") or ""),
        "sender_id": str(sender_id.get("open_id") or payload.get("user_id") or ""),
        "text": content,
    }


def _content_text(raw_value: Any) -> str:
    if isinstance(raw_value, dict):
        value = raw_value.get("text") or raw_value.get("content") or ""
        return str(value)
    if not isinstance(raw_value, str):
        return str(raw_value)
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value
    if isinstance(payload, dict):
        return str(payload.get("text") or payload.get("content") or raw_value)
    return raw_value


def _build_provider(settings: Settings):
    if settings.provider in {"feishu", "lark_cli"}:
        return LarkCliProvider(settings, fallback=MockProvider(settings))
    return MockProvider(settings)


def _mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False)
    text = re.sub(r"oc_[A-Za-z0-9]+", "<masked:chat_id>", text)
    text = re.sub(r"ou_[A-Za-z0-9]+", "<masked:user_id>", text)
    return json.loads(text)
