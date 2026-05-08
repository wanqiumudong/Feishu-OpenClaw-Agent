from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RoutedMessage:
    workflow: str
    payload: dict
    reply_style: str


@dataclass(frozen=True)
class WorkflowRoute:
    workflow: str
    title: str
    description: str
    examples: tuple[str, ...]
    reply_style: str
    payload: dict
    terms: tuple[str, ...]


WORKFLOW_ROUTES = (
    WorkflowRoute(
        workflow="pre_meeting",
        title="会前背景包",
        description="整理会议目标、必读资料、近期决策、未关闭风险和待确认问题。",
        examples=("请生成 Go/No-Go 会前背景包", "下次评审会前需要看什么"),
        reply_style="card",
        payload={"event": "go_no_go_review"},
        terms=("会前", "背景包", "会议前", "准备材料", "会前准备", "评审会前"),
    ),
    WorkflowRoute(
        workflow="post_meeting",
        title="会后行动项",
        description="从会议纪要中抽取决策、负责人、截止时间和任务预览。",
        examples=("请整理会后行动项", "把这次 Go/No-Go 会议的任务列出来"),
        reply_style="card",
        payload={"minutes": "go_no_go_minutes"},
        terms=("会后", "行动项", "action", "todo", "任务预览", "负责人", "截止时间"),
    ),
    WorkflowRoute(
        workflow="reconcile",
        title="推进总表对账",
        description="对比任务、群聊和推进表，发现漏项、状态变化和阻塞原因。",
        examples=("请做推进表对账", "现在有哪些事项状态不一致"),
        reply_style="card",
        payload={},
        terms=("对账", "推进表", "状态变化", "状态不一致", "不一致", "漏项", "阻塞", "进展", "项目推进"),
    ),
    WorkflowRoute(
        workflow="graphrag_global",
        title="全局主题分析",
        description="从项目材料中归纳主题、风险和跨来源关系。",
        examples=("项目当前主要主题和风险是什么", "全局看一下 Go/No-Go 风险"),
        reply_style="text",
        payload={},
        terms=("全局", "主题", "总体", "整体", "归纳", "总结", "风险概览"),
    ),
)

CAPABILITY_TERMS = ("能力", "可以做", "能做", "用法", "说明", "帮助", "help", "怎么用", "介绍")


def route_message(text: str) -> RoutedMessage:
    cleaned = normalize_message_text(text)
    if is_capability_request(cleaned):
        return RoutedMessage("help", {}, "text")
    route = select_workflow(cleaned)
    if route is not None:
        payload = dict(route.payload)
        if route.workflow.startswith("graphrag"):
            payload["question"] = cleaned or "项目当前主要主题和风险是什么？"
        return RoutedMessage(route.workflow, payload, route.reply_style)
    return RoutedMessage("graphrag_local", {"question": cleaned or "Go/No-Go 灰度发布有哪些阻塞？"}, "text")


def build_capability_markdown() -> str:
    lines = [
        "# MeetingFlow Agent",
        "",
        "我可以处理会议和项目推进相关问题：",
        "",
    ]
    for route in WORKFLOW_ROUTES:
        lines.append(f"- **{route.title}**：{route.description}")
        lines.append(f"  示例：{route.examples[0]}")
    lines.extend(
        [
            "- **带来源问答**：直接提问，我会基于当前办公材料检索证据并回答。",
            "  示例：Go/No-Go 灰度发布有哪些阻塞？",
            "",
            "当前回复会保留来源或证据线索，高风险写入默认需要显式开关。",
        ]
    )
    return "\n".join(lines)


def select_workflow(text: str) -> WorkflowRoute | None:
    lowered = text.lower()
    best_route = None
    best_score = 0
    for route in WORKFLOW_ROUTES:
        score = _route_score(lowered, route)
        if score > best_score:
            best_score = score
            best_route = route
    return best_route if best_score > 0 else None


def is_capability_request(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in CAPABILITY_TERMS)


def normalize_message_text(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"@\S+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _route_score(text: str, route: WorkflowRoute) -> int:
    return sum(1 for term in route.terms if term.lower() in text)
