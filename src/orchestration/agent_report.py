from distribution.renderer import sources_from_items
from models import MarkdownResult, SourceRef
from retrieval.indexer import build_index
from retrieval.retriever import retrieve


WORKFLOW_QUERIES = [
    (
        "带来源问答",
        "上次技术评审会的主要风险是什么？",
        "检索多源材料，压缩为带依据的回答。",
    ),
    (
        "会前背景包",
        "Go/No-Go 灰度 回滚 风险 行动项 必读资料",
        "聚合日历、文档、纪要和未关闭风险，生成会前准备材料。",
    ),
    (
        "会后行动项",
        "Go/No-Go 会议后 行动项 负责人 截止时间 任务预览",
        "从会议纪要中抽取决策和任务预览，保留来源。",
    ),
    (
        "推进总表对账",
        "推进表 任务 状态变化 阻塞 漏项 群聊线索",
        "比较任务、群聊和推进表，输出更新建议。",
    ),
]


def build_agent_report(provider) -> MarkdownResult:
    bundle = provider.load_bundle()
    index = build_index(bundle)
    sources: list[SourceRef] = []
    lines = [
        "# MeetingFlow Agent 工程化报告",
        "",
        "## 数据覆盖",
        f"- docs：{len(bundle.docs)}",
        f"- minutes：{len(bundle.minutes)}",
        f"- chat messages：{len(bundle.chat_messages)}",
        f"- tasks：{len(bundle.tasks)}",
        f"- calendar events：{len(bundle.calendar_events)}",
        f"- board rows：{len(bundle.board_rows)}",
        f"- open risks：{len([risk for risk in bundle.truth.get('risks', []) if risk.get('status') == 'open'])}",
        f"- decisions：{len(bundle.truth.get('decisions', []))}",
        "",
        "## AI 分工",
        "- Retriever：从文档、纪要、群聊、任务、日历和推进表中召回证据。",
        "- Evidence Curator：去重并保留来源，避免只输出没有依据的结论。",
        "- GraphRAG Indexer：构建 text units、entities、relationships 和 community reports。",
        "- Workflow Planner：把办公需求分配到 QA、会前、会后和对账流程。",
        "- Extractor：把会议纪要转成决策、负责人、截止时间和任务预览。",
        "- Reconciler：比较任务、群聊和推进表，发现漏项、状态差异和阻塞。",
        "- Distributor：把结果发送到测试群、测试任务和测试 Base，默认 dry-run。",
        "- Evaluator：用 accuracy、robustness、scale 和 real smoke 检查结果。",
        "",
        "## 工作流 Trace",
    ]

    for name, query, purpose in WORKFLOW_QUERIES:
        matches = retrieve(index, query, limit=5)
        workflow_sources = sources_from_items(matches)
        sources.extend(workflow_sources)
        lines.extend(
            [
                f"### {name}",
                f"- 目标：{purpose}",
                f"- 查询：{query}",
                f"- 召回来源数：{len(workflow_sources)}",
                "- Top sources：",
                *_source_lines(workflow_sources),
                "",
            ]
        )

    lines.extend(
        [
            "## 写入保护",
            "- 默认 `MEETINGFLOW_DRY_RUN=1`。",
            "- 只有 `MEETINGFLOW_REAL_WRITE=1` 时才允许写测试群、测试任务或测试 Base。",
            "- 所有真实对象 ID 和 token 都只来自本地环境变量，不写入仓库。",
            "- 输出中的飞书来源会脱敏为 `feishu://...`。",
            "",
            "## 评测入口",
            "- `meetingflow-eval accuracy`：检查标准问题、来源和字段。",
            "- `meetingflow-eval graphrag --scale 100`：检查 Local Search、Global Search 和图检索规模。",
            "- `meetingflow-eval robustness`：检查噪声和冲突数据。",
            "- `meetingflow-eval full --scale 200`：组合准确性、鲁棒性和规模测试。",
            "- `meetingflow-eval real`：检查真实飞书测试对象读取。",
            "",
            "## 当前边界",
            "- 当前没有生产部署指标。",
            "- 当前没有用户实测反馈。",
            "- 当前已有本地卡片 JSON 预览和 mock 事件路由。",
            "- 真实长连接事件订阅、真实飞书卡片投递和 OpenClaw channel 仍是后续增强项。",
        ]
    )
    return MarkdownResult(markdown="\n".join(lines) + "\n", sources=_dedupe_sources(sources))


def _source_lines(sources: list[SourceRef]) -> list[str]:
    if not sources:
        return ["  - 无"]
    return [f"  - [{source.kind}] {source.title}：`{source.path}`" for source in sources]


def _dedupe_sources(sources: list[SourceRef]) -> list[SourceRef]:
    output = []
    seen = set()
    for source in sources:
        key = (source.kind, source.title, source.path)
        if key in seen:
            continue
        seen.add(key)
        output.append(source)
    return output
