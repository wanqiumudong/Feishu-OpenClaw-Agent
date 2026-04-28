from distribution.renderer import render_qa_answer, sources_from_items
from providers.mock_provider import MockProvider
from retrieval.indexer import build_index
from retrieval.retriever import retrieve


def answer_question(provider: MockProvider, question: str):
    bundle = provider.load_bundle()
    items = build_index(bundle)
    matches = retrieve(items, question, limit=5)
    sources = sources_from_items(matches)
    answer = _compose_answer(question, bundle, matches)
    return render_qa_answer(question, answer, sources)


def _compose_answer(question: str, bundle, matches) -> str:
    if "技术评审" in question and "风险" in question:
        risks = [
            "长会议逐字稿过长，可能导致抽取延迟增加。",
            "非任务型承诺句容易被误判为行动项。",
            "文档和会议纪要标题不一致时，知识链接召回可能不稳定。",
        ]
        return "上次技术评审会主要识别了三类风险：\n\n" + "\n".join(f"- {risk}" for risk in risks)

    if "灰度" in question or "回滚" in question:
        return (
            "灰度上线需要先确认回归测试、客服 FAQ、监控面板和 Go/No-Go 结论。"
            "回滚阈值是结构化抽取失败率超过 3%，或 P95 延迟超过 12 秒并持续 30 分钟。"
        )

    if "阻塞" in question or "未关闭" in question:
        open_risks = [
            f"{risk['title']}（owner：{risk['owner']}，阻塞：{risk['blocker']}）"
            for risk in bundle.truth["risks"]
            if risk["status"] == "open"
        ]
        return "当前未关闭阻塞包括：\n\n" + "\n".join(f"- {risk}" for risk in open_risks)

    if not matches:
        return "当前 mock 数据中没有找到足够来源，建议补充对应文档或会议纪要。"

    top = matches[0]
    excerpt = top.content.strip().splitlines()[:5]
    return "根据当前召回到的资料，最相关的信息来自「{}」：\n\n{}".format(
        top.title,
        "\n".join(excerpt),
    )
