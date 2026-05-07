from distribution.renderer import render_qa_answer, sources_from_items
from llm.client import LLMClient
from orchestration.llm_tasks import llm_qa_answer
from providers.mock_provider import MockProvider
from retrieval.indexer import build_index
from retrieval.retriever import retrieve


def answer_question(provider: MockProvider, question: str):
    bundle = provider.load_bundle()
    items = build_index(bundle)
    matches = retrieve(items, question, limit=5)
    sources = sources_from_items(matches)
    answer = _compose_answer(question, bundle, matches)
    llm_answer = _try_llm_answer(provider, question, matches)
    if llm_answer:
        answer = llm_answer
    return render_qa_answer(question, answer, sources)


def _try_llm_answer(provider: MockProvider, question: str, matches) -> str:
    settings = getattr(provider, "settings", None)
    if not settings:
        return ""
    client = LLMClient(settings)
    if not client.available or not matches:
        return ""
    try:
        return llm_qa_answer(client, question, matches)
    except Exception:
        return ""


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

    if "权限" in question and "首版" in question:
        return (
            "跨部门权限扩散不应放进首版，原因是权限边界、历史会议可见性和自动周报推送都存在风险。"
            "首版更适合只保留会议纪要结构化、行动项预览和人工确认，不直接扩大可见范围。"
        )

    if "自动周报" in question and ("MVP" in question or "本次" in question):
        return (
            "自动周报不进入本次 MVP，因为本次上线范围聚焦结构化摘要、行动项抽取和风险提示。"
            "自动周报涉及跨部门分发、权限扩散和推送频率控制，适合放到后续版本。"
        )

    if "非任务型承诺句" in question or ("评测集" in question and "误召回" in question):
        return (
            "非任务型承诺句需要加入评测集，因为它们看起来像行动项，但缺少明确负责人、截止时间或执行承诺。"
            "这类样本能帮助评估行动项抽取的误召回风险。"
        )

    if "Go/No-Go" in question and "行动项" in question:
        actions = [task for task in bundle.tasks if "go_no_go_minutes" in task.get("source", "")]
        if actions:
            return "Go/No-Go 会议后需要同步的行动项包括：\n\n" + "\n".join(
                f"- {task['title']}（owner：{task['owner']}，due：{task.get('due_date', '待确认')}）"
                for task in actions[:6]
            )

    if "上线复盘" in question or "复盘会" in question:
        return (
            "上线复盘会应重点查看上线 SOP、客服 FAQ、灰度客户反馈、上线复盘纪要和任务推进状态。"
            "这些材料能覆盖上线结果、用户反馈、回滚口径和后续 backlog。"
        )

    if "结构化抽取" in question and ("架构" in question or "字段" in question):
        return (
            "结构化抽取服务采用异步队列处理会议纪要，会议结束后写入结构化结果表。"
            "前端只读取已确认字段，避免把未确认的模型中间结果直接展示给用户。"
        )

    if not matches:
        return "当前 mock 数据中没有找到足够来源，建议补充对应文档或会议纪要。"

    top = matches[0]
    excerpt = top.content.strip().splitlines()[:5]
    return "根据当前召回到的资料，最相关的信息来自「{}」：\n\n{}".format(
        top.title,
        "\n".join(excerpt),
    )
