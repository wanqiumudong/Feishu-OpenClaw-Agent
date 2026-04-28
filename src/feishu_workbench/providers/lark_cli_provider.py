import hashlib
import json
import subprocess
from collections.abc import Callable
from html.parser import HTMLParser
from typing import Any

from feishu_workbench.config import Settings
from feishu_workbench.models import DataBundle, KnowledgeItem
from feishu_workbench.providers.mock_provider import MockProvider


class LarkCliProvider:
    """Future provider boundary for real lark-cli integration.

    This provider only implements read-only document/minutes ingestion for test
    Feishu objects. It preserves the mock fallback and does not send messages,
    create tasks, or write Base records.
    """

    COMMAND_TEMPLATES = {
        "fetch_doc": "lark-cli docs +fetch --api-version v2 --as user --doc <doc_url_or_token> --format json",
        "search_docs": "lark-cli docs +search --query <keyword> --format json",
        "meeting_notes": "lark-cli vc +notes --as user --minute-tokens <minute_token> --format json",
        "send_message": "lark-cli im +messages-send --chat-id <chat_id> --text <text>",
        "create_task": "lark-cli task +create --summary <title> --due <due_time>",
        "upsert_base_record": "lark-cli base +record-upsert --app-token <token> --table-id <table>",
    }

    def __init__(
        self,
        settings: Settings,
        *,
        fallback: MockProvider | None = None,
        runner: Callable[[list[str]], dict[str, Any]] | None = None,
    ):
        self.settings = settings
        self.fallback = fallback or MockProvider(settings)
        self.runner = runner or self._run_json

    def load_bundle(self) -> DataBundle:
        bundle = self.fallback.load_bundle()
        docs = list(bundle.docs)
        minutes = list(bundle.minutes)

        if self.settings.feishu_doc_test_token:
            docs.append(self.fetch_doc(self.settings.feishu_doc_test_token))
        if self.settings.feishu_minutes_test_token:
            minutes.append(self.fetch_minutes(self.settings.feishu_minutes_test_token))

        return DataBundle(
            truth=bundle.truth,
            docs=docs,
            minutes=minutes,
            chat_messages=bundle.chat_messages,
            tasks=bundle.tasks,
            calendar_events=bundle.calendar_events,
            board_rows=bundle.board_rows,
        )

    def fetch_doc(self, token: str) -> KnowledgeItem:
        payload = self.runner(["docs", "+fetch", "--api-version", "v2", "--as", "user", "--doc", token, "--format", "json"])
        return self._item_from_payload(payload, kind="doc", token=token, source_prefix="docs")

    def fetch_minutes(self, token: str) -> KnowledgeItem:
        payload = self.runner(["vc", "+notes", "--as", "user", "--minute-tokens", token, "--format", "json"])
        return self._item_from_payload(payload, kind="minutes", token=token, source_prefix="minutes")

    def send_message(self, *_args, **_kwargs):
        raise NotImplementedError("Message delivery is not enabled in the read-only lark-cli provider.")

    def create_task(self, *_args, **_kwargs):
        raise NotImplementedError("Task creation is not enabled; use post-meeting task preview instead.")

    def _run_json(self, args: list[str]) -> dict[str, Any]:
        command = [self.settings.lark_cli_bin, *args]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"lark-cli executable not found: {self.settings.lark_cli_bin}. "
                "Install it or set LARK_CLI_BIN."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            message = stderr if stderr else "lark-cli command failed"
            raise RuntimeError(message) from exc

        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("lark-cli did not return JSON output") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("lark-cli JSON output must be an object")
        return parsed

    def _item_from_payload(
        self,
        payload: dict[str, Any],
        *,
        kind: str,
        token: str,
        source_prefix: str,
    ) -> KnowledgeItem:
        raw_content = self._first_text(payload, ("content", "text", "markdown", "raw_content", "body"))
        title = (
            self._first_text(payload, ("title", "name", "summary"))
            or self._title_from_markup(raw_content)
            or f"Feishu {kind} {self._safe_id(token)}"
        )
        content = self._content_text(payload)
        safe_id = f"feishu_{kind}_{self._safe_id(token)}"
        return KnowledgeItem(
            id=safe_id,
            title=title,
            kind=kind,
            content=content,
            source_path=f"feishu://{source_prefix}/{safe_id}",
            tags=["feishu", "readonly", kind],
            metadata={"provider": "lark_cli", "source_prefix": source_prefix},
        )

    @classmethod
    def _content_text(cls, payload: dict[str, Any]) -> str:
        direct = cls._first_text(payload, ("content", "text", "markdown", "raw_content", "body"))
        if direct:
            return cls._plain_text(direct)
        data = payload.get("data")
        if isinstance(data, dict):
            nested = cls._content_text(data)
            if nested:
                return nested
        blocks = payload.get("blocks") or payload.get("children")
        if isinstance(blocks, list):
            parts = [cls._stringify(value) for value in blocks]
            return cls._plain_text("\n".join(part for part in parts if part))
        for value in payload.values():
            if isinstance(value, dict):
                nested = cls._content_text(value)
                if nested:
                    return nested
        return cls._plain_text(cls._stringify(payload))

    @staticmethod
    def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        data = payload.get("data")
        if isinstance(data, dict):
            for key in keys:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        for value in payload.values():
            if isinstance(value, dict):
                nested = LarkCliProvider._first_text(value, keys)
                if nested:
                    return nested
        return ""

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            texts = [LarkCliProvider._stringify(item) for item in value.values()]
            return "\n".join(text for text in texts if text)
        if isinstance(value, list):
            texts = [LarkCliProvider._stringify(item) for item in value]
            return "\n".join(text for text in texts if text)
        return ""

    @staticmethod
    def _safe_id(token: str) -> str:
        return hashlib.sha1(token.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _title_from_markup(text: str) -> str:
        if "<" not in text or ">" not in text:
            return ""
        parser = _MarkupTextExtractor()
        parser.feed(text)
        return parser.title

    @staticmethod
    def _plain_text(text: str) -> str:
        if "<" not in text or ">" not in text:
            return text.strip()
        parser = _MarkupTextExtractor()
        parser.feed(text)
        return parser.text


class _MarkupTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._title_parts: list[str] = []
        self._in_title = False

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self._title_parts if part.strip()).strip()

    @property
    def text(self) -> str:
        lines = [part.strip() for part in self._parts if part.strip()]
        return "\n".join(lines).strip()

    def handle_starttag(self, tag: str, _attrs):
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str):
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._title_parts.append(text)
        self._parts.append(text)
