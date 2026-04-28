# First Real Feishu Integration Sprint

## 第一目标

用真实测试飞书文档和会议纪要替换部分 mock 数据源，但不做任何写操作。目标是验证读取、归一化和现有 pipeline 兼容性，不追求完整飞书闭环。

当前仓库已具备 `LarkCliProvider` 只读接入框架和 mock fallback。本机已安装并授权官方 `lark-cli` 1.0.19，且已用无敏感测试文档验证真实读取。下一步重点不是改 pipeline，而是准备测试会议纪要 `minute_token`，补齐 minutes 读取验证。

## 最小任务

1. 确认 `lark-cli` 安装方式。
   - 已记录安装命令和版本，详见 `docs/lark_cli_setup_check.md`。
   - 已确认本机可执行 `lark-cli version 1.0.19`。
   - 不把安装缓存或凭证提交入库。

2. 确认登录/授权方式。
   - 使用测试飞书租户或测试应用。
   - 配置只放本地 `.env`。
   - `.env.example` 只保留占位符。
   - 当前已完成浏览器授权，文档中不记录 App ID、user open id 或 token。

3. 用测试飞书文档验证读取。
   - 准备一份无敏感信息的测试文档。
   - 通过 `lark-cli docs +fetch --api-version v2 --as user --doc <test_doc_url_or_token> --format json` 读取。
   - 当前已完成验证。

4. 用测试会议纪要验证读取。
   - 准备一份无敏感信息的测试会议纪要。
   - 通过 `lark-cli vc +notes --as user --minute-tokens <test_minute_token> --format json` 读取。
   - 当前未完成，因为还没有测试会议产生的 `minute_token`。

5. 转换成现有结构。
   - 文档转换为 `KnowledgeItem(kind="doc")`。
   - 会议纪要转换为 `KnowledgeItem(kind="minutes")`。
   - 保留脱敏来源标题和对象类型。
   - 当前 `LarkCliProvider` 已实现最小归一化，后续需要用真实 payload 补齐字段映射。

6. 保持 `MockProvider` 可用。
   - `MEETINGFLOW_PROVIDER=mock` 仍为默认。
   - 真实读取失败时可回到 mock demo。

7. 增加 dry-run 模式。
   - 只读取和生成输出。
   - 不发送消息。
   - 不创建任务。
   - 不写 Base。

## 验收标准

- 没有真实 token、secret、cookie 或授权值进入仓库。
- mock demo 仍然可跑。
- 至少能从真实测试文档读取内容，并转换为现有 `KnowledgeItem`。
- 至少能从真实测试会议纪要读取内容，并转换为现有 `KnowledgeItem`。
- outputs 中能生成带真实测试来源标题但不泄露敏感信息的结果。
- tests 不因真实接入失败而失败。

## 回滚策略

- 如果真实接入失败，设置 `MEETINGFLOW_PROVIDER=mock`，系统回到当前 mock 模式。
- 所有真实调用都通过 config 开关控制。
- 真实读取模块不应改变现有 mock 数据文件。
- 不影响现有 tests。
- 不把真实输出提交到公共仓库。

## 本 sprint 不做

- 不发送飞书消息。
- 不创建任务。
- 不写 Base。
- 不接 OpenClaw。
- 不接复杂事件订阅。
- 不处理多租户权限体系。
