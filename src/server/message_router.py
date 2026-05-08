from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RoutedMessage:
    workflow: str
    payload: dict
    reply_style: str


def route_message(text: str) -> RoutedMessage:
    cleaned = normalize_message_text(text)
    if _is_help(cleaned):
        return RoutedMessage("help", {}, "text")
    if "会前" in cleaned or "背景包" in cleaned:
        return RoutedMessage("pre_meeting", {"event": "go_no_go_review"}, "card")
    if "会后" in cleaned or "行动项" in cleaned:
        return RoutedMessage("post_meeting", {"minutes": "go_no_go_minutes"}, "card")
    if "对账" in cleaned or "推进表" in cleaned:
        return RoutedMessage("reconcile", {}, "card")
    if "全局" in cleaned or "主题" in cleaned:
        return RoutedMessage("graphrag_global", {"question": cleaned or "项目当前主要主题和风险是什么？"}, "text")
    return RoutedMessage("graphrag_local", {"question": cleaned or "Go/No-Go 灰度发布有哪些阻塞？"}, "text")


def normalize_message_text(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"@\S+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _is_help(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ("你能做什么", "能做什么", "帮助", "help", "功能"))
