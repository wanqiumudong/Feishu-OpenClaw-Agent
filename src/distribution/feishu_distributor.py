import hashlib
import json
import re
import subprocess
from collections.abc import Callable
from typing import Any

from config import Settings
from models import ActionPreview, DeliveryResult
from utils.io import write_jsonl


class FeishuDistributor:
    """Send MeetingFlow outputs to test Feishu objects through lark-cli."""

    def __init__(
        self,
        settings: Settings,
        *,
        runner: Callable[[list[str]], dict[str, Any]] | None = None,
    ):
        self.settings = settings
        self.runner = runner or self._run_json

    @property
    def dry_run(self) -> bool:
        return self.settings.dry_run or not self.settings.real_write

    def send_markdown(self, markdown: str, *, title: str = "MeetingFlow Test Result") -> DeliveryResult:
        self._require(self.settings.feishu_chat_id, "FEISHU_CHAT_ID")
        content = f"## {title}\n\n{markdown[:3500]}"
        args = [
            "im",
            "+messages-send",
            "--as",
            self.settings.feishu_send_as,
            "--chat-id",
            self.settings.feishu_chat_id,
            "--markdown",
            content,
            "--idempotency-key",
            self._idempotency_key("message", content),
        ]
        return self._execute("send_message", args)

    def create_task(self, action: ActionPreview) -> DeliveryResult:
        title = f"MeetingFlow Test - {action.title}"
        args = [
            "task",
            "+create",
            "--as",
            "user",
            "--summary",
            title,
            "--description",
            f"来源：{action.source.title}\n背景：{action.background}",
            "--idempotency-key",
            self._idempotency_key("task", title),
        ]
        if action.due_date and action.due_date != "待确认":
            args.extend(["--due", action.due_date])
        if self.settings.feishu_tasklist_id:
            args.extend(["--tasklist-id", self.settings.feishu_tasklist_id])
        return self._execute("create_task", args)

    def upsert_base_record(self, fields: dict[str, Any]) -> DeliveryResult:
        self._require(self.settings.feishu_base_token, "FEISHU_BASE_TOKEN")
        self._require(self.settings.feishu_base_table_id, "FEISHU_BASE_TABLE_ID")
        safe_fields = {"来源": "MeetingFlow Test", **fields}
        args = [
            "base",
            "+record-upsert",
            "--as",
            "user",
            "--base-token",
            self.settings.feishu_base_token,
            "--table-id",
            self.settings.feishu_base_table_id,
            "--json",
            json.dumps(safe_fields, ensure_ascii=False),
        ]
        return self._execute("upsert_base_record", args)

    def _execute(self, operation: str, args: list[str]) -> DeliveryResult:
        if self.dry_run:
            args = [*args, "--dry-run"]
        command = [self.settings.lark_cli_bin, *args]
        try:
            response = self.runner(args)
            result = DeliveryResult(
                operation=operation,
                dry_run=self.dry_run,
                command=self._masked_command(command),
                ok=True,
                response=self._safe_response(response),
            )
        except Exception as exc:
            result = DeliveryResult(
                operation=operation,
                dry_run=self.dry_run,
                command=self._masked_command(command),
                ok=False,
                error=self._mask_text(str(exc)),
            )
        self._append_log(result)
        return result

    def _run_json(self, args: list[str]) -> dict[str, Any]:
        command = [self.settings.lark_cli_bin, *args]
        try:
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            message = (exc.stderr or exc.stdout or "").strip()
            raise RuntimeError(message or "lark-cli command failed") from exc
        stdout = completed.stdout.strip()
        if not stdout:
            return {"ok": True}
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return {"ok": True, "stdout": stdout[:1000]}
        return payload if isinstance(payload, dict) else {"data": payload}

    def _append_log(self, result: DeliveryResult) -> None:
        log_path = self.settings.reports_dir / "real_run_log.jsonl"
        write_jsonl(
            log_path,
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

    def _masked_command(self, command: list[str]) -> list[str]:
        masked = []
        mask_next = False
        secret_flags = {"--chat-id", "--base-token", "--table-id", "--tasklist-id"}
        for part in command:
            if mask_next:
                masked.append(self._mask_value(part))
                mask_next = False
                continue
            masked.append(part)
            if part in secret_flags:
                mask_next = True
        return masked

    def _safe_response(self, response: dict[str, Any]) -> dict[str, Any]:
        text = json.dumps(response, ensure_ascii=False)
        text = self._mask_text(text)
        return json.loads(text)

    def _mask_text(self, text: str) -> str:
        for value in [
            self.settings.feishu_chat_id,
            self.settings.feishu_base_token,
            self.settings.feishu_base_table_id,
            self.settings.feishu_tasklist_id,
        ]:
            if value:
                text = text.replace(value, self._mask_value(value))
        text = re.sub(r"oc_[A-Za-z0-9]+", "<masked:chat_id>", text)
        text = re.sub(r"ou_[A-Za-z0-9]+", "<masked:user_id>", text)
        return text

    @staticmethod
    def _require(value: str, name: str) -> None:
        if not value:
            raise RuntimeError(f"Missing {name}.")

    @staticmethod
    def _idempotency_key(prefix: str, value: str) -> str:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:24]
        return f"meetingflow-{prefix}-{digest}"

    @staticmethod
    def _mask_value(value: str) -> str:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
        return f"<masked:{digest}>"
