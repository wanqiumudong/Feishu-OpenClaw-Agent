from distribution.renderer import sources_from_items
from models import MarkdownResult
from retrieval.graphrag import graphrag_retrieve, graph_summary


def answer_with_graphrag(provider, question: str, *, mode: str = "local") -> MarkdownResult:
    bundle = provider.load_bundle()
    result = graphrag_retrieve(bundle, question, mode=mode, seed_limit=10, limit=14)
    sources = sources_from_items(result.expanded_items)
    lines = [
        "# GraphRAG Answer",
        "",
        f"**问题**：{question}",
        f"**模式**：{mode}",
        "",
        "## 答案",
        "",
        _compose_answer(result.expanded_items),
        "",
        "## Microsoft GraphRAG-aligned Context",
        *_context_lines(result.context),
        "",
        "## Graph Retrieval Trace",
        f"- {graph_summary(result)}",
        "- seed sources:",
        *_item_lines(result.seed_items[:6]),
        "- expanded evidence:",
        *_item_lines(result.expanded_items[:10]),
        "",
        "## Graph Edges",
        *_edge_lines(result.edges[:12]),
        "",
        "## 来源",
        *_source_lines(sources),
    ]
    return MarkdownResult(markdown="\n".join(lines) + "\n", sources=sources)


def _compose_answer(items) -> str:
    if not items:
        return "当前没有找到足够证据。"
    grouped = {}
    for item in items:
        grouped.setdefault(item.kind, []).append(item)

    lines = [
        "GraphRAG 先构建 text units、entities、relationships 和 community reports，再按问题选择相关上下文。",
        "当前最重要的线索如下：",
        "",
    ]
    for kind in ("doc", "minutes", "truth", "task", "base", "chat", "calendar"):
        for item in grouped.get(kind, [])[:2]:
            excerpt = " ".join(line.strip() for line in item.content.splitlines() if line.strip())[:120]
            lines.append(f"- [{kind}] {item.title}: {excerpt}")
    return "\n".join(lines)


def _item_lines(items) -> list[str]:
    if not items:
        return ["  - 无"]
    return [f"  - [{item.kind}] {item.title} (`{item.source_path}`)" for item in items]


def _edge_lines(edges) -> list[str]:
    if not edges:
        return ["- 无"]
    output = []
    for edge in edges:
        evidence = f"，evidence={edge.evidence}" if edge.evidence else ""
        output.append(f"- {edge.relation}: `{edge.source}` -> `{edge.target}`{evidence}")
    return output


def _context_lines(context) -> list[str]:
    if not context:
        return ["- 无"]
    lines = [
        f"- text_units: {len(context.text_units)}",
        f"- entities: {len(context.selected_entities)}",
        f"- relationships: {len(context.relationships)}",
        f"- community_reports: {len(context.community_reports)}",
        "- selected community reports:",
    ]
    if context.community_reports:
        lines.extend(f"  - {report.title}: {report.summary}" for report in context.community_reports[:5])
    else:
        lines.append("  - 无")
    return lines


def _source_lines(sources) -> list[str]:
    if not sources:
        return ["- 无"]
    return [f"- [{source.kind}] {source.title}：`{source.path}`" for source in sources]
