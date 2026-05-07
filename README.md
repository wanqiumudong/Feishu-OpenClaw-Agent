# MeetingFlow Agent

MeetingFlow Agent 是一个面向飞书 AI 校园挑战赛的办公场景智能助手原型，聚焦会议与项目推进场景。

它把飞书群消息、测试文档和本地模拟协作数据整理成四条可运行的 Agent 工作流：

- 带来源问答：根据文档、会议纪要、群聊、任务和推进表回答问题。
- 会前背景包：为指定会议生成目标、参会人、必读资料、历史决策和风险。
- 会后行动项：从会议纪要中抽取决策、负责人、截止时间和任务创建预览。
- 推进总表对账：根据任务、会议和群聊线索生成项目状态更新预览。

项目目标不是做一个泛化聊天机器人，而是把“会前准备、会后执行、项目推进对齐”这条办公链路做成可复现的飞书 Bot 应用。

## Done
- 默认使用本地 mock 数据，开箱即可运行。
- 已加入 `meetingflow-server`，可作为飞书 Bot webhook 后端接收消息事件。
- 已加入真实飞书测试接入层，可通过官方 `lark-cli` 读取测试文档和测试会议纪要，也保留 SDK 事件和卡片边界。
- 已加入测试群消息和卡片回复能力。写操作默认 dry-run，只有本地显式打开真实写入时才会写入测试对象。
- 已加入 LLM 生成层，可使用 OpenAI-compatible 模型生成会前摘要、会后行动项和带来源回答；未配置模型时自动回退到规则实现。
- 已加入 Agent runtime、tool registry 和 run trace，所有主要工作流都可通过统一 runtime 执行。
- 已加入飞书卡片预览、mock 事件触发、真实 webhook 入口和 SDK/OpenAPI 分发边界。
- 已加入完整评测 harness，覆盖准确性、来源命中、Agent trace、卡片、事件、dry-run safety、鲁棒性、规模和真实飞书 smoke check。
- 真实长连接事件、任务/Base 写入、OpenClaw channel 和生产部署仍未完成。

## Engineering Highlights

- 多源办公对象建模：用 docs、minutes、chat、tasks、calendar 和 base-style board 模拟真实协作现场。
- 统一中间表示：将不同来源归一到 `KnowledgeItem`、`DataBundle`、`SourceRef` 等结构，便于检索、抽取和渲染复用。
- 场景化 pipeline：`qa`、`pre-meeting`、`post-meeting`、`reconcile` 分别对应办公流程中的查询、会前、会后和推进对账环节。
- 来源可追溯：所有输出都保留来源，避免只给结论、不知道依据来自哪里。
- Bot-first 应用形态：通过 `meetingflow-server` 接收飞书事件，CLI 保留为开发、录屏和评测入口。
- 真实接入隔离：真实飞书读写集中在 provider 和 distributor 层，pipeline 不直接依赖飞书接口。
- Agent runtime：通过 tool registry 执行 workflow，并输出结构化 trace，便于复盘和评测。
- 评测优先：提供批量 harness，用标准用例、噪声数据和合成规模数据检查系统表现。
- GraphRAG 检索：参考 Microsoft GraphRAG 的 Local Search 和 Global Search 结构，构建 `text_units`、`entities`、`relationships` 和 `community_reports`。
- Feishu card/event：提供卡片 JSON、webhook event routing 和 SDK/OpenAPI adapter，真实配置缺失时仍可 dry-run 验证工程路径。

## Innovation Points

- 从“知识库问答”推进到“会议与项目推进工作流 Agent”，覆盖会议前后和项目对账。
- 将会议纪要、任务、群聊和推进表交叉使用，支持发现漏记事项、状态变化和阻塞信息。
- 输出采用“预览/建议”方式，而不是直接写入系统，更符合办公场景中的人工确认流程。
- 用 mock-driven 方式先固定流程闭环和工程边界，保证 demo 稳定，也避免公开仓暴露真实组织数据。
- 引入 LLM 但不依赖单一模型。模型负责压缩、抽取和解释，代码负责来源约束、字段校验、写入保护和回退。
- 引入 GraphRAG。Local Search 用实体作为入口，扩展到关系、文本片段和社区报告；Global Search 用社区报告做全局主题归纳。
- 引入 Agent runtime 和 trace，把检索、生成、渲染、分发和评测拆成可观察工具调用。
- 引入飞书 Bot 服务层，让 Agent 能从群消息事件触发，并以文本或结构化卡片返回，而不是只在终端输出。
- 把飞书官方 CLI 当作能力底座，项目创新集中在会议与项目推进的工作流编排、多源证据组织和评测标准。

## Demo Path

建议按以下顺序展示：

