from pathlib import Path
from typing import Any

from models import MarkdownResult
from utils.io import read_json


def build_submission_pack(provider, project_root: Path) -> MarkdownResult:
    bundle = provider.load_bundle()
    eval_cases = _count_eval_cases(project_root / "data" / "evaluation")
    lines = [
        "# 复赛表单可复制内容",
        "",
        "## 1. Demo 展示",
        "",
        "建议提交一段 5 到 7 分钟录屏，并附上仓库 README。",
        "录屏从 `bash scripts/run_full_demo.sh` 开始，展示本地可复现的完整流程。",
        "",
        "展示顺序建议如下：",
        "",
        "- 数据规模摘要，说明当前样例覆盖文档、纪要、群聊、任务、日历和推进表。",
        "- 带来源问答，展示 Agent 如何从多源材料中找依据。",
        "- 会前背景包，展示会议目标、必读资料、历史决策和未关闭风险。",
        "- 会后行动项，展示从纪要抽取负责人、截止时间和任务预览。",
        "- 推进总表对账，展示漏项、状态变化和阻塞信息。",
        "- Evidence Graph，展示回答背后的资料、风险、任务和推进表关系。",
        "- GraphRAG Local Search 和 Global Search，展示 text units、entities、relationships 和 community reports。",
        "- Agent runtime、卡片预览、mock 事件触发和评测 harness，说明系统不是只靠一次 demo。",
        "",
        f"当前 mock 数据规模为 docs {len(bundle.docs)}、minutes {len(bundle.minutes)}、"
        f"chat messages {len(bundle.chat_messages)}、tasks {len(bundle.tasks)}、"
        f"calendar events {len(bundle.calendar_events)}、board rows {len(bundle.board_rows)}。",
        f"当前人工整理评测样例约 {eval_cases} 条，运行时还会抽取最多 100 条来源覆盖检查。",
        "评测覆盖准确性、来源命中、GraphRAG、Agent trace、卡片、事件、安全边界、鲁棒性和规模测试。",
        "",
        "## 2. 核心部分代码展示",
        "",
        "建议展示以下代码路径：",
        "",
        "- `src/main.py`，CLI 入口，负责串起工作流、真实 smoke、分发和报告。",
        "- `src/models.py`，统一数据结构，包括 `KnowledgeItem`、`DataBundle`、`SourceRef` 和写入预览。",
        "- `src/retrieval/`，统一检索层，把不同办公对象放入同一个索引。",
        "- `src/pipelines/`，四条主要工作流，分别处理 QA、会前、会后和推进对账。",
        "- `src/orchestration/evidence_graph.py`，生成可核对的证据关系图。",
        "- `src/retrieval/graphrag_index.py` 和 `src/retrieval/graphrag.py`，实现 GraphRAG 索引、Local Search 和 Global Search。",
        "- `src/orchestration/agent_report.py`，生成 Agent 工程化报告。",
        "- `src/providers/lark_cli_provider.py`，通过官方 `lark-cli` 读取测试飞书对象。",
        "- `src/distribution/card_renderer.py`，生成飞书卡片 JSON 预览。",
        "- `src/distribution/sdk_distributor.py`，提供 SDK dry-run 分发边界。",
        "- `src/distribution/feishu_distributor.py`，负责测试群、测试任务和测试 Base 的 dry-run 写入保护。",
        "- `src/orchestration/event_server.py`，把 mock 飞书消息事件路由到具体工作流。",
        "- `src/evaluation/run_eval.py`，批量评测入口。",
        "",
        "## 3. 项目亮点介绍",
        "",
        "MeetingFlow Agent 解决的是会议和项目推进里的信息分散问题。",
        "同一个事项可能同时出现在文档、会议纪要、群聊、任务和推进表中。",
        "人工处理时，经常需要会前翻资料、会后整理任务、推进时核对状态。",
        "",
        "项目把这些动作整理成四条稳定工作流：带来源问答、会前背景包、会后行动项和推进总表对账。",
        "输出不会直接改真实任务和表格，而是先生成预览和依据，方便负责人确认。",
        "真实飞书接入被隔离在 provider 和 distributor 层，业务逻辑仍能复用。",
        "GraphRAG 层参考 Microsoft GraphRAG 的结构，将材料拆成 text units，再组织 entities、relationships 和 community reports。",
        "",
        "和只调用飞书 CLI 的示例不同，本项目的重点是办公对象建模、证据组织、场景工作流和批量评测。",
        "它可以扩展到周会、需求评审、上线评审、客户反馈复盘等团队场景。",
        "",
        "## 4. AI 亮点介绍",
        "",
        "AI 在项目中主要负责检索、压缩、抽取、归纳和对账解释。",
        "代码负责来源约束、字段校验、写入保护和模型不可用时的回退。",
        "",
        "核心 AI 工程点包括：",
        "",
        "- Evidence-first。先召回来源，再生成答案和行动项。",
        "- Source-traced output。输出保留来源，便于人工核对。",
        "- Preview-first action。AI 生成任务和 Base 更新预览，不默认写入真实系统。",
        "- LLM 和规则双轨。配置模型时使用 OpenAI-compatible 模型，未配置时仍能稳定运行。",
        "- Workflow agent。Agent 围绕会前、会后和项目推进运行，不做泛化聊天入口。",
        "- Harness-driven。用准确性、来源覆盖、鲁棒性、规模和真实 smoke 检查结果。",
        "",
        "人和 AI 的分工也比较明确。",
        "人负责确定场景边界、测试对象、上线风险和最终写入确认。",
        "AI 负责从材料中整理依据、抽取行动项、发现阻塞和生成可核对建议。",
        "",
        "## 5. 其他信息补充",
        "",
        "当前版本已经支持本地 mock demo、批量评测、真实飞书测试文档读取、卡片 JSON 预览、mock 事件触发和写操作 dry-run。",
        "真实写入只用于测试群、测试任务和测试 Base，并且需要本地显式打开。",
        "",
        "当前还没有完成真实长连接事件订阅、真实飞书卡片投递、OpenClaw channel、多用户权限路由和生产部署。",
        "也没有用户实测反馈和生产环境指标。",
        "这些内容会作为后续增强方向，不在当前提交中写成已完成能力。",
    ]
    return MarkdownResult(markdown="\n".join(lines) + "\n")


def _count_eval_cases(folder: Path) -> int:
    total = 0
    if not folder.exists():
        return total
    for path in sorted(folder.glob("*.json")):
        payload = read_json(path)
        total += _count_cases(payload)
    return total


def _count_cases(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return sum(_count_cases(value) for value in payload.values())
    return 0
