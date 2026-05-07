from collections import defaultdict

from models import DataBundle, GraphEdge, GraphNode, GraphRAGContext, GraphRAGResult, KnowledgeItem
from retrieval.graphrag_index import GraphRAGIndex, build_graphrag_index
from retrieval.retriever import score_item


def graphrag_retrieve(
    bundle: DataBundle,
    query: str,
    *,
    mode: str = "local",
    seed_limit: int = 10,
    limit: int = 12,
) -> GraphRAGResult:
    index = build_graphrag_index(bundle)
    if mode == "global":
        return _global_search(index, query, limit=limit)
    if mode != "local":
        raise ValueError(f"Unsupported GraphRAG mode: {mode}")
    return _local_search(index, query, seed_limit=seed_limit, limit=limit)


def _local_search(index: GraphRAGIndex, query: str, *, seed_limit: int, limit: int) -> GraphRAGResult:
    entity_scores = _score_entities(index, query)
    selected_entities = [
        index.entities[entity_id]
        for entity_id, _score in sorted(entity_scores.items(), key=lambda pair: -pair[1])[:seed_limit]
    ]
    text_unit_scores: dict[str, float] = defaultdict(float)
    relationship_ids = set()
    community_ids = set()

    for entity in selected_entities:
        entity_score = entity_scores.get(entity.id, 1.0)
        community_ids.add(entity.community_id)
        for unit_id in entity.text_unit_ids:
            text_unit_scores[unit_id] += entity_score
        for relationship_id in index.entity_to_relationships.get(entity.id, set()):
            relationship = index.relationships[relationship_id]
            relationship_ids.add(relationship_id)
            for unit_id in relationship.text_unit_ids:
                text_unit_scores[unit_id] += entity_score * relationship.weight * 0.5
            other_id = relationship.target if relationship.source == entity.id else relationship.source
            for unit_id in index.entity_to_text_units.get(other_id, set()):
                text_unit_scores[unit_id] += entity_score * relationship.weight * 0.35

    ranked_unit_ids = _rank_text_units(index, query, text_unit_scores)[:limit]
    text_units = [index.text_units[unit_id] for unit_id in ranked_unit_ids]
    ranked_relationship_ids = sorted(
        relationship_ids,
        key=lambda relationship_id: -index.relationships[relationship_id].weight,
    )[:50]
    relationships = [index.relationships[relationship_id] for relationship_id in ranked_relationship_ids]
    reports = [index.community_reports[community_id] for community_id in sorted(community_ids) if community_id in index.community_reports]
    items = [index.text_unit_items[unit_id] for unit_id in ranked_unit_ids]
    return GraphRAGResult(
        query=query,
        seed_items=items[: min(len(items), seed_limit)],
        expanded_items=items,
        nodes=_nodes_for_context(selected_entities, reports),
        edges=_edges_for_relationships(relationships),
        scores=dict(text_unit_scores),
        context=GraphRAGContext(
            mode="local",
            selected_entities=selected_entities,
            text_units=text_units,
            relationships=relationships,
            community_reports=reports,
        ),
    )


