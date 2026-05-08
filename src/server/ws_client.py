import json
from dataclasses import asdict
from typing import Any

import lark_oapi as lark
from lark_oapi.ws import Client as LarkWsClient

from config import Settings
from server.event_handler import handle_feishu_event


def build_message_payload(event: Any) -> dict[str, Any]:
    data = event.event
    message = data.message if data else None
    sender = data.sender if data else None
    sender_id = getattr(sender, "sender_id", None)
    return {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "message": {
                "chat_id": getattr(message, "chat_id", "") or "",
                "message_id": getattr(message, "message_id", "") or "",
                "content": getattr(message, "content", "") or "",
            },
            "sender": {
                "sender_id": {
                    "open_id": getattr(sender_id, "open_id", "") or "",
                    "user_id": getattr(sender_id, "user_id", "") or "",
                    "union_id": getattr(sender_id, "union_id", "") or "",
                }
            },
        },
    }


def build_event_handler(settings: Settings):
    def on_message(event) -> None:
        result = handle_feishu_event(build_message_payload(event), {}, settings)
        print(json.dumps(_log_result(result), ensure_ascii=False))

    return (
        lark.EventDispatcherHandler.builder(
            settings.feishu_encrypt_key,
            settings.feishu_verification_token,
        )
        .register_p2_im_message_receive_v1(on_message)
        .build()
    )


def start_ws_client(settings: Settings) -> None:
    if not settings.feishu_app_id or not settings.feishu_app_credential:
        raise RuntimeError("FEISHU_APP_ID and FEISHU_APP_SECRET are required.")
    handler = build_event_handler(settings)
    client = LarkWsClient(
        settings.feishu_app_id,
        settings.feishu_app_credential,
        log_level=lark.LogLevel.INFO,
        event_handler=handler,
    )
    print(
        json.dumps(
            {
                "status": "starting",
                "mode": "feishu_ws",
                "provider": settings.provider,
                "dry_run": settings.dry_run or not settings.real_write,
                "reply_mode": settings.reply_mode,
            },
            ensure_ascii=False,
        )
    )
    client.start()


def _log_result(result: dict[str, Any]) -> dict[str, Any]:
    delivery = result.get("delivery")
    if hasattr(delivery, "__dataclass_fields__"):
        result = dict(result)
        result["delivery"] = asdict(delivery)
    return {
        "status": result.get("status"),
        "workflow": result.get("workflow"),
        "reply_style": result.get("reply_style"),
        "run_id": result.get("run_id"),
        "tool_calls": result.get("tool_calls"),
        "delivery": result.get("delivery"),
    }
