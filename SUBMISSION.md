# 复赛提交说明

## 表单填写草稿

### 1. Demo 展示

Demo 建议使用 7 到 10 分钟录屏。展示顺序为项目介绍、飞书 Bot 群内触发、数据规模、带来源 QA、会前背景包、会后行动项、推进总表对账、GraphRAG、Agent runtime、harness 评测和真实飞书测试边界。

推荐录屏入口：

```bash
bash scripts/run_full_demo.sh
```

该脚本只使用 mock provider，强制 dry-run，关闭真实写入。它会依次运行单元测试、数据规模摘要、四条工作流、GraphRAG、runtime inspection、卡片预览、mock 事件触发、Agent 工程化报告、full harness 和小规模数据生成 smoke。飞书群内 Bot 触发建议单独录屏展示。

也可以运行：

```bash
meetingflow submission-pack
```

该命令会直接输出一版表单可复制内容。

### 2. 核心部分代码展示

核心代码建议展示五部分：

- `src/main.py`：CLI 入口，串起四条工作流、真实 smoke、分发和工程化报告。
- `src/server/`：飞书 Bot webhook 后端，提供 `/health`、`/feishu/events` 和 `/internal/run`。
- `src/orchestration/runtime.py`：Agent runtime 和 tool registry，负责统一执行工作流并记录 trace。
- `src/retrieval/`：统一检索层和 GraphRAG 层，把 docs、minutes、truth、calendar、chat、task 和 base 纳入索引，并生成 text units、entities、relationships 和 community reports。
- `src/pipelines/`：会前、会后、QA 和推进对账的业务工作流。
- `src/orchestration/evidence_graph.py`：证据图生成，展示资料、风险、任务和推进表之间的关系。
- `src/orchestration/graphrag_answer.py`：GraphRAG Local Search 和 Global Search 的输出编排。
- `src/server/event_handler.py`：真实 webhook 事件入口，把飞书消息类事件路由到工作流。
- `src/distribution/card_renderer.py` 和 `src/distribution/sdk_distributor.py`：飞书卡片 JSON 渲染与 SDK/OpenAPI dry-run 分发。
- `src/orchestration/submission_pack.py`：根据当前工程生成复赛表单草稿，避免手写时夸大边界。
- `src/providers/lark_cli_provider.py` 和 `src/distribution/feishu_distributor.py`：真实飞书测试对象的读取、发送和写入保护。
- `src/evaluation/run_eval.py`：harness，覆盖 accuracy、robustness、scale 和 real smoke。

### 3. 项目亮点介绍

MeetingFlow Agent 聚焦会议与项目推进，不做泛化聊天。它把飞书办公对象组织成四条可复现工作流：带来源问答、会前背景包、会后行动项和推进总表对账。

项目亮点包括：

- 多源办公数据统一建模，覆盖文档、会议纪要、群聊、任务、日历和推进表。
- 参考 Microsoft GraphRAG 的结构实现 GraphRAG，支持 Local Search 和 Global Search。
- Agent runtime 统一管理工具调用、运行 trace、dry-run 状态和输出。
- 飞书 Bot webhook 和卡片入口能展示应用形态，而不只是在终端运行命令。
- 输出保留来源，便于人工核对。
- 写操作默认 dry-run，先生成任务和 Base 更新预览，再由人确认。
- 真实飞书接入隔离在 provider 和 distributor 层，业务 pipeline 可以复用。
- 使用 harness 做大规模评测，不只依赖一次 demo。

### 4. AI 亮点介绍

AI 在项目中承担检索、压缩、抽取、归纳和对账解释。代码负责来源约束、字段校验、写入保护和回退。

高阶 AI 工程点包括：

- Evidence-first 工作流。先召回来源，再生成答案和行动项。
- GraphRAG 检索。先构建 text units、entities、relationships 和 community reports，再按问题选择 Local Search 或 Global Search。
- Agent runtime。把 Retriever、GraphRAG、Workflow、Renderer、Distributor 和 Evaluator 组织成可追踪工具调用。
- Preview-first 写入策略。AI 只生成建议，不直接改任务和 Base。
- LLM 和规则双轨。配置模型时使用 `gemini-3.1-flash-lite-preview` 生成摘要和抽取结果，模型不可用时自动回退规则实现。
- Agent 分工明确。Retriever、Evidence Curator、Workflow Planner、Extractor、Reconciler、Distributor 和 Evaluator 分层协作。
- harness 驱动验证。用 accuracy、source coverage、robustness、scale 和 real smoke 检查结果。

