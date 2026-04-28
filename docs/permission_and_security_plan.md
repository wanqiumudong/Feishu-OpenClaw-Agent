# Permission and Security Plan

## 配置项设计

真实接入配置只能通过本地环境变量或本地 `.env` 提供，公共仓库只保留 `.env.example` 占位符。

| 变量 | 用途 | 当前状态 |
| --- | --- | --- |
| `MEETINGFLOW_PROVIDER` | 选择 `mock`、`lark_cli` 或未来 `sdk` provider | 规划中，默认应为 `mock` |
| `MEETINGFLOW_DRY_RUN` | 控制写操作和发送操作是否只预览 | 规划中，默认应为 `true` |
| `FEISHU_APP_ID` | 飞书应用 ID | 仅占位 |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 仅占位，不得提交真实值 |
| `FEISHU_TENANT_KEY` | 测试租户标识 | 仅占位 |
| `FEISHU_USER_ACCESS_TOKEN` | 需要用户授权时的访问凭证 | 仅占位，不建议长期落盘 |
| `FEISHU_BOT_CHAT_ID` | 测试机器人发送目标群 | 仅占位 |
| `FEISHU_BASE_APP_TOKEN` | 测试 Base app token | 仅占位 |
| `FEISHU_BASE_TABLE_ID` | 测试 Base table id | 仅占位 |
| `FEISHU_DOC_TEST_TOKEN` | 测试文档 token 或 URL | 仅占位 |
| `FEISHU_MINUTES_TEST_TOKEN` | 测试会议纪要 token | 仅占位 |
| `FEISHU_CALENDAR_ID` | 测试日历 ID | 仅占位 |

## `.env.example` 规则

- `.env.example` 只能使用 `<placeholder>`。
- `.env`、`.env.*` 必须继续被 `.gitignore` 排除。
- 允许提交 `.env.example`，但不得提交 `.env.local`、`.env.test` 或真实配置。
- 示例文件里不得出现真实密钥、真实用户标识、真实群 ID 或真实企业数据。

## 权限矩阵

权限名称需按官方文档确认，本文不硬编精确 scope。

| 能力 | 需要访问的数据 | 可能需要的权限范围 | 接入方式 | 风险等级 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| 文档搜索/读取 | 测试文档标题、正文、URL/token | 需按官方文档确认 Docs/Wiki 读取权限 | lark-cli 优先，SDK 补位 | 中 | 已授权，测试文档读取已验证 |
| 会议纪要读取 | 测试会议纪要标题、正文、参会信息 | 需按官方文档确认 VC/Minutes 读取权限 | lark-cli 优先 | 中 | 已授权，等待 minute token |
| 日历读取 | 会议标题、时间、参会人、描述 | 需按官方文档确认 Calendar 读取权限 | lark-cli 或 SDK | 中 | 未接入 |
| 群消息读取 | 测试群消息内容、发送人、时间 | 需按官方文档确认 IM 消息读取权限 | lark-cli 或 SDK | 高 | 后置 |
| 机器人文本发送 | 测试群 ID、消息内容 | 需按官方文档确认 IM 发送权限 | lark-cli 或 SDK | 中 | 后置 |
| 飞书卡片发送 | 测试群 ID、卡片 JSON | 需按官方文档确认卡片/消息发送权限 | SDK 或 OpenAPI | 中 | 后置 |
| 任务创建 | 任务标题、负责人、截止时间 | 需按官方文档确认 Task 写权限 | lark-cli 或 SDK | 高 | 后置，必须 dry-run |
| Base 查询 | 测试表字段、记录内容 | 需按官方文档确认 Base 读权限 | lark-cli 或 SDK | 中 | 后置 |
| Base 写入 | 测试表记录 upsert | 需按官方文档确认 Base 写权限 | lark-cli 或 SDK | 高 | 后置，必须 dry-run |
| 事件订阅 | 事件 payload、对象 ID、时间 | 需按官方文档确认事件订阅和回调权限 | SDK/OpenAPI | 高 | 后置 |
| OpenClaw channel | 飞书上下文和 Agent 消息 | 需按官方平台确认 | OpenClaw | 高 | 后期入口 |

## 数据安全边界

- 公共仓库只保留 mock 数据、脱敏样例和配置占位符。
- 不落盘真实敏感内容；如必须缓存真实测试数据，应存放在被 gitignore 的本地目录，并使用脱敏标题。
- `outputs/` 中避免真实个人姓名、真实群 ID、真实文档 URL、真实企业数据。
- `logs/` 中避免凭证、chat id、user id、tenant key 明文。
- 提交前必须运行 secret 风险检查。
- 真实飞书数据不得进入 public GitHub 仓库。

## 本地开发与比赛 Demo 的区别

| 场景 | 可用数据 | 可用能力 | 对外展示方式 |
| --- | --- | --- | --- |
| 本地开发 | mock 数据、脱敏测试数据 | CLI、本地 outputs、dry-run | 可公开 mock 示例 |
| 比赛 Demo | 测试飞书租户或自建测试数据 | 只读接入、测试群发送、测试表 dry-run | 展示测试对象，不展示密钥 |
| 公共仓库 | mock 数据和示例输出 | 可复现本地 demo | 不包含真实凭证和真实企业数据 |

## 提交前检查清单

- `git diff --check`
- `python -m unittest discover -s tests`
- 检查误导性完成表述。
- 检查凭证和 token 风险。
- 检查 `.env`、本地 logs 和真实 outputs 没有被 stage。
