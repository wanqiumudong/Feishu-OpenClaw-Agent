# MeetingFlow Agent

MeetingFlow Agent 是一个面向飞书 AI 校园挑战赛的办公场景智能助手原型，聚焦会议与项目推进场景。

它把本地模拟的飞书协作数据整理成四条可运行的 Agent 工作流：

- 带来源问答：根据文档、会议纪要、群聊、任务和推进表回答问题。
- 会前背景包：为指定会议生成目标、参会人、必读资料、历史决策和风险。
- 会后行动项：从会议纪要中抽取决策、负责人、截止时间和任务创建预览。
- 推进总表对账：根据任务、会议和群聊线索生成项目状态更新预览。

项目目标不是做一个泛化聊天机器人，而是把“会前准备、会后执行、项目推进对齐”这条办公链路做成可复现的场景工作流。

## Done
- 默认使用本地 mock 数据，开箱即可运行。
- 真实会议纪要读取、事件触发、消息卡片、任务写入、Base 写入和 OpenClaw channel 仍未完成。

## Engineering Highlights

- 多源办公对象建模：用 docs、minutes、chat、tasks、calendar 和 base-style board 模拟真实协作现场。
- 统一中间表示：将不同来源归一到 `KnowledgeItem`、`DataBundle`、`SourceRef` 等结构，便于检索、抽取和渲染复用。
- 场景化 pipeline：`qa`、`pre-meeting`、`post-meeting`、`reconcile` 分别对应办公流程中的查询、会前、会后和推进对账环节。
- 来源可追溯：所有输出都保留来源，避免只给结论、不知道依据来自哪里。
- CLI-first demo：通过 `meetingflow` 命令稳定复现，适合现场演示、录屏和测试。

## Innovation Points

- 从“知识库问答”推进到“会议与项目推进工作流 Agent”，覆盖会议前后和项目对账。
- 将会议纪要、任务、群聊和推进表交叉使用，支持发现漏记事项、状态变化和阻塞信息。
- 输出采用“预览/建议”方式，而不是直接写入系统，更符合办公场景中的人工确认流程。
- 用 mock-driven 方式先固定流程闭环和工程边界，保证 demo 稳定，也避免公开仓暴露真实组织数据。

## Demo Path

建议按以下顺序展示：

1. `qa`：先展示带来源问答，说明 Agent 能从多源材料中找依据。
2. `pre-meeting`：展示会前背景包，说明如何减少会前翻资料时间。
3. `post-meeting`：展示会后行动项，说明如何从纪要转成任务预览。
4. `reconcile`：展示推进表对账，说明如何发现漏项、状态变化和阻塞。

## Repository Layout

```text
data/                 # mock 办公数据，支撑本地 demo
src/                  # Agent 框架、provider、retriever、pipeline 和 renderer
tests/                # smoke tests
pyproject.toml        # Python package 配置
```

运行 demo 后会在本地生成 `outputs/`，该目录不作为展示内容提交。

## Quick Start

环境要求：

- Python 3.10+

安装：

```bash
python -m pip install -e .
```

运行四条 mock demo：

```bash
meetingflow qa --question "上次技术评审会的主要风险是什么？"
meetingflow pre-meeting --event go_no_go_review
meetingflow post-meeting --minutes go_no_go_minutes
meetingflow reconcile
```

每条命令都会在终端打印 Markdown，并在本地写入 `outputs/`。

## Tests

```bash
python -m unittest discover -s tests
```

当前测试覆盖：

- mock 数据加载
- QA 流程
- 会前背景包
- 会后行动项
- 推进总表对账

## Evaluation

项目还提供一套批量评测入口，用于检查输出准确性、来源命中和规模表现。

```bash
meetingflow-eval accuracy
meetingflow-eval scale --scale 200
```

评测会生成本地 `reports/`。该目录只用于实验记录，不作为展示内容提交。

当前评测覆盖：

- QA 标准问题、会前背景包、会后行动项和推进表对账。
- 来源覆盖检查，默认扫过当前 mock 数据中的主要知识对象。
- 合成数据规模测试。`--scale 200` 会扩展到约 1200 篇文档、600 份会议纪要、10000 条群聊和 2800 个任务。

## TODO
- 真实会议纪要端到端读取
- 事件订阅和自动触发
- 飞书机器人消息或卡片投递
- 飞书任务创建
- Base 写入
- OpenClaw channel
- 多用户权限和生产部署
