from collections import defaultdict
import re
from typing import Any

from models import (
    CommunityReport,
    DataBundle,
    GraphEntity,
    GraphRelationship,
    KnowledgeItem,
    TextUnit,
)
from retrieval.indexer import build_index


COMMUNITIES = [
    ("release", "灰度发布与回滚", ["灰度", "Go/No-Go", "上线", "回滚", "监控", "P95", "War Room"]),
    ("quality", "质量评测与行动项抽取", ["测试", "误召回", "评测", "行动项", "长会议", "重复"]),
    ("security", "权限与数据安全", ["权限", "安全", "越权", "脱敏", "可见性"]),
    ("customer", "客户反馈与客服 FAQ", ["客服", "FAQ", "客户反馈", "用户反馈", "话术"]),
    ("delivery", "项目推进与任务对账", ["推进表", "任务", "阻塞", "状态", "owner", "负责人"]),
    ("architecture", "结构化抽取架构", ["架构", "异步队列", "结构化结果表", "字段", "接口"]),
    ("scope", "MVP 范围与产品决策", ["PRD", "MVP", "范围", "自动周报", "产品评审"]),
]


class GraphRAGIndex:
    def __init__(
        self,
        *,
        text_units: dict[str, TextUnit],
        text_unit_items: dict[str, KnowledgeItem],
        entities: dict[str, GraphEntity],
        relationships: dict[str, GraphRelationship],
        community_reports: dict[str, CommunityReport],
        entity_to_text_units: dict[str, set[str]],
        entity_to_relationships: dict[str, set[str]],
        community_to_entities: dict[str, set[str]],
    ):
        self.text_units = text_units
        self.text_unit_items = text_unit_items
        self.entities = entities
        self.relationships = relationships
        self.community_reports = community_reports
        self.entity_to_text_units = entity_to_text_units
        self.entity_to_relationships = entity_to_relationships
        self.community_to_entities = community_to_entities


def build_graphrag_index(bundle: DataBundle) -> GraphRAGIndex:
    items = build_index(bundle)
    text_units, text_unit_items = _build_text_units(items)
    entity_seed: dict[str, dict[str, Any]] = {}
    relationships: dict[str, GraphRelationship] = {}
    entity_to_text_units: dict[str, set[str]] = defaultdict(set)
    entity_to_relationships: dict[str, set[str]] = defaultdict(set)
    community_to_entities: dict[str, set[str]] = defaultdict(set)

    people = _known_people(bundle)
    for unit in text_units.values():
        titles = _extract_entities(unit, people)
        for title, entity_type, description in titles:
            community_id = _community_for_text(f"{title}\n{description}\n{unit.text}")
            entity_id = _entity_id(title)
            record = entity_seed.setdefault(
                entity_id,
                {
                    "title": title,
                    "entity_type": entity_type,
                    "description": description,
                    "text_unit_ids": set(),
                    "community_id": community_id,
                },
            )
            record["text_unit_ids"].add(unit.id)
            if not record.get("community_id"):
                record["community_id"] = community_id
            entity_to_text_units[entity_id].add(unit.id)
            if community_id:
                community_to_entities[community_id].add(entity_id)

        unit_entities = [_entity_id(title) for title, _type, _description in titles]
        for left, right in _pairs(unit_entities[:8]):
            _add_relationship(
                relationships,
                entity_to_relationships,
                left,
                right,
                "co_occurs_in_text_unit",
                0.8,
                unit.id,
            )

    _add_structured_relationships(bundle, text_units, entity_seed, relationships, entity_to_text_units, entity_to_relationships, community_to_entities)

    entities = {
        entity_id: GraphEntity(
            id=entity_id,
            title=record["title"],
            entity_type=record["entity_type"],
            description=record["description"],
            text_unit_ids=sorted(record["text_unit_ids"]),
            community_id=record.get("community_id", ""),
        )
        for entity_id, record in entity_seed.items()
    }
    community_reports = _build_community_reports(
        entities,
        relationships,
        text_units,
        community_to_entities,
    )
    return GraphRAGIndex(
        text_units=text_units,
        text_unit_items=text_unit_items,
        entities=entities,
        relationships=relationships,
        community_reports=community_reports,
        entity_to_text_units=entity_to_text_units,
        entity_to_relationships=entity_to_relationships,
        community_to_entities=community_to_entities,
    )


def _build_text_units(items: list[KnowledgeItem]) -> tuple[dict[str, TextUnit], dict[str, KnowledgeItem]]:
    units: dict[str, TextUnit] = {}
    unit_items: dict[str, KnowledgeItem] = {}
    for item in items:
        chunks = _split_text(item.content)
        for index, chunk in enumerate(chunks, start=1):
            unit_id = f"tu:{_safe_id(item.kind + ':' + item.id + ':' + str(index))}"
            units[unit_id] = TextUnit(
                id=unit_id,
                text=chunk,
                source_item_id=item.id,
                source_title=item.title,
                source_kind=item.kind,
                source_path=item.source_path,
            )
            unit_items[unit_id] = KnowledgeItem(
                id=f"{item.id}#tu{index}",
                title=item.title,
                kind=item.kind,
                content=chunk,
                source_path=item.source_path,
                tags=item.tags,
                metadata={**item.metadata, "text_unit_id": unit_id},
            )
    return units, unit_items


