# Agent Orchestration Plan

## 设计原则

MeetingFlow Agent 不做泛化聊天机器人，而是围绕会议与项目推进设计场景工作流。当前 CLI 是最小入口，后续触发方式可以扩展为定时、事件和用户消息，但最终都应进入同一组 workflow。

## Workflow A：会前背景包

- 触发：会议开始前 N 分钟、日历事件、手动命令 `pre-meeting`。
- 输入：会议标题、参会人、会议描述、相关文档、历史会议纪要、未完成任务。
- 处理：
  - 读取会议事件和相关文档。
  - 检索历史决策、未关闭风险和待确认问题。
  - 去重同类信息，压缩为高密度知识。
  - 保留来源路径或飞书对象引用。
- 输出：会前背景包 Markdown；后续可转换为飞书卡片。
- 当前对应代码：`pre_meeting_brief.py`、`retrieval/indexer.py`、`retrieval/retriever.py`、`renderer.py`。
- 未来新增模块：`orchestration/pre_meeting.py`、`distribution/feishu_card_renderer.py`、`triggers/calendar_trigger.py`。

## Workflow B：会后行动项

- 触发：会议纪要生成、会议结束事件、手动命令 `post-meeting`。
- 输入：会议纪要、讨论内容、已有任务、相关文档。
- 处理：
  - 抽取会议结论、决策、Action Items、负责人、截止时间和风险。
  - 与已有任务比对，避免重复创建。
  - 生成任务创建预览和负责人知识包。
- 输出：任务创建预览、项目群摘要；后续可转为 Task dry-run 或卡片。
- 当前对应代码：`post_meeting_actions.py`、`renderer.py`。
- 未来新增模块：`orchestration/post_meeting.py`、`pipelines/task_dedup.py`、`distribution/task_preview_card.py`。

## Workflow C：推进总表对账

- 触发：定时任务、任务状态变化、Base 变更事件、手动命令 `reconcile`。
- 输入：任务、会议纪要、项目讨论、推进表。
- 处理：
  - 识别任务存在但推进表缺失的事项。
  - 识别状态变化。
  - 补全阻塞原因和来源。
  - 生成写入预览，不直接改真实 Base。
- 输出：推进表更新预览、风险提醒、对账摘要。
- 当前对应代码：`reconcile_board.py`、`renderer.py`。
- 未来新增模块：`orchestration/reconcile.py`、`pipelines/base_diff.py`、`distribution/reconcile_card.py`。

## Workflow D：带来源问答

- 触发：用户提问、命令行 `qa`、未来飞书消息。
- 输入：问题、文档、纪要、任务、推进表。
- 处理：
  - 将多源数据归一化为 `KnowledgeItem`。
  - 检索相关来源。
  - 生成带来源答案。
  - 标记无法确认的内容，避免幻觉。
- 输出：带来源答案 Markdown；后续可转为聊天回复或卡片。
- 当前对应代码：`qa.py`、`indexer.py`、`retriever.py`、`renderer.py`。
- 未来新增模块：`orchestration/qa.py`、`evaluation/qa_eval.py`。

## Agent 分层设计

| 层 | 责任 | 当前位置 | 未来新增 |
| --- | --- | --- | --- |
| Provider | 读取或写入飞书/本地数据 | `providers/mock_provider.py`、`providers/lark_cli_provider.py` | `providers/feishu_sdk_provider.py`、provider protocol |
| Retriever | 多源资料索引和召回 | `retrieval/indexer.py`、`retrieval/retriever.py` | vector retriever、hybrid retriever |
| Planner / Orchestrator | 根据触发选择 workflow，组织步骤 | 暂无独立模块，逻辑散在 CLI/pipeline | `orchestration/` |
| Pipeline | 实现场景能力 | `pipelines/*.py` | task dedup、base diff、source normalization |
| Renderer | 将结果转为 Markdown 或卡片结构 | `distribution/renderer.py` | card renderer、message formatter |
| Distributor | 发送消息、创建任务、写 Base | 当前未实现 | `distribution/feishu_distributor.py` |
| Evaluator | 评测准确性、来源命中和效率 | 当前只有 smoke tests | `evaluation/` 和评测样例 |

## 触发方式与优先级

| 触发方式 | 适用 workflow | 优先级 | 风险 |
| --- | --- | --- | --- |
| 手动 CLI | A/B/C/D | P0 | 最稳定，但不是真实办公触发 |
| 定时触发 | A/C | P1 | 需要调度和重复触发去重 |
| 事件触发 | A/B/C | P1 | 需要事件权限、回调验签和失败重试 |
| 用户消息触发 | D/A/B | P1 | 需要消息权限、上下文解析和敏感信息控制 |
| OpenClaw channel | D/A/B/C | P2 | 入口复杂，必须等数据源和分发链路稳定 |

## 编排风险

- 不应让每个 workflow 直接调用真实飞书 API；真实能力应集中在 Provider 和 Distributor。
- 不应跳过 dry-run；写任务、写 Base、发消息必须先可预览。
- 不应把完整文档或大表格塞进模型上下文；应先落地、清洗、检索、摘要。
- 不应把事件触发和用户消息触发混成同一逻辑；触发层只负责生成 workflow request。
