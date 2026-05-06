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
]


def retrieve(items: list[KnowledgeItem], query: str, limit: int = 5) -> list[KnowledgeItem]:
    scored = []
    for item in items:
        score = _score(item, query)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1].kind, pair[1].title))
    return [item for _score_value, item in scored[:limit]]


def _score(item: KnowledgeItem, query: str) -> int:
    haystack = f"{item.title}\n{item.content}\n{' '.join(item.tags)}".lower()
    query_lower = query.lower()
    score = 0

    for term in KEY_TERMS:
        if term.lower() in query_lower and term.lower() in haystack:
            score += 5

    for token in _tokens(query):
        if token.lower() in haystack:
            score += 1

    return score


def _tokens(text: str) -> list[str]:
    ascii_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-/]*", text)
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return ascii_tokens + chinese_chunks
