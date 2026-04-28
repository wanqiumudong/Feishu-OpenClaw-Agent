from feishu_workbench.models import ActionPreview, MarkdownResult, ReconcileResult, SourceRef


def sources_from_items(items) -> list[SourceRef]:
    sources = []
    seen = set()
    for item in items:
        key = (item.id, item.source_path)
        if key in seen:
            continue
        seen.add(key)
        sources.append(SourceRef(id=item.id, title=item.title, kind=item.kind, path=item.source_path))
    return sources


def render_qa_answer(question: str, answer: str, sources: list[SourceRef]) -> MarkdownResult:
    lines = [
        "# QA 示例：带来源回答",
        "",
        f"**问题**：{question}",
        "",
        "## 答案",
        "",
        answer,
        "",
        "## 来源",
    ]
    lines.extend(_source_lines(sources))
    return MarkdownResult(markdown="\n".join(lines) + "\n", sources=sources)


def render_pre_meeting_brief(event: dict, sections: dict, sources: list[SourceRef]) -> MarkdownResult:
    lines = [
        f"# 会前背景包：{event['title']}",
        "",
        f"- 时间：{event['start']} - {event['end']}",
        f"- 会议目的：{event['purpose']}",
        f"- 参会人：{'、'.join(event['attendees'])}",
        "",
        "## 必读资料",
        *[f"- {doc}" for doc in sections["required_docs"]],
        "",
        "## 最近关键决策",
        *[f"- {decision}" for decision in sections["decisions"]],
        "",
        "## 未关闭风险",
        *[f"- {risk}" for risk in sections["risks"]],
        "",
        "## 待确认问题",
        *[f"- {question}" for question in sections["questions"]],
        "",
        "## 来源",
        *_source_lines(sources),
    ]
    return MarkdownResult(markdown="\n".join(lines) + "\n", sources=sources)


def render_post_meeting_actions(minutes_title: str, decisions: list[str], actions: list[ActionPreview], sources: list[SourceRef]) -> str:
    lines = [
        f"# 会后行动卡片：{minutes_title}",
        "",
        "## 会议结论",
        *[f"- {decision}" for decision in decisions],
        "",
        "## 任务创建预览",
    ]
    for action in actions:
        lines.append(f"- **{action.title}**")
        lines.append(f"  - 负责人：{action.owner}")
        lines.append(f"  - 截止时间：{action.due_date}")
        lines.append(f"  - 背景资料：{action.background}")
        lines.append(f"  - 来源：{action.source.title} ({action.source.path})")
    lines.extend(["", "## 来源", *_source_lines(sources)])
    return "\n".join(lines) + "\n"


def render_reconcile_summary(result: ReconcileResult) -> str:
    lines = [
        "# 推进总表对账预览",
        "",
        "## 新增事项",
    ]
    lines.extend(_dict_lines(result.new_items, "title"))
    lines.extend(["", "## 状态更新"])
    lines.extend(_dict_lines(result.status_updates, "title"))
    lines.extend(["", "## 阻塞补全"])
    lines.extend(_dict_lines(result.blocker_updates, "title"))
    lines.extend(["", "## 来源", *_source_lines(result.sources)])
    return "\n".join(lines) + "\n"


def _source_lines(sources: list[SourceRef]) -> list[str]:
    if not sources:
        return ["- 无"]
    return [f"- [{source.kind}] {source.title}：`{source.path}`" for source in sources]


def _dict_lines(rows: list[dict], title_key: str) -> list[str]:
    if not rows:
        return ["- 无"]
    output = []
    for row in rows:
        title = row.get(title_key) or row.get("item") or row.get("事项") or "未命名事项"
        detail = row.get("reason") or row.get("blocker") or row.get("status") or row.get("source") or ""
        output.append(f"- {title}" + (f"：{detail}" if detail else ""))
    return output