def _global_search(index: GraphRAGIndex, query: str, *, limit: int) -> GraphRAGResult:
    report_scores = {}
    for report in index.community_reports.values():
        score = _text_overlap_score(query, f"{report.title}\n{report.summary}") + report.rank * 0.05
        if score > 0:
            report_scores[report.id] = score
    if not report_scores:
        report_scores = {report.id: report.rank * 0.05 for report in index.community_reports.values()}

    reports = [
        index.community_reports[report_id]
        for report_id, _score in sorted(report_scores.items(), key=lambda pair: -pair[1])[: min(limit, 8)]
    ]
    text_unit_scores: dict[str, float] = defaultdict(float)
    relationship_ids = set()
    selected_entities = []
    for report in reports:
        for entity_id in report.entity_ids[:12]:
            entity = index.entities[entity_id]
            selected_entities.append(entity)
            for unit_id in entity.text_unit_ids:
                text_unit_scores[unit_id] += report_scores.get(report.id, 1.0)
        relationship_ids.update(report.relationship_ids[:20])

    ranked_unit_ids = _rank_text_units(index, query, text_unit_scores)[:limit]
    text_units = [index.text_units[unit_id] for unit_id in ranked_unit_ids]
    relationships = [index.relationships[relationship_id] for relationship_id in sorted(relationship_ids) if relationship_id in index.relationships]
    items = [index.text_unit_items[unit_id] for unit_id in ranked_unit_ids]
    return GraphRAGResult(
        query=query,
        seed_items=items[: min(len(items), 6)],
        expanded_items=items,
        nodes=_nodes_for_context(selected_entities, reports),
        edges=_edges_for_relationships(relationships),
        scores=dict(report_scores),
        context=GraphRAGContext(
            mode="global",
            selected_entities=selected_entities,
            text_units=text_units,
            relationships=relationships,
            community_reports=reports,
        ),
    )


def graph_summary(result: GraphRAGResult) -> str:
    context = result.context
    if context:
        return (
            f"mode={context.mode}, entities={len(context.selected_entities)}, "
            f"text_units={len(context.text_units)}, relationships={len(context.relationships)}, "
            f"community_reports={len(context.community_reports)}"
        )
    return (
        f"seeds={len(result.seed_items)}, expanded_items={len(result.expanded_items)}, "
        f"nodes={len(result.nodes)}, edges={len(result.edges)}"
    )


def _score_entities(index: GraphRAGIndex, query: str) -> dict[str, float]:
    scores = {}
    for entity in index.entities.values():
        score = _text_overlap_score(query, f"{entity.title}\n{entity.description}\n{entity.entity_type}")
        if entity.title in query:
            score += 8
        for unit_id in entity.text_unit_ids[:8]:
            score += max(score_item(index.text_unit_items[unit_id], query), 0) * 0.25
        if score > 0:
            scores[entity.id] = score
    return scores


def _rank_text_units(index: GraphRAGIndex, query: str, text_unit_scores: dict[str, float]) -> list[str]:
    for unit_id, unit in index.text_units.items():
        if unit_id not in text_unit_scores:
            baseline = score_item(index.text_unit_items[unit_id], query)
            if baseline > 0:
                text_unit_scores[unit_id] += baseline * 0.4
    return sorted(
        text_unit_scores,
        key=lambda unit_id: (
            -text_unit_scores[unit_id],
            _kind_rank(index.text_units[unit_id].source_kind),
            index.text_units[unit_id].source_title,
        ),
    )


def _nodes_for_context(entities, reports) -> list[GraphNode]:
    nodes = [
        GraphNode(id=entity.id, kind=f"entity:{entity.entity_type}", label=entity.title, item_key=entity.id)
        for entity in entities
    ]
    nodes.extend(GraphNode(id=f"community:{report.id}", kind="community_report", label=report.title) for report in reports)
    return _dedupe_nodes(nodes)


def _edges_for_relationships(relationships) -> list[GraphEdge]:
    return [
        GraphEdge(
            source=relationship.source,
            target=relationship.target,
            relation=relationship.description,
            weight=relationship.weight,
            evidence=",".join(relationship.text_unit_ids[:3]),
        )
        for relationship in relationships
    ]


def _text_overlap_score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    text_lower = text.lower()
    return float(sum(1 for token in query_tokens if token.lower() in text_lower))


def _tokens(text: str) -> list[str]:
    import re

    return re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-/]*|[\u4e00-\u9fff]{2,}", text)


def _kind_rank(kind: str) -> int:
    order = {"doc": 0, "minutes": 1, "truth": 2, "calendar": 3, "task": 4, "base": 5, "chat": 6}
    return order.get(kind, 99)


def _dedupe_nodes(nodes: list[GraphNode]) -> list[GraphNode]:
    output = []
    seen = set()
    for node in nodes:
        if node.id in seen:
            continue
        seen.add(node.id)
        output.append(node)
    return output