def _extract_entities(unit: TextUnit, people: set[str]) -> list[tuple[str, str, str]]:
    text = f"{unit.source_title}\n{unit.text}"
    entities: list[tuple[str, str, str]] = [
        (unit.source_title, f"source:{unit.source_kind}", f"Source object from {unit.source_path}")
    ]
    for name in people:
        if name and name in text:
            entities.append((name, "person", f"Person mentioned in {unit.source_title}"))
    for _community_id, _title, terms in COMMUNITIES:
        for term in terms:
            if term in text:
                entities.append((term, "topic", f"Office workflow topic: {term}"))
    for phrase in re.findall(r"(?:task|risk|decision|REQ|P95|FAQ|Go/No-Go)[A-Za-z0-9_\-/]*", text):
        entities.append((phrase, "keyword", f"Keyword extracted from {unit.source_title}"))
    return _dedupe_entity_tuples(entities)


def _add_structured_relationships(
    bundle: DataBundle,
    text_units: dict[str, TextUnit],
    entity_seed: dict[str, dict[str, Any]],
    relationships: dict[str, GraphRelationship],
    entity_to_text_units: dict[str, set[str]],
    entity_to_relationships: dict[str, set[str]],
    community_to_entities: dict[str, set[str]],
) -> None:
    source_lookup = _source_to_units(text_units)

    def ensure(title: str, entity_type: str, description: str, text_unit_id: str = "") -> str:
        entity_id = _entity_id(title)
        community_id = _community_for_text(f"{title}\n{description}")
        record = entity_seed.setdefault(
            entity_id,
            {
                "title": title,
                "entity_type": entity_type,
                "description": description,
                "text_unit_ids": set(),
                "community_id": community_id,
            },
        )
        if text_unit_id:
            record["text_unit_ids"].add(text_unit_id)
            entity_to_text_units[entity_id].add(text_unit_id)
        if community_id:
            community_to_entities[community_id].add(entity_id)
        return entity_id

    for task in bundle.tasks:
        task_entity = ensure(task.get("title", ""), "task", f"Task status: {task.get('status', '')}")
        owner_entity = ensure(task.get("owner", ""), "person", "Task owner")
        _add_relationship(relationships, entity_to_relationships, task_entity, owner_entity, "owned_by", 1.5, "")
        for link in task.get("related_links", []):
            for unit_id in _matching_units(source_lookup, str(link)):
                source_entity = ensure(text_units[unit_id].source_title, f"source:{text_units[unit_id].source_kind}", "Related background", unit_id)
                _add_relationship(relationships, entity_to_relationships, task_entity, source_entity, "uses_background", 1.4, unit_id)

    for event in bundle.calendar_events:
        event_entity = ensure(event.get("title", ""), "event", event.get("purpose", ""))
        for attendee in event.get("attendees", []):
            attendee_entity = ensure(attendee, "person", "Meeting attendee")
            _add_relationship(relationships, entity_to_relationships, event_entity, attendee_entity, "attendee", 1.0, "")
        for doc in event.get("related_docs", []):
            for unit_id in _matching_units(source_lookup, doc):
                source_entity = ensure(text_units[unit_id].source_title, f"source:{text_units[unit_id].source_kind}", "Meeting material", unit_id)
                _add_relationship(relationships, entity_to_relationships, event_entity, source_entity, "requires_doc", 1.6, unit_id)
        related_minutes = event.get("related_minutes", "")
        for unit_id in _matching_units(source_lookup, related_minutes):
            minutes_entity = ensure(text_units[unit_id].source_title, "source:minutes", "Meeting minutes", unit_id)
            _add_relationship(relationships, entity_to_relationships, event_entity, minutes_entity, "has_minutes", 1.8, unit_id)

    for risk in bundle.truth.get("risks", []):
        risk_entity = ensure(risk.get("title", ""), "risk", risk.get("blocker", ""))
        owner_entity = ensure(risk.get("owner", ""), "person", "Risk owner")
        _add_relationship(relationships, entity_to_relationships, risk_entity, owner_entity, "risk_owner", 1.5, "")
        for unit_id in _matching_units(source_lookup, risk.get("source", "")):
            source_entity = ensure(text_units[unit_id].source_title, f"source:{text_units[unit_id].source_kind}", "Risk source", unit_id)
            _add_relationship(relationships, entity_to_relationships, risk_entity, source_entity, "risk_source", 1.8, unit_id)

    for decision in bundle.truth.get("decisions", []):
        decision_entity = ensure(decision.get("content", "")[:48], "decision", decision.get("content", ""))
        for unit_id in _matching_units(source_lookup, decision.get("source", "")):
            source_entity = ensure(text_units[unit_id].source_title, f"source:{text_units[unit_id].source_kind}", "Decision source", unit_id)
            _add_relationship(relationships, entity_to_relationships, decision_entity, source_entity, "decision_source", 1.8, unit_id)


