from distribution.renderer import render_pre_meeting_brief, sources_from_items
from providers.mock_provider import MockProvider
from retrieval.indexer import build_index
from retrieval.retriever import retrieve


def build_pre_meeting_brief(provider: MockProvider, event_id: str):
    bundle = provider.load_bundle()
    event = provider.get_event(event_id)
    query = f"{event['title']} {event['purpose']} 灰度 回滚 风险 行动项"
    matches = retrieve(build_index(bundle), query, limit=8)
    sources = sources_from_items(matches)

    sections = {
        "required_docs": _required_docs(event),
        "decisions": [decision["content"] for decision in bundle.truth["decisions"][-3:]],
        "risks": [
            f"{risk['title']}（owner：{risk['owner']}，阻塞：{risk['blocker']}）"
            for risk in bundle.truth["risks"]
            if risk["status"] == "open"
        ],
        "questions": [
            "是否确认本周五进入 20% 灰度？",
            "P95 接近 11 秒是否仍可接受？",
            "客服 FAQ 回滚说明是否能在灰度前补齐？",
            "推进总表中是否还有漏记的行动项？",
        ],
    }
    return render_pre_meeting_brief(event, sections, sources)


def _required_docs(event: dict) -> list[str]:
    docs = event.get("related_docs") or []
    if not docs:
        return ["项目概览", "PRD", "相关会议纪要"]
    return docs
