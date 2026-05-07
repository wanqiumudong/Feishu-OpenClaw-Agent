import hashlib
import json
import subprocess
from collections.abc import Callable
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from config import Settings
from models import DataBundle, KnowledgeItem
from providers.mock_provider import MockProvider


class LarkCliProvider:
    """Read-only Feishu provider backed by the official lark-cli."""

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

        for doc_url in self.settings.feishu_doc_urls:
            docs.append(self.fetch_doc(doc_url))
        for minute_token in self.settings.feishu_minute_tokens:
            minutes.append(self.fetch_minutes(minute_token))

        return DataBundle(
            truth=bundle.truth,
            docs=docs,
            minutes=minutes,
            chat_messages=bundle.chat_messages,
            tasks=bundle.tasks,
            calendar_events=bundle.calendar_events,
            board_rows=bundle.board_rows,
        )

    def get_event(self, event_id: str) -> dict[str, Any]:
        return self.fallback.get_event(event_id)

    def get_minutes(self, minutes_id: str) -> KnowledgeItem:
        for item in self.load_bundle().minutes:
            if item.id == minutes_id:
                return item
        return self.fallback.get_minutes(minutes_id)

    def fetch_doc(self, doc_url: str) -> KnowledgeItem:
        wiki_item = self._fetch_wiki_backed_item(doc_url)
        if wiki_item is not None:
            return wiki_item

        payload = self.runner(
            [
                "docs",
                "+fetch",
                "--api-version",
                "v2",
                "--as",
                "user",
                "--doc",
                doc_url,
                "--doc-format",
                "markdown",
                "--format",
                "json",
            ]
        )
        return self._item_from_payload(payload, kind="doc", token=doc_url, source_prefix="docs")

    def fetch_slides(self, slides_token: str) -> KnowledgeItem:
        payload = self.runner(
            [
                "slides",
                "xml_presentations",
                "get",
                "--as",
                "user",
                "--params",
                json.dumps({"xml_presentation_id": slides_token}, ensure_ascii=False),
                "--format",
                "json",
            ]
        )
        return self._item_from_payload(payload, kind="slides", token=slides_token, source_prefix="slides")

    def fetch_minutes(self, minute_token: str) -> KnowledgeItem:
        payload = self.runner(
            [
                "vc",
                "+notes",
                "--as",
                "user",
                "--minute-tokens",
                minute_token,
                "--format",
                "json",
            ]
        )
        return self._item_from_payload(payload, kind="minutes", token=minute_token, source_prefix="minutes")

    def _run_json(self, args: list[str]) -> dict[str, Any]:
        command = [self.settings.lark_cli_bin, *args]
        try:
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"lark-cli executable not found: {self.settings.lark_cli_bin}") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise RuntimeError(stderr or "lark-cli command failed") from exc

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("lark-cli did not return JSON output") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("lark-cli JSON output must be an object")
        return payload

    def _item_from_payload(
        self,
        payload: dict[str, Any],
        *,
        kind: str,
        token: str,
        source_prefix: str,
    ) -> KnowledgeItem:
        raw_content = self._raw_content_text(payload)
        content = self._plain_text(raw_content)
        title = (
            self._first_text(payload, ("title", "name", "summary"))
            or self._title_from_markup(raw_content)
            or f"Feishu {kind} {self._safe_id(token)}"
        )
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

    def _fetch_wiki_backed_item(self, url_or_token: str) -> KnowledgeItem | None:
        token = self._token_from_url(url_or_token, "wiki")
        if not token:
            return None

        payload = self.runner(
            [
                "wiki",
                "spaces",
                "get_node",
                "--as",
                "user",
                "--params",
                json.dumps({"token": token}, ensure_ascii=False),
                "--format",
                "json",
            ]
        )
        node = self._node_from_payload(payload)
        obj_type = str(node.get("obj_type", "")).strip()
        obj_token = str(node.get("obj_token", "")).strip()
        if not obj_token:
            raise RuntimeError("Wiki node did not return obj_token.")
        if obj_type == "docx":
            payload = self.runner(
                [
                    "docs",
                    "+fetch",
                    "--api-version",
                    "v2",
                    "--as",
                    "user",
                    "--doc",
                    obj_token,
                    "--doc-format",
                    "markdown",
                    "--format",
                    "json",
                ]
            )
            return self._item_from_payload(payload, kind="doc", token=obj_token, source_prefix="docs")
        if obj_type == "slides":
            return self.fetch_slides(obj_token)
        raise RuntimeError(f"Unsupported wiki object type '{obj_type}'. Current real-smoke supports docx and slides.")

    @staticmethod
    def _node_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
        node = payload.get("node")
        if isinstance(node, dict):
            return node
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("node"), dict):
            return data["node"]
        raise RuntimeError("Wiki get_node response did not contain node data.")

    @staticmethod
    def _token_from_url(value: str, segment: str) -> str:
        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        for index, part in enumerate(parts):
            if part == segment and index + 1 < len(parts):
                return parts[index + 1]
        return ""

    @classmethod
    def _content_text(cls, payload: dict[str, Any]) -> str:
        return cls._plain_text(cls._raw_content_text(payload))

    @classmethod
    def _raw_content_text(cls, payload: dict[str, Any]) -> str:
        direct = cls._first_text(payload, ("content", "text", "markdown", "raw_content", "body"))
        if direct:
            return direct
        data = payload.get("data")
        if isinstance(data, dict):
            nested = cls._raw_content_text(data)
            if nested:
                return nested
        blocks = payload.get("blocks") or payload.get("children")
        if isinstance(blocks, list):
            return "\n".join(cls._stringify(block) for block in blocks)
        return cls._stringify(payload)

    @staticmethod
    def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = payload.get(key)
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
            return "\n".join(text for text in (LarkCliProvider._stringify(item) for item in value.values()) if text)
        if isinstance(value, list):
            return "\n".join(text for text in (LarkCliProvider._stringify(item) for item in value) if text)
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
        return " ".join(part for part in self._title_parts if part).strip()

    @property
    def text(self) -> str:
        return "\n".join(part for part in self._parts if part).strip()

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
