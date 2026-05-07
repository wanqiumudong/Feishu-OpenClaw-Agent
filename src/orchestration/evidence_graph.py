from collections.abc import Iterable
import re
from typing import Any

from distribution.renderer import sources_from_items
from models import MarkdownResult, SourceRef
from retrieval.indexer import build_index
from retrieval.retriever import retrieve


def build_evidence_graph(provider, topic: str = "Go/No-Go 灰度发布") -> MarkdownResult:
    bundle = provider.load_bundle()
    index = build_index(bundle)
    matches = retrieve(index, topic, limit=10)
    sources = sources_from_items(matches)
    source_paths = {source.path for source in sources}

    risks = _related_risks(bundle.truth.get("risks", []), topic, source_paths)
    decisions = _related_decisions(bundle.truth.get("decisions", []), topic, source_paths)
    tasks = _related_tasks(bundle.tasks, topic, source_paths)
    board_rows = _related_board_rows(bundle.board_rows, topic, source_paths)

    lines = [
        "# MeetingFlow Evidence Graph",
        "",
        f"- Topic: {topic}",
        f"- Retrieved sources: {len(sources)}",
        f"- Related decisions: {len(decisions)}",
        f"- Related risks: {len(risks)}",
        f"- Related tasks: {len(tasks)}",
        f"- Related board rows: {len(board_rows)}",
        "",
        "## Mermaid",
        "",
        "```mermaid",
        "graph TD",
        f'  T["Topic: {_label(topic, 42)}"]',
        '  classDef source fill:#eef6ff,stroke:#337ab7,color:#111;',
        '  classDef risk fill:#fff3e6,stroke:#c56a00,color:#111;',
        '  classDef task fill:#f2f7ee,stroke:#4d7c0f,color:#111;',
        '  classDef decision fill:#f5f0ff,stroke:#7c3aed,color:#111;',
        '  classDef board fill:#f7f7f7,stroke:#666,color:#111;',
    ]

    for idx, source in enumerate(sources[:8]):
        node = f"S{idx}"
        lines.append(f'  {node}["{_label(source.kind + ": " + source.title)}"]:::source')
        lines.append(f"  T --> {node}")

    for idx, decision in enumerate(decisions[:6]):
        node = f"D{idx}"
        lines.append(f'  {node}["Decision: {_label(decision.get("content", ""))}"]:::decision')
        lines.append(f"  {_source_node(decision.get('source', ''), sources)} --> {node}")

    for idx, risk in enumerate(risks[:6]):
        node = f"R{idx}"
        lines.append(f'  {node}["Risk: {_label(risk.get("title", ""))}"]:::risk')
        lines.append(f"  {_source_node(risk.get('source', ''), sources)} --> {node}")

    for idx, task in enumerate(tasks[:7]):
        node = f"A{idx}"
        label = f"{task.get('status', '')}: {task.get('title', '')}"
        lines.append(f'  {node}["Task: {_label(label)}"]:::task')
        lines.append(f"  {_source_node(_first_link(task), sources)} --> {node}")

    for idx, row in enumerate(board_rows[:6]):
        node = f"B{idx}"
        label = f"{row.get('status', '')}: {row.get('item', '')}"
        lines.append(f'  {node}["Board: {_label(label)}"]:::board')
        lines.append(f"  {_source_node(row.get('related_doc', '') or row.get('related_meeting', ''), sources)} --> {node}")

    lines.extend(
        [
            "```",
            "",
            "## Evidence Table",
            "",
            "| Type | Title | Source |",
            "|---|---|---|",
        ]
    )
    for source in sources[:10]:
        lines.append(f"| {source.kind} | {_cell(source.title)} | `{source.path}` |")

    if decisions:
        lines.extend(["", "## Decisions"])
        for decision in decisions[:6]:
            lines.append(f"- {decision.get('date', '')} {decision.get('content', '')}")
    if risks:
        lines.extend(["", "## Open Risks"])
        for risk in risks[:6]:
            lines.append(f"- {risk.get('title', '')}: {risk.get('blocker', '')}")
    if tasks:
        lines.extend(["", "## Action Signals"])
        for task in tasks[:7]:
            blocker = task.get("blocker") or "无阻塞"
            lines.append(
                f"- {task.get('title', '')}: {task.get('owner', '')}, "
                f"{task.get('status', '')}, due {task.get('due_date', '')}, {blocker}"
            )

    lines.extend(
        [
            "",
            "## What This Adds",
            "- 把一次回答背后的证据关系显式展示出来。",
            "- 能看到哪些结论来自文档，哪些来自纪要、任务或推进表。",
            "- 适合录屏时解释 Agent 如何把多源办公数据组织成可核对结果。",
        ]
    )
    return MarkdownResult(markdown="\n".join(lines) + "\n", sources=sources)


def _related_risks(risks: Iterable[dict[str, Any]], topic: str, source_paths: set[str]) -> list[dict[str, Any]]:
    return _rank_related(
        risks,
        topic,
        source_paths,
        fields=("title", "blocker", "owner", "source"),
        prefer=lambda item: item.get("status") in {"open", "in_progress", "blocked"},
    )


def _related_decisions(
    decisions: Iterable[dict[str, Any]], topic: str, source_paths: set[str]
) -> list[dict[str, Any]]:
    return _rank_related(decisions, topic, source_paths, fields=("content", "meeting", "source", "date"))


def _related_tasks(tasks: Iterable[dict[str, Any]], topic: str, source_paths: set[str]) -> list[dict[str, Any]]:
    return _rank_related(
        tasks,
        topic,
        source_paths,
        fields=("title", "owner", "status", "source", "blocker", "related_links"),
        prefer=lambda item: item.get("priority") == "P0" or item.get("status") in {"blocked", "in_progress"},
    )


def _related_board_rows(
    rows: Iterable[dict[str, Any]], topic: str, source_paths: set[str]
) -> list[dict[str, Any]]:
    return _rank_related(
        rows,
        topic,
        source_paths,
        fields=("item", "owner", "status", "latest_progress", "blocker", "related_doc", "related_meeting"),
        prefer=lambda item: bool(item.get("blocker")) or item.get("status") in {"blocked", "in_progress"},
    )


def _rank_related(
    items: Iterable[dict[str, Any]],
    topic: str,
    source_paths: set[str],
    *,
    fields: tuple[str, ...],
    prefer=None,
) -> list[dict[str, Any]]:
    tokens = _tokens(topic)
    scored = []
    for item in items:
        text = " ".join(_string_values(item.get(field)) for field in fields)
        score = sum(1 for token in tokens if token and token.lower() in text.lower())
        score += sum(3 for path in source_paths if path and path in text)
        if prefer and prefer(item):
            score += 2
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


def _source_node(path: str, sources: list[SourceRef]) -> str:
    if not sources:
        return "T"
    for idx, source in enumerate(sources[:8]):
        if path and (path in source.path or source.path in path):
            return f"S{idx}"
    return "T"


def _first_link(task: dict[str, Any]) -> str:
    links = task.get("related_links") or []
    if isinstance(links, list) and links:
        return str(links[0])
    return str(task.get("source", ""))


def _tokens(text: str) -> list[str]:
    return [part for part in re.split(r"[\s,，。/]+", text) if part]


def _string_values(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(_string_values(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_string_values(item) for item in value.values())
    return str(value or "")


def _label(value: str, limit: int = 34) -> str:
    value = " ".join(str(value).split())
    value = value.replace('"', "'").replace("[", "(").replace("]", ")")
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "..."


def _cell(value: str) -> str:
    return str(value).replace("|", "/")
