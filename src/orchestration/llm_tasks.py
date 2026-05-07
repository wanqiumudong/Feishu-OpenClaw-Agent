from typing import Any

from llm.client import LLMClient, parse_json_object
from models import ActionPreview, KnowledgeItem, SourceRef
from orchestration.workflow import evidence_prompt


def llm_qa_answer(client: LLMClient, question: str, matches: list[KnowledgeItem]) -> str:
    prompt = (
        "你是 MeetingFlow Agent，只能基于给定来源回答。"
        "回答要简洁，必须说明依据，不要编造没有出现在来源中的事实。\n\n"
        f"问题：{question}\n\n来源：\n{evidence_prompt(matches)}"
    )
    return client.chat(
        [
            {"role": "system", "content": "你负责企业会议和项目推进场景的带来源问答。"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=900,
    )


def llm_brief_summary(client: LLMClient, event: dict[str, Any], matches: list[KnowledgeItem]) -> str:
    prompt = (
        "请为会议生成一段高密度会前摘要。只基于来源材料，控制在 5 条以内。"
        "每条要能帮助参会人快速进入讨论。\n\n"
        f"会议：{event.get('title')}\n目的：{event.get('purpose')}\n\n来源：\n{evidence_prompt(matches)}"
    )
    return client.chat(
        [
            {"role": "system", "content": "你负责生成会前背景包。"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=900,
    )


def llm_post_meeting_json(client: LLMClient, minutes_content: str, source: SourceRef) -> tuple[list[str], list[ActionPreview]]:
    prompt = (
        "从会议纪要中抽取会议结论和行动项。返回严格 JSON，格式为："
        '{"decisions":["..."],"actions":[{"title":"...","owner":"...","due_date":"YYYY-MM-DD 或 待确认","background":"..."}]}。'
        "不要输出 JSON 以外的文字。\n\n"
        f"会议纪要：\n{minutes_content[:6000]}"
    )
    text = client.chat(
        [
            {"role": "system", "content": "你负责把会议纪要转成可确认的任务预览。"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1200,
    )
    payload = parse_json_object(text)
    decisions = [str(item).strip() for item in payload.get("decisions", []) if str(item).strip()]
    actions = []
    for item in payload.get("actions", []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        actions.append(
            ActionPreview(
                title=title,
                owner=str(item.get("owner", "待确认")).strip() or "待确认",
                due_date=str(item.get("due_date", "待确认")).strip() or "待确认",
                background=str(item.get("background", "待确认")).strip() or "待确认",
                source=source,
            )
        )
    return decisions, actions


def llm_reconcile_note(client: LLMClient, context: str) -> str:
    prompt = (
        "请基于任务、推进表和群聊线索，生成一段项目推进对账说明。"
        "重点说明新增事项、状态变化和阻塞原因。不要编造来源中不存在的事项。\n\n"
        f"上下文：\n{context[:6000]}"
    )
    return client.chat(
        [
            {"role": "system", "content": "你负责项目推进对账。"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=900,
    )
