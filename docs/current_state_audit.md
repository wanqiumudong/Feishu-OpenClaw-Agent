# Current State Audit

## 审查范围

本审查只基于当前仓库内容：`README.md`、`docs/`、`data/`、`outputs/`、`src/feishu_workbench/`、`tests/` 和 `pyproject.toml`。当前版本是 mock-driven bootstrap MVP，不包含真实飞书组织接入、OpenClaw channel、事件订阅、消息卡片投递、任务写入或 Base 写入。

## 当前已完成能力

- 命令行入口：`python -m feishu_workbench` 已提供 `qa`、`pre-meeting`、`post-meeting`、`reconcile` 四个命令。
- 带来源问答：`qa.py` 基于 mock 数据构建索引，使用关键词召回并输出 Markdown 与来源列表。
- 会前背景包：`pre_meeting_brief.py` 根据日历事件和相关资料生成会议目标、必读资料、关键决策、未关闭风险和待确认问题。
- 会后行动项：`post_meeting_actions.py` 从会议纪要 checkbox 行抽取 Action Items，并生成任务创建预览；当前不创建真实飞书任务。
- 推进总表对账：`reconcile_board.py` 对比任务、推进表和群聊线索，生成新增事项、状态更新和阻塞补全预览；当前不写真实 Base。
- Markdown 渲染：`distribution/renderer.py` 统一生成本地 Markdown 输出。
- smoke tests：`tests/test_smoke.py` 覆盖数据加载和四条 pipeline 的最小可运行性。
- 真实只读接入框架：`LarkCliProvider` 可在配置测试文档/会议纪要 token 后调用本地 `lark-cli`，将返回内容归一化为 `KnowledgeItem`；本机已安装并授权官方 `lark-cli` 1.0.19，真实测试文档读取已验证，会议纪要读取仍待 minute token。

## 当前 mock 数据覆盖对象

当前数据均为 synthetic/mock，不来自真实飞书租户或真实业务用户。

| 对象 | 文件位置 | 数量 | 用途 |
| --- | --- | ---: | --- |
| 真相层 | `data/ground_truth/project_truth.json` | 1 | 定义项目、角色、决策、风险、时间线、会议和优先问题 |
| Docs/Wiki | `data/docs/*.md` | 6 | 支撑 QA、会前资料、风险和 SOP 查询 |
| Minutes | `data/minutes/*.md` | 3 | 支撑会前历史决策和会后行动项抽取 |
| Chat | `data/chats/project_chat.jsonl` | 50 | 支撑对账线索和项目讨论上下文 |
| Tasks | `data/tasks/tasks.json` | 14 | 支撑会后任务预览和推进表对账 |
| Calendar | `data/calendar/events.json` | 4 | 支撑会前背景包触发 |
| Base | `data/base/priority_board.csv` / `.json` | 5 行 | 支撑推进总表对账预览 |

## 适合接真实飞书的位置

- `providers/`：最适合承接真实飞书读取与写入边界。`MockProvider` 当前可运行；`LarkCliProvider` 当前已支持只读文档/纪要接入框架，但发送消息、创建任务和写 Base 仍未启用。
- `models.py`：`DataBundle`、`KnowledgeItem`、`SourceRef` 是现有统一结构，真实数据应先转换到这些结构再进入 pipeline。
- `retrieval/indexer.py`：当前把 docs、minutes、chat、tasks、base 统一成 `KnowledgeItem`。真实接入后应尽量保持该归一化入口稳定。
- `pipelines/`：当前承载四条业务能力。真实接入阶段应尽量只替换 provider，而不是重写 pipeline。
- `distribution/renderer.py`：当前只渲染 Markdown。后续飞书卡片和消息分发应新增 Distributor 层，不应直接把卡片逻辑塞进 pipeline。
- `main.py`：当前可通过配置选择 `mock` 或 `lark_cli` provider；未来可继续扩展 `sdk` provider，并保留 dry-run。

## 最适合保留的抽象边界

- Provider 边界：本地 mock 与真实飞书接入都应输出统一数据结构。
- Retrieval 边界：召回逻辑可以从关键词升级到更强检索，但输入输出应保持 `KnowledgeItem` 列表。
- Pipeline 边界：业务工作流应保持“输入 -> 处理 -> MarkdownResult/PostMeetingResult/ReconcileResult”。
- Renderer/Distributor 边界：内容生成和飞书分发应分开，避免真实消息发送影响本地 demo。
- Dry-run 边界：任何写任务、写 Base、发消息能力都必须先有预览模式。

## 当前最薄弱的部分

- 真实接入仍未完成完整端到端验证：`LarkCliProvider` 已具备只读调用框架，本机已验证 `lark-cli` 可执行、授权和测试文档读取；会议纪要读取、事件触发、消息分发和写操作仍未验证。
- Provider 类型仍偏向 `MockProvider`：pipeline 函数签名直接引用 `MockProvider`，后续需要抽象成协议或基类。
- 检索较轻量：当前是关键词打分，适合 demo，不适合复杂语义等价和大规模资料。
- 会后行动项抽取依赖格式：当前依赖 `- [ ]` checkbox 和固定中文日期句式。
- 对账逻辑较粗：当前用标题匹配和简单状态/阻塞比较，不处理同义项、拆分任务或跨项目冲突。
- 配置和权限体系缺失：没有真实飞书配置加载、权限矩阵、事件订阅和安全日志策略。
- 评测仍是 smoke tests：尚未有 gold set、来源命中评分、人工评分或效率对比。

## 当前可运行与不可声称内容

已可运行：

- 本地 mock 数据加载。
- 四条本地 CLI demo。
- 四份 outputs 示例。
- 8 个 tests。

不可声称：

- 不可声称完成端到端真实飞书接入；当前只完成测试文档只读读取验证和 provider 框架。
- 不可声称完成 OpenClaw channel。
- 不可声称有真实用户反馈或线上效果。
- 不可声称可以写真实任务、真实 Base 或发送真实飞书卡片。