def _build_community_reports(
    entities: dict[str, GraphEntity],
    relationships: dict[str, GraphRelationship],
    text_units: dict[str, TextUnit],
    community_to_entities: dict[str, set[str]],
) -> dict[str, CommunityReport]:
    reports = {}
    for community_id, title, terms in COMMUNITIES:
        entity_ids = sorted(community_to_entities.get(community_id, set()))
        if not entity_ids:
            continue
        relationship_ids = [
            rel.id
            for rel in relationships.values()
            if rel.source in entity_ids or rel.target in entity_ids
        ]
        text_unit_ids = sorted(
            {
                unit_id
                for entity_id in entity_ids
                for unit_id in entities[entity_id].text_unit_ids
                if unit_id in text_units
            }
        )
        sample_entities = "、".join(entities[entity_id].title for entity_id in entity_ids[:8])
        sample_sources = "；".join(text_units[unit_id].source_title for unit_id in text_unit_ids[:5])
        reports[community_id] = CommunityReport(
            id=community_id,
            title=title,
            summary=(
                f"{title}社区覆盖 {len(entity_ids)} 个实体、{len(relationship_ids)} 条关系。"
                f"核心实体包括：{sample_entities}。代表来源包括：{sample_sources}。"
            ),
            entity_ids=entity_ids,
            relationship_ids=relationship_ids,
            text_unit_ids=text_unit_ids,
            rank=float(len(entity_ids) + len(relationship_ids) * 0.5),
        )
    return reports


def _add_relationship(
    relationships: dict[str, GraphRelationship],
    entity_to_relationships: dict[str, set[str]],
    source: str,
    target: str,
    description: str,
    weight: float,
    text_unit_id: str,
) -> None:
    if not source or not target or source == target:
        return
    rel_id = f"rel:{_safe_id(source + ':' + target + ':' + description + ':' + text_unit_id)}"
    relationships.setdefault(
        rel_id,
        GraphRelationship(
            id=rel_id,
            source=source,
            target=target,
            description=description,
            weight=weight,
            text_unit_ids=[text_unit_id] if text_unit_id else [],
        ),
    )
    entity_to_relationships[source].add(rel_id)
    entity_to_relationships[target].add(rel_id)


def _community_for_text(text: str) -> str:
    best = ("delivery", 0)
    for community_id, _title, terms in COMMUNITIES:
        score = sum(1 for term in terms if term and term in text)
        if score > best[1]:
            best = (community_id, score)
    return best[0]


def _known_people(bundle: DataBundle) -> set[str]:
    people = {role.get("name", "") for role in bundle.truth.get("roles", [])}
    people.update(task.get("owner", "") for task in bundle.tasks)
    people.update(message.get("sender", "") for message in bundle.chat_messages)
    for event in bundle.calendar_events:
        people.update(event.get("attendees", []))
    return {person for person in people if person}


def _source_to_units(text_units: dict[str, TextUnit]) -> dict[str, set[str]]:
    output: dict[str, set[str]] = defaultdict(set)
    for unit in text_units.values():
        output[unit.source_path].add(unit.id)
        output[unit.source_item_id].add(unit.id)
        output[unit.source_path.split("/")[-1]].add(unit.id)
        output[unit.source_path.split("/")[-1].replace(".md", "")].add(unit.id)
    return output


def _matching_units(source_lookup: dict[str, set[str]], value: str) -> list[str]:
    if not value:
        return []
    value = value.replace("\\", "/")
    matches = set(source_lookup.get(value, set()))
    for key, unit_ids in source_lookup.items():
        if value in key or key in value:
            matches.update(unit_ids)
    return sorted(matches)


def _split_text(text: str, *, max_chars: int = 900) -> list[str]:
    chunks = []
    current: list[str] = []
    current_size = 0
    for paragraph in [part.strip() for part in text.split("\n\n") if part.strip()] or [text.strip()]:
        if current and current_size + len(paragraph) > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_size = 0
        current.append(paragraph)
        current_size += len(paragraph)
    if current:
        chunks.append("\n\n".join(current))
    return chunks or [text]


def _pairs(values: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            pairs.append((left, right))
    return pairs


def _dedupe_entity_tuples(values: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    output = []
    seen = set()
    for value in values:
        key = value[0]
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _entity_id(title: str) -> str:
    return f"entity:{_safe_id(title)}"


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value.strip())
    return safe[:96] or "empty"
