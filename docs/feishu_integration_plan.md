# Feishu Integration Plan

## 原则

MeetingFlow Agent 的真实接入顺序是：先读取，后触发，再分发，最后写操作和 OpenClaw 入口。当前仓库已有 `MockProvider` 和只读 `LarkCliProvider` 框架，下一步应验证真实测试飞书对象能稳定转换为现有 `DataBundle` / `KnowledgeItem`，而不是重写 pipeline。

本机已安装并授权官方 `lark-cli` 1.0.19，已完成真实测试文档读取验证；会议纪要读取仍等待测试会议产生的 `minute_token`。权限范围仍需要以当前 `lark-cli auth` / `schema` 输出和官方文档确认为准。

## Phase 0：当前 mock-driven MVP

- 目标：用本地 synthetic 数据验证会议与项目推进场景是否成立。
- 输入：`data/` 下 mock Docs、Minutes、Chat、Tasks、Calendar、Base。
- 输出：四类本地 Markdown：QA、会前背景包、会后行动项、推进表对账。
- 验收标准：`python -m unittest discover -s tests` 通过；四条 demo 命令可生成 outputs。
- 当前状态：已完成 bootstrap；默认仍使用 mock 数据，只读 `LarkCliProvider` 框架已存在；本机已完成 `lark-cli` 授权和真实测试文档读取，会议纪要读取仍未验证。

## Phase 1：真实只读数据源接入

- 目标：用真实测试飞书文档和会议纪要替换部分 mock 数据源。
- 输入：测试飞书文档、测试 Wiki 或文档 URL、测试会议纪要 token、可公开或脱敏的测试内容。
- 输出：归一化后的 docs/minutes `KnowledgeItem`，继续进入现有 QA、会前和会后 pipeline。
- 验收标准：
  - mock provider 仍可用。
  - 至少能读取一个测试文档和一个测试会议纪要。
  - 不把 token、chat id、真实个人信息写入仓库。
  - outputs 中只出现脱敏标题或测试数据。

## Phase 2：事件触发

- 目标：把手动 CLI 触发扩展为定时或事件触发。
- 输入：日历事件、会议结束事件、消息事件、任务状态变化事件。
- 输出：触发任务记录和待执行 workflow 请求；默认 dry-run，不直接发送消息或写入任务。
- 验收标准：
  - 可在本地模拟事件 payload。
  - 相同事件重复触发可去重。
  - 事件失败不影响手动 CLI。

## Phase 3：消息/卡片分发

- 目标：把 Markdown 输出转换为机器人文本消息或飞书卡片。
- 输入：现有 MarkdownResult、PostMeetingResult、ReconcileResult。
- 输出：群消息文本、飞书卡片 JSON 草案、发送 dry-run 日志。
- 验收标准：
  - 默认 dry-run。
  - 文本消息可发送到测试群。
  - 卡片模板不包含真实敏感字段。

## Phase 4：任务与 Base 写操作

- 目标：把会后行动项和推进表对账从“预览”扩展到可控写入。
- 输入：ActionPreview、ReconcileResult、用户确认结果。
- 输出：任务创建请求、Base 记录 upsert 请求、操作审计记录。
- 验收标准：
  - 必须人工确认后写入。
  - 支持 dry-run 和 rollback note。
  - 写操作失败不会破坏本地状态。

## Phase 5：OpenClaw 入口集成

- 目标：将稳定的读、生成、分发链路作为 OpenClaw channel 或工具能力暴露。
- 输入：OpenClaw 消息上下文、飞书群聊上下文、用户命令。
- 输出：调用现有 workflow 的结果，并通过飞书消息或卡片返回。
- 验收标准：
  - 在真实数据源稳定后再接入。
  - 能明确区分 channel 输入和工具调用。
  - 不绕过权限与 dry-run 策略。

## Phase 6：评测与 Demo 固化

- 目标：把 demo 从“可运行”变成“可验证、可复现、可展示”。
- 输入：golden QA、会议评测样例、行动项标注、对账期望结果、录屏脚本。
- 输出：评测表、Demo 脚本、截图清单、最终展示 README。
- 验收标准：
  - 至少 10 个评测用例。
  - 关键输出可复现。
  - 真实接入和 mock 边界写清楚。

## lark-cli 优先接入清单

| 现有能力 | 目标飞书对象 | lark-cli 能力方向 | 当前映射 | 备注 |
| --- | --- | --- | --- | --- |
| 带来源问答 | Docs/Wiki | `docs +search` / `docs +fetch --api-version v2 --as user` | `docs` -> `KnowledgeItem` | 命令入口已核对，仍需授权和测试对象 |
| 会前背景包 | Calendar + Docs + Minutes | `calendar +agenda`、`docs +fetch --api-version v2 --as user`、`vc +notes --as user` | `calendar_events` + docs/minutes | 先读取日历事件，再检索相关资料 |
| 会后行动项 | Minutes | `vc +notes --as user` / `minutes +search` | `minutes` -> `KnowledgeItem` | 先只读纪要，不自动创建任务 |
| 推进总表对账 | Task + Base + Chat | `task +search`、`base +record-search`、`im +chat-messages-list` / `im +messages-search` | tasks + board + chat | 先读取，写操作后置 |
| 消息发送 | IM | `im +messages-send` | Distributor 层 | 第三阶段后再接，默认 dry-run |
| 任务创建 | Task | `task +create` | ActionPreview -> dry-run | 必须先人工确认 |
| Base 写入 | Base | `base +record-upsert` | ReconcileResult -> dry-run | 必须先测试表和 dry-run |

## SDK / OpenAPI 补位策略

适合 SDK / OpenAPI 的能力：

- 事件订阅和长连接回调。
- 需要稳定类型化结构的任务、日历、Base 写入。
- 复杂鉴权、租户级 token 管理、回调验签和错误重试。
- `lark-cli` 当前没有覆盖或命令输出不稳定的能力。

先不碰的能力：

- 多租户权限体系。
- 大规模企业数据同步。
- 批量写真实任务或真实 Base。
- 复杂审批、云盘和非会议主线业务域。

未来 `FeishuSdkProvider` 设计：

- 与 `LarkCliProvider` 并列存在，不替换 `MockProvider`。
- 对外输出同一组归一化结构：`DataBundle`、`KnowledgeItem`、`SourceRef`。
- 只在需要 SDK 的能力上补位，例如事件和写操作。
- 配置通过环境变量读取，默认禁用真实调用。

共存策略：

- `MockProvider`：默认本地 demo 和测试。
- `LarkCliProvider`：优先真实只读数据源。
- `FeishuSdkProvider`：事件、复杂鉴权和类型化写操作补位。
- Orchestrator 根据 config 选择 provider，pipeline 不直接关心接入方式。

## 真实接入优先级

1. 只读文档和会议纪要：先替换 docs/minutes，验证来源和内容结构。
2. 日历事件和会前触发：把会前背景包从手动命令扩展为日历驱动。
3. 机器人文本消息：先发送简单文本到测试群。
4. 卡片消息：将 Markdown 输出压缩为结构化卡片。
5. 任务创建和 Base 写入：先 dry-run，再人工确认写入测试对象。
6. OpenClaw channel：在读、生成、分发链路稳定后作为入口集成。