人和 AI 的分工是：人负责确认场景边界、测试对象和写入动作；AI 负责整理资料、抽取行动项、发现阻塞和生成对账建议。

### 5. 其他补充

当前已完成官方 `lark-cli` 重新授权，并用测试飞书文档完成真实只读读取 smoke。`meetingflow-eval real` 已能在配置测试文档后通过。

当前已完成本地卡片预览、SDK/OpenAPI dry-run 分发、webhook 事件入口和 mock 事件触发。真实长连接事件、任务/Base 正式写入、OpenClaw channel、多用户权限路由和生产部署仍未完成，项目不会把这些内容包装成已完成能力。

## 完整性与价值

MeetingFlow Agent 解决的是会议和项目推进中的信息分散问题。团队资料通常散在文档、会议纪要、群聊、任务和推进表里。会前需要翻资料，会后需要整理行动项，项目推进时还要反复核对状态和阻塞。

项目把这些对象整理成四个可运行流程：

- 带来源问答
- 会前背景包
- 会后行动项
- 推进总表对账

AI 的作用是检索、压缩、抽取、归纳和解释。代码负责来源约束、结构校验、写入保护和评测。这样可以减少会前准备、会后整理和项目同步中的重复劳动。

当前 demo 可以本地稳定运行，也可以在测试飞书对象上做 smoke check。飞书 Bot 后端可以接收群消息事件并回复测试群。真实写入默认 dry-run。

## 创新性

项目的重点不是简单调用飞书 CLI，而是把飞书对象组织成会议与项目推进场景的 Agent。

主要差异点：

- 多源办公对象统一建模。文档、会议纪要、群聊、任务和推进表统一进入 `KnowledgeItem` 和 `DataBundle`。
- 输出带来源。每个回答、行动项和对账建议都保留依据。
- 证据图可视化。录屏时能直接展示结论背后的资料关系。
- 预览优先。任务创建和 Base 更新先生成预览，再由人工确认。
- LLM 和规则双轨。LLM 负责生成和抽取，规则代码负责校验和回退。
- harness 优先。项目提供准确性、来源、鲁棒性、规模和真实飞书 smoke check，不只依赖录屏。

这套方法可以推广到周会、需求评审、上线评审、客户问题复盘等办公场景。

## 方法设计

项目采用三步方法。

第一步是数据建模。先把文档、纪要、群聊、任务和推进表都转成统一对象，再做检索、抽取和渲染。这样可以避免每个飞书接口单独写一套业务逻辑。

第二步是场景编排。Agent 不以聊天为中心，而是围绕会前、会后和项目推进三个真实动作运行。每个动作都有输入、处理、输出和来源。

第三步是 harness 评测。项目参考 RAG 和 Agent 评测中的常见指标，检查来源命中、答案命中、行动项字段、写入安全、噪声鲁棒性和规模表现。这样可以避免只靠一次录屏证明系统可用。

这和普通 vibe coding 生成的工程不同。普通工程常常只有页面、接口调用和少量示例。MeetingFlow Agent 有稳定数据层、明确工作流、真实接入边界、LLM 回退策略和可重复评测。

## 技术实现性

工程按以下层次组织：

- provider 层读取 mock 数据或飞书测试对象。
- runtime 层统一调度工具并记录 trace。
- retriever 层构建统一检索索引。
- pipeline 层实现四类会议和项目流程。
- LLM 层提供可选生成能力。
- server 层负责飞书 Bot webhook、challenge 和消息事件路由。
- distributor 层负责卡片、测试群发送、任务创建和 Base 写入。
- evaluation 层负责批量评测、trace 验证、卡片验证、事件验证和规模测试。

真实飞书接入使用官方 `lark-cli`。它只作为底层能力入口，业务逻辑仍由 MeetingFlow Agent 控制。

安全边界：

- 不提交 `.env`。
- 不提交 token、secret、cookie、真实 user id 或真实业务数据。
- 写操作默认 dry-run。
- 真实写入只允许测试群、测试任务和测试 Base。

## 当前未完成

- 真实长连接事件订阅尚未完成。
- 生产级飞书卡片交互和按钮回调尚未完成。
- OpenClaw channel 尚未完成。
- 多用户权限路由和生产部署尚未完成。
- 当前没有用户实测反馈和生产环境指标。

这些内容会作为复赛后的增强方向，不在当前提交中包装成已完成。
