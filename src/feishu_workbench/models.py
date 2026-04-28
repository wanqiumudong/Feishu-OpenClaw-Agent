from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    id: str
    title: str
    kind: str
    path: str


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    title: str
    kind: str
    content: str
    source_path: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DataBundle:
    truth: dict[str, Any]
    docs: list[KnowledgeItem]
    minutes: list[KnowledgeItem]
    chat_messages: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    calendar_events: list[dict[str, Any]]
    board_rows: list[dict[str, Any]]


@dataclass(frozen=True)
class MarkdownResult:
    markdown: str
    sources: list[SourceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionPreview:
    title: str
    owner: str
    due_date: str
    background: str
    source: SourceRef


@dataclass(frozen=True)
class PostMeetingResult:
    markdown: str
    actions: list[ActionPreview]
    decisions: list[str]
    sources: list[SourceRef]


@dataclass(frozen=True)
class ReconcileResult:
    markdown: str
    new_items: list[dict[str, Any]]
    status_updates: list[dict[str, Any]]
    blocker_updates: list[dict[str, Any]]
    sources: list[SourceRef]
