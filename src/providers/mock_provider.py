from pathlib import Path
from typing import Any

from config import Settings
from models import DataBundle, KnowledgeItem
from utils.io import read_csv, read_json, read_jsonl, read_text


class MockProvider:
    """Local synthetic-data provider used by the bootstrap MVP."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def load_bundle(self) -> DataBundle:
        data_dir = self.settings.data_dir
        return DataBundle(
            truth=read_json(data_dir / "ground_truth" / "project_truth.json"),
            docs=self._load_markdown_items(data_dir / "docs", "doc"),
            minutes=self._load_markdown_items(data_dir / "minutes", "minutes"),
            chat_messages=read_jsonl(data_dir / "chats" / "project_chat.jsonl"),
            tasks=read_json(data_dir / "tasks" / "tasks.json"),
            calendar_events=read_json(data_dir / "calendar" / "events.json"),
            board_rows=read_csv(data_dir / "base" / "priority_board.csv"),
        )

    def get_event(self, event_id: str) -> dict[str, Any]:
        for event in self.load_bundle().calendar_events:
            if event["event_id"] == event_id:
                return event
        raise KeyError(f"Unknown event_id: {event_id}")

    def get_minutes(self, minutes_id: str) -> KnowledgeItem:
        for item in self.load_bundle().minutes:
            if item.id == minutes_id:
                return item
        raise KeyError(f"Unknown minutes_id: {minutes_id}")

    def _load_markdown_items(self, folder: Path, kind: str) -> list[KnowledgeItem]:
        items = []
        for path in sorted(folder.glob("*.md")):
            content = read_text(path)
            title = self._extract_title(content, path.stem)
            items.append(
                KnowledgeItem(
                    id=path.stem,
                    title=title,
                    kind=kind,
                    content=content,
                    source_path=self._source_path(path),
                    tags=self._infer_tags(path.name, content),
                )
            )
        return items

    def _source_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.settings.project_root))
        except ValueError:
            return str(path.relative_to(self.settings.data_dir.parent))

    @staticmethod
    def _extract_title(content: str, fallback: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return fallback

    @staticmethod
    def _infer_tags(filename: str, content: str) -> list[str]:
        tags = []
        text = f"{filename}\n{content}"
        for term in ["PRD", "技术", "上线", "灰度", "回滚", "FAQ", "测试", "会议", "风险", "行动项"]:
            if term in text:
                tags.append(term)
        return tags
