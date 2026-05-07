import re

from distribution.renderer import render_post_meeting_actions
from llm.client import LLMClient
from models import ActionPreview, PostMeetingResult, SourceRef
from orchestration.llm_tasks import llm_post_meeting_json
from providers.mock_provider import MockProvider


def build_post_meeting_actions(provider: MockProvider, minutes_id: str) -> PostMeetingResult:
    minutes = provider.get_minutes(minutes_id)
    decisions = _extract_section_bullets(minutes.content, "## 关键结论")
    if not decisions:
        decisions = _extract_section_bullets(minutes.content, "## 关键决策")
    actions = _extract_actions(minutes.content, minutes)
    sources = [SourceRef(id=minutes.id, title=minutes.title, kind=minutes.kind, path=minutes.source_path)]
    llm_result = _try_llm_actions(provider, minutes.content, sources[0])
    if llm_result:
        llm_decisions, llm_actions = llm_result
        if llm_decisions:
            decisions = llm_decisions
        if llm_actions:
            actions = llm_actions
    markdown = render_post_meeting_actions(minutes.title, decisions, actions, sources)
    return PostMeetingResult(markdown=markdown, actions=actions, decisions=decisions, sources=sources)


def _try_llm_actions(provider: MockProvider, content: str, source: SourceRef):
    settings = getattr(provider, "settings", None)
    if not settings:
        return None
    client = LLMClient(settings)
    if not client.available:
        return None
    try:
        return llm_post_meeting_json(client, content, source)
    except Exception:
        return None


def _extract_actions(content: str, minutes) -> list[ActionPreview]:
    actions = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("- [ ]"):
            continue
        text = line.replace("- [ ]", "").strip(" 。")
        match = re.match(r"(?P<owner>[\u4e00-\u9fff]{2,3})在 (?P<due>\d{4}-\d{2}-\d{2}) 前(?P<title>.+)", text)
        if match:
            owner = match.group("owner")
            due_date = match.group("due")
            title = match.group("title").strip()
        else:
            owner = "待确认"
            due_date = "待确认"
            title = text
        actions.append(
            ActionPreview(
                title=title,
                owner=owner,
                due_date=due_date,
                background=_background_for(title),
                source=SourceRef(id=minutes.id, title=minutes.title, kind=minutes.kind, path=minutes.source_path),
            )
        )
    return actions


def _extract_section_bullets(content: str, heading: str) -> list[str]:
    lines = content.splitlines()
    capture = False
    bullets = []
    for line in lines:
        if line.strip() == heading:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture and line.strip().startswith("- "):
            bullets.append(line.strip()[2:])
    return bullets


def _background_for(title: str) -> str:
    if "FAQ" in title or "客服" in title:
        return "data/docs/faq_user_feedback.md"
    if "监控" in title or "灰度" in title:
        return "data/docs/release_sop_gray_rollback.md"
    if "测试" in title or "回归" in title:
        return "data/docs/test_checklist_quality.md"
    return "data/docs/project_overview.md"
