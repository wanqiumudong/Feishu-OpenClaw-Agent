import hashlib
import json
import re
from typing import Any

from config import Settings
from distribution.card_renderer import validate_card
from models import DeliveryResult, FeishuCard
from utils.io import write_jsonl


class FeishuSdkDistributor:
    """Optional SDK-backed distributor. It stays dry-run unless explicitly enabled."""

    def __init__(self, settings: Settings, *, client: Any | None = None):
        self.settings = settings
        self.client = client

    @property
    def dry_run(self) -> bool:
        return self.settings.dry_run or not self.settings.real_write

    def send_text(self, chat_id: str, text: str) -> DeliveryResult:
        content = text[:3500]
        if self.dry_run:
            result = DeliveryResult(
                operation="send_text",
                dry_run=True,
                command=["feishu-sdk", "im.message.create", "--chat-id", self._mask_value(chat_id), "--text", "<dry-run-text>"],
                ok=True,
                response={"chat_id": self._mask_value(chat_id), "text_chars": len(content)},
            )
            self._append_log(result)
            return result
        return self._send_message(chat_id=chat_id, msg_type="text", content={"text": content}, operation="send_text")

    def send_card_to_chat(self, chat_id: str, card: FeishuCard) -> DeliveryResult:
        errors = validate_card(card.card)
        if errors:
            result = DeliveryResult(
                operation="send_card",
                dry_run=self.dry_run,
                command=["feishu-sdk", "im.message.create", "--chat-id", self._mask_value(chat_id), "<card>"],
                ok=False,
                error=";".join(errors),
            )
            self._append_log(result)
            return result
        if self.dry_run:
            result = DeliveryResult(
                operation="send_card",
                dry_run=True,
                command=["feishu-sdk", "im.message.create", "--chat-id", self._mask_value(chat_id), "<dry-run-card>"],
                ok=True,
                response={"chat_id": self._mask_value(chat_id), "card_title": card.title, "source_count": card.source_count},
            )
            self._append_log(result)
            return result
        return self._send_message(chat_id=chat_id, msg_type="interactive", content=card.card, operation="send_card")

    def send_card(self, card: FeishuCard) -> DeliveryResult:
        errors = validate_card(card.card)
        if errors:
            return DeliveryResult(
                operation="send_card",
                dry_run=self.dry_run,
                command=["feishu-sdk", "im.message.create", "<card>"],
                ok=False,
                error=";".join(errors),
            )
        if self.dry_run:
            return DeliveryResult(
                operation="send_card",
                dry_run=True,
                command=["feishu-sdk", "im.message.create", "<dry-run-card>"],
                ok=True,
                response={"card_title": card.title, "source_count": card.source_count},
            )
        if self.client is None:
            return DeliveryResult(
                operation="send_card",
                dry_run=False,
                command=["feishu-sdk", "im.message.create", "<card>"],
                ok=False,
                error="SDK client is not configured.",
            )
        return DeliveryResult(
            operation="send_card",
            dry_run=False,
            command=["feishu-sdk", "im.message.create", "<card>"],
            ok=False,
            error="Real SDK card sending is intentionally gated for test tenants.",
        )

    def _send_message(self, *, chat_id: str, msg_type: str, content: dict[str, Any], operation: str) -> DeliveryResult:
        if not (self.settings.feishu_app_id and self.settings.feishu_app_credential):
            result = DeliveryResult(
                operation=operation,
                dry_run=False,
                command=["feishu-sdk", "im.message.create", "--chat-id", self._mask_value(chat_id), f"--type={msg_type}"],
                ok=False,
                error="FEISHU_APP_ID and FEISHU_APP_SECRET are required for real SDK delivery.",
            )
            self._append_log(result)
            return result
        if self.client is None:
            self.client = self._build_client()
        if self.client is None:
            result = DeliveryResult(
                operation=operation,
                dry_run=False,
                command=["feishu-sdk", "im.message.create", "--chat-id", self._mask_value(chat_id), f"--type={msg_type}"],
                ok=False,
                error="lark_oapi is not installed.",
            )
            self._append_log(result)
            return result
        try:
            response = self._sdk_create_message(chat_id, msg_type, content)
            ok = bool(getattr(response, "success", lambda: False)())
            error = "" if ok else self._mask_text(str(getattr(response, "msg", "") or getattr(response, "raw", "")))
            result = DeliveryResult(
                operation=operation,
                dry_run=False,
                command=["feishu-sdk", "im.message.create", "--chat-id", self._mask_value(chat_id), f"--type={msg_type}"],
                ok=ok,
                response={"chat_id": self._mask_value(chat_id), "msg_type": msg_type} if ok else {},
                error=error,
            )
        except Exception as exc:
            result = DeliveryResult(
                operation=operation,
                dry_run=False,
                command=["feishu-sdk", "im.message.create", "--chat-id", self._mask_value(chat_id), f"--type={msg_type}"],
                ok=False,
                error=self._mask_text(str(exc)),
            )
        self._append_log(result)
        return result

    def _build_client(self) -> Any | None:
        try:
            import lark_oapi as lark  # type: ignore
        except Exception:
            return None
        return lark.Client.builder().app_id(self.settings.feishu_app_id).app_secret(self.settings.feishu_app_credential).build()

    def _sdk_create_message(self, chat_id: str, msg_type: str, content: dict[str, Any]) -> Any:
        import lark_oapi as lark  # type: ignore
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody  # type: ignore

        body = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type(msg_type)
            .content(json.dumps(content, ensure_ascii=False))
            .uuid(self._idempotency_key(msg_type, json.dumps(content, ensure_ascii=False)))
            .build()
        )
        request = CreateMessageRequest.builder().receive_id_type("chat_id").request_body(body).build()
        return self.client.im.v1.message.create(request)

    def _append_log(self, result: DeliveryResult) -> None:
        write_jsonl(
            self.settings.reports_dir / "real_run_log.jsonl",
            [
                {
                    "operation": result.operation,
                    "dry_run": result.dry_run,
                    "command": result.command,
                    "ok": result.ok,
                    "error": result.error,
                }
            ],
            append=True,
        )

    def _mask_text(self, text: str) -> str:
        text = re.sub(r"oc_[A-Za-z0-9]+", "<masked:chat_id>", text)
        text = re.sub(r"ou_[A-Za-z0-9]+", "<masked:user_id>", text)
        for value in (self.settings.feishu_app_id, self.settings.feishu_app_credential):
            if value:
                text = text.replace(value, self._mask_value(value))
        return text

    @staticmethod
    def _idempotency_key(prefix: str, value: str) -> str:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:24]
        return f"meetingflow-{prefix}-{digest}"

    @staticmethod
    def _mask_value(value: str) -> str:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
        return f"<masked:{digest}>"
