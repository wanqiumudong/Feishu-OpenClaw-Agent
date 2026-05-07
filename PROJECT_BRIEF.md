# MeetingFlow Agent 项目说明

这份说明面向简历、面试和复赛项目介绍。它只描述当前仓库能展示和验证的内容。

## 技术栈

- Python 3.10+
- CLI 应用框架：`argparse`
- 数据层：Markdown、JSON、JSONL、CSV
- 检索层：关键词检索、来源排序、GraphRAG-style retrieval
- GraphRAG 层：text units、entities、relationships、community reports、Local Search、Global Search
- Agent 层：runtime、tool registry、run trace、workflow dispatch
- LLM 层：OpenAI-compatible chat completions，可选启用，未配置时规则回退
- 飞书接入层：FastAPI Bot webhook、Feishu SDK/OpenAPI adapter、官方 `lark-cli` smoke、card renderer
- 评测层：unittest、accuracy harness、Agent trace harness、card harness、event harness、safety harness、robustness harness、scale benchmark、GraphRAG harness、real smoke
- 安全边界：`.env` 本地配置、默认 dry-run、显式真实写入开关、公开仓不提交密钥和真实业务数据

## 可以写进简历的项目描述

MeetingFlow Agent 是一个面向飞书办公场景的会议与项目推进智能助手。项目将文档、会议纪要、群聊、任务、日历和推进表统一建模，支持带来源问答、会前背景包、会后行动项抽取、推进表对账、GraphRAG 检索、Agent trace 和飞书 Bot webhook。系统默认使用 mock 数据稳定演示，也支持通过官方 `lark-cli` 读取测试飞书文档，并通过 SDK/OpenAPI 向测试群回复。

## 核心工程工作

- 设计多源办公对象模型，将 docs、minutes、chat、tasks、calendar 和 base-style board 统一成可检索数据。
- 实现四条场景工作流，覆盖会前准备、会后执行和项目推进对账。
- 实现 GraphRAG-style retrieval，构建 text units、entities、relationships 和 community reports，并支持 Local Search 和 Global Search。
- 实现 Agent runtime 和 tool registry，统一执行 QA、会前、会后、对账、GraphRAG 和报告生成，并输出结构化 run trace。
- 实现飞书 Bot webhook、消息事件路由、卡片渲染和 SDK/OpenAPI dry-run 分发边界。
- 实现 preview-first 写入策略，任务和 Base 更新先生成预览，默认不写真实系统。
- 实现可重复评测 harness，覆盖准确性、来源命中、Agent trace、卡片、事件、dry-run safety、鲁棒性、规模测试、GraphRAG 上下文质量和真实飞书 smoke。

## 创新点

- 从普通知识库问答扩展到会议与项目推进工作流。
- 把会议纪要、任务、群聊和推进表交叉使用，用于发现漏项、阻塞和状态冲突。
- GraphRAG 不只用于展示图，而是参与检索。Local Search 从实体进入关系和文本片段，Global Search 从社区报告归纳项目主题。
- Agent runtime 不只执行命令，还记录工具调用、耗时、来源数量和 dry-run 状态，支持回归测试。
- 飞书 Bot 服务层让系统可以从群消息事件触发并生成结构化卡片，不再只有 CLI 输出。
- 写操作采用预览优先，降低 AI 自动写入办公系统的风险。
- 评测不依赖单次 demo，提供大规模 synthetic benchmark 和多维度 harness。

## 当前边界

- 当前 GraphRAG 采用工程化本地实现，结构参考 Microsoft GraphRAG 的 Local Search 和 Global Search，并结合当前办公对象模型完成索引、检索和结果编排。
- 当前事件服务支持 webhook 模式，真实长连接事件仍需后续接入。
- 当前飞书卡片支持 JSON 预览、dry-run 和测试群回复边界，生产级卡片交互仍需继续完善。
- 当前没有生产部署。
- 当前没有用户实测反馈和生产环境指标。
- OpenClaw channel 和多用户权限路由仍未完成。
- 真实飞书接入当前只建议使用测试对象，不提交真实密钥或真实业务数据。

## 面试讲法

可以按三层讲：

1. 业务层：解决会议前后和项目推进中的信息分散问题。
2. 工程层：多源数据统一建模，runtime、tool registry、provider、distributor 和 evaluation 分层。
3. AI 层：Evidence-first、GraphRAG、LLM+规则回退、preview-first action、trace-driven runtime 和 harness-driven validation。
