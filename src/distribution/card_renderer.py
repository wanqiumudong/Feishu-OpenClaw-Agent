from typing import Any

from models import FeishuCard, SourceRef


def render_feishu_card(workflow: str, markdown: str, sources: list[SourceRef], *, title: str = "MeetingFlow") -> FeishuCard:
    summary = _compact_markdown(markdown)
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": _template_for_workflow(workflow),
        },
        "elements": [
            {"tag": "markdown", "content": summary},
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"来源数：{len(sources)}\n\n{_source_block(sources)}",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "确认预览"},
                        "type": "primary",
                        "value": {"action": "confirm_preview", "workflow": workflow},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "刷新风险"},
                        "type": "default",
                        "value": {"action": "refresh_risk", "workflow": workflow},
                    },
                ],
            },
        ],
    }
    return FeishuCard(title=title, card=card, workflow=workflow, source_count=len(sources))


def validate_card(card: dict[str, Any]) -> list[str]:
    errors = []
    if not isinstance(card.get("header"), dict):
        errors.append("missing_header")
    if not isinstance(card.get("elements"), list) or not card.get("elements"):
        errors.append("missing_elements")
    if "config" not in card:
        errors.append("missing_config")
    text = str(card)
    if "token" in text.lower() or "secret" in text.lower():
        errors.append("possible_secret_text")
    return errors


def _compact_markdown(markdown: str, *, limit: int = 2600) -> str:
    lines = [line for line in markdown.splitlines() if line.strip()]
    content = "\n".join(lines[:60])
    if len(content) > limit:
        return content[: limit - 3] + "..."
    return content


def _source_block(sources: list[SourceRef]) -> str:
    if not sources:
        return "无"
    return "\n".join(f"- [{source.kind}] {source.title}" for source in sources[:8])


def _template_for_workflow(workflow: str) -> str:
    if workflow in {"post_meeting", "reconcile"}:
        return "orange"
    if workflow.startswith("graphrag"):
        return "purple"
    if workflow == "pre_meeting":
        return "blue"
    return "green"
