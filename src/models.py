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


@dataclass(frozen=True)
class DeliveryResult:
    operation: str
    dry_run: bool
    command: list[str]
    ok: bool
    response: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass(frozen=True)
class ToolCall:
    name: str
    ok: bool
    elapsed_ms: int
    input_summary: str
    output_summary: str
    error: str = ""


@dataclass(frozen=True)
class AgentTrace:
    run_id: str
    workflow: str
    input_payload: dict[str, Any]
    tool_calls: list[ToolCall]
    output_markdown: str
    source_count: int
    dry_run: bool
    elapsed_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeishuCard:
    title: str
    card: dict[str, Any]
    workflow: str
    source_count: int


@dataclass(frozen=True)
class EvidencePacket:
    id: str
    title: str
    kind: str
    excerpt: str
    source_path: str


@dataclass(frozen=True)
class WorkflowRun:
    workflow: str
    input_summary: str
    evidence: list[EvidencePacket]
    markdown: str
    used_llm: bool = False
    validation_notes: list[str] = field(default_factory=list)
    deliveries: list[DeliveryResult] = field(default_factory=list)


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    label: str
    source_path: str = ""
    item_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    evidence: str = ""


@dataclass(frozen=True)
class TextUnit:
    id: str
    text: str
    source_item_id: str
    source_title: str
    source_kind: str
    source_path: str


@dataclass(frozen=True)
class GraphEntity:
    id: str
    title: str
    entity_type: str
    description: str
    text_unit_ids: list[str] = field(default_factory=list)
    community_id: str = ""


@dataclass(frozen=True)
class GraphRelationship:
    id: str
    source: str
    target: str
    description: str
    weight: float
    text_unit_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CommunityReport:
    id: str
    title: str
    summary: str
    entity_ids: list[str] = field(default_factory=list)
    relationship_ids: list[str] = field(default_factory=list)
    text_unit_ids: list[str] = field(default_factory=list)
    rank: float = 0.0


@dataclass(frozen=True)
class GraphRAGContext:
    mode: str
    selected_entities: list[GraphEntity] = field(default_factory=list)
    text_units: list[TextUnit] = field(default_factory=list)
    relationships: list[GraphRelationship] = field(default_factory=list)
    community_reports: list[CommunityReport] = field(default_factory=list)


@dataclass(frozen=True)
class GraphRAGResult:
    query: str
    seed_items: list[KnowledgeItem]
    expanded_items: list[KnowledgeItem]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    scores: dict[str, float] = field(default_factory=dict)
    context: GraphRAGContext | None = None