1. 飞书群内 @Bot：展示用户不需要命令行即可触发 Agent。
2. `qa`：展示带来源问答，说明 Agent 能从多源材料中找依据。
3. `pre-meeting`：展示会前背景包，说明如何减少会前翻资料时间。
4. `post-meeting`：展示会后行动项，说明如何从纪要转成任务预览。
5. `reconcile`：展示推进表对账，说明如何发现漏项、状态变化和阻塞。

## Repository Layout

```text
data/                 # mock 办公数据，支撑本地 demo
src/                  # Agent 框架、Bot 服务、provider、retriever、pipeline 和 renderer
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
meetingflow evidence-graph --topic "Go/No-Go 灰度发布"
meetingflow graphrag --mode local --question "Go/No-Go 灰度发布有哪些阻塞？"
meetingflow graphrag --mode global --question "项目当前主要主题和风险是什么？"
meetingflow inspect-runtime
meetingflow run --workflow qa --payload '{"question":"上次技术评审会的主要风险是什么？"}'
meetingflow card-preview --workflow pre_meeting
meetingflow event-server --mode mock --text "请生成 Go/No-Go 会前背景包"
meetingflow agent-report
meetingflow submission-pack
```

每条命令都会在终端打印 Markdown，并在本地写入 `outputs/`。

`agent-report` 会输出工程化报告，适合录屏时展示数据规模、AI 分工、工作流 trace、写入保护和评测入口。

`evidence-graph` 会输出 Mermaid 证据图，展示回答背后的文档、纪要、任务、风险和推进表关系。

`graphrag` 会输出对齐 Microsoft GraphRAG 思路的 Local Search 或 Global Search 结果，展示 text units、entities、relationships 和 community reports。

`submission-pack` 会根据当前仓库生成复赛表单可复制内容，方便提交前统一检查是否有夸大表述。

`inspect-runtime`、`run`、`card-preview` 和 `event-server` 用于展示 Agent 平台化能力。它们会生成本地 trace 或卡片 JSON，默认不写真实飞书对象。

启动飞书 Bot 后端：

```bash
meetingflow-server --host 0.0.0.0 --port 8080
```

配置公网地址后，在飞书开发者后台把事件订阅 URL 指向：

```text
https://<public-domain>/feishu/events
```

用户在飞书测试群里 @Bot 后，后端会调用同一套 Agent runtime，并用 bot 身份返回文本或卡片。部署步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

真实测试模式需要你先在本地完成飞书授权，并只使用测试文档、测试群、测试任务和测试 Base。不要提交任何 token、secret 或真实业务数据。

```bash
MEETINGFLOW_PROVIDER=feishu \
FEISHU_DOC_URLS="<test-doc-url>" \
meetingflow real-smoke
```

发送到测试群默认仍是 dry-run。要真实写测试对象，需要同时配置测试对象 ID，并显式打开 `MEETINGFLOW_REAL_WRITE=1`。

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
meetingflow-eval full --scale 500
meetingflow-eval robustness
meetingflow-eval graphrag --scale 100
meetingflow-eval agent-trace
meetingflow-eval cards
meetingflow-eval events
meetingflow-eval safety
meetingflow-eval real
```

评测会生成本地 `reports/`。该目录只用于实验记录，不作为展示内容提交。

当前评测覆盖：

- QA 标准问题、会前背景包、会后行动项和推进表对账。
- 来源覆盖检查，默认扫过当前 mock 数据中的主要知识对象。
- 合成数据规模测试。`--scale 200` 会扩展到约 1200 篇文档、600 份会议纪要、10000 条群聊和 2800 个任务。
- GraphRAG harness，检查 Local Search、Global Search、社区报告和规模化图检索。
- Agent trace、卡片、事件和 dry-run safety harness，用于检查完整工程路径。
- Bot webhook 测试，用于检查飞书事件入口、challenge、消息路由和 dry-run 回复。
- 噪声与冲突数据测试，用于检查标题不一致、状态冲突、缺失负责人和误导性群聊线索。
- 真实飞书 smoke check，用于验证当前本地授权和测试对象配置。

更多评测说明见 [EVALUATION.md](EVALUATION.md)，复赛提交说明见 [SUBMISSION.md](SUBMISSION.md)。

完整测试步骤见 [TESTING.md](TESTING.md)，部署选择说明见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## TODO
- 真实长连接事件订阅
- 任务和 Base 写入正式确认流
- OpenClaw channel
- 多用户权限和生产部署

## References

- Microsoft GraphRAG: https://github.com/microsoft/graphrag
- GraphRAG Local Search: https://microsoft.github.io/graphrag/query/local_search/
- GraphRAG Global Search: https://microsoft.github.io/graphrag/query/global_search/
