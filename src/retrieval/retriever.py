import re

from models import KnowledgeItem


KEY_TERMS = [
    "技术评审",
    "产品评审",
    "Go/No-Go",
    "风险",
    "灰度",
    "上线",
    "回滚",
    "P95",
    "延迟",
    "行动项",
    "任务",
    "FAQ",
    "客服",
    "测试",
    "误召回",
    "监控",
    "推进表",
    "阻塞",
    "权限",
    "自动周报",
    "客户反馈",
    "用户反馈",
    "非任务型承诺句",
    "评测集",
    "结构化结果表",
    "已确认字段",
    "异步队列",
    "复盘",
    "证据",
    "字段",
]

KIND_PRIORITY = {
    "doc": 0,
    "minutes": 1,
    "truth": 2,
    "calendar": 3,
    "task": 4,
    "chat": 5,
    "base": 6,
}


def retrieve(items: list[KnowledgeItem], query: str, limit: int = 5) -> list[KnowledgeItem]:
    scored = []
    for item in items:
        score = score_item(item, query)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], KIND_PRIORITY.get(pair[1].kind, 99), pair[1].title))
    return [item for _score_value, item in scored[:limit]]


def score_item(item: KnowledgeItem, query: str) -> int:
    return _score(item, query)


def _score(item: KnowledgeItem, query: str) -> int:
    haystack = f"{item.title}\n{item.content}\n{' '.join(item.tags)}".lower()
    query_lower = query.lower()
    score = 0

    if item.title.lower() == query_lower or item.title.lower() in query_lower or query_lower in item.title.lower():
        score += 20

    for term in KEY_TERMS:
        if term.lower() in query_lower and term.lower() in haystack:
            score += 5

    for token in _tokens(query):
        if token.lower() in haystack:
            score += 1
        if token.lower() in item.title.lower():
            score += 2

    if item.kind == "truth" and "未关闭" in query:
        score += 10
    if item.kind == "base" and ("推进表" in query or "表里" in query):
        score += 12
    if item.kind == "doc" and "长会议" in query:
        score += 5
    if item.kind == "chat" and "长会议" in query:
        score += 5
    if item.kind == "calendar" and ("复盘" in query or "材料" in query):
        score += 8
    if item.kind == "doc" and ("复盘" in query or "材料" in query):
        score += 3

    return score


def _tokens(text: str) -> list[str]:
    ascii_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-/]*", text)
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return ascii_tokens + chinese_chunks
