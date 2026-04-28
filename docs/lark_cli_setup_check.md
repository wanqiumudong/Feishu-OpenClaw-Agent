# Lark CLI Setup Check

## 目标

记录本机对官方 `larksuite/cli` 的安装、命令核对和当前接入边界。本文只记录工具可用性，不表示已经完成真实飞书组织接入。

## 安装来源

- 官方仓库：`https://github.com/larksuite/cli`
- npm 包：`@larksuite/cli`
- 本机版本：`lark-cli version 1.0.19`
- 安装方式：
  - `npm install -g @larksuite/cli --ignore-scripts`
  - 手动下载官方 release binary：`lark-cli-1.0.19-linux-amd64.tar.gz`
  - 按 npm 包内 `checksums.txt` 校验 SHA256 后放入全局包目录的 `bin/lark-cli`

说明：直接执行 `npm install -g @larksuite/cli` 时，postinstall 下载 native binary 阶段曾长时间无输出。为避免不透明等待，本轮改用可核验的手动 binary 安装路径。

## 已确认命令入口

以下命令来自本机 `lark-cli --help` 或子命令 `--help` 输出：

```bash
lark-cli docs +fetch --api-version v2 --as user --doc <doc_url_or_token> --format json
lark-cli docs +search --query <keyword> --format json
lark-cli vc +notes --as user --minute-tokens <minute_token> --format json
lark-cli minutes +search
lark-cli calendar +agenda
lark-cli im +messages-send
lark-cli task +create
lark-cli base +record-upsert
```

其中 `docs +fetch` 默认 v1，并提示应使用 `--api-version v2`。`vc +notes` 只支持 user 身份。工程中的 `LarkCliProvider` 已显式使用 `--api-version v2` 和 `--as user`。

## 当前配置状态

`lark-cli doctor` 当前结果：

- CLI 版本检查通过：`1.0.19`
- CLI 更新检查提示：存在 `1.0.20`，当前暂不强制升级
- 配置文件检查通过
- token 本地检查通过
- token 服务端验证通过
- `open.feishu.cn` 与 `mcp.feishu.cn` 可达

`lark-cli auth status` 当前结果：

- `tokenStatus: valid`
- `identity: user`
- scope 已覆盖 docs、vc、minutes、calendar、im、task、base 等当前验证需要的能力域

本文不记录 App ID、user open id、token、secret 或真实对象 token。

## 已验证真实读取

本轮已通过 `lark-cli docs +create` 创建一份无敏感信息的测试文档，并通过以下命令完成真实读取验证：

```bash
LARK_CLI_NO_PROXY=1 lark-cli docs +fetch --api-version v2 --as user --doc <test_doc_token> --format json
```

验证结果：

- 飞书返回 `ok: true`
- 返回 payload 包含 `data.document.content`
- `LarkCliProvider` 可将该 payload 归一化为 `KnowledgeItem(kind="doc")`
- 标题可解析为 `MeetingFlow Agent 测试文档`
- 正文会去除 `<title>`、`<p>`、`<li>` 等 XML/HTML 标签
- `source_path` 使用 hash 后的 `feishu://docs/...`，不泄露原始文档 token
- QA pipeline 可召回该真实测试文档并生成带来源回答

会议纪要读取尚未验证，因为当前没有真实测试会议产生的 `minute_token`。

## 后续最小真实接入步骤

1. 准备无敏感信息的测试会议并生成会议纪要。
2. 用测试会议纪要验证：
   ```bash
   lark-cli vc +notes --as user --minute-tokens <test_minute_token> --format json
   ```
3. 将测试对象标识只放入本地 `.env` 或一次性 shell 环境：
   ```bash
   MEETINGFLOW_PROVIDER=lark_cli
   FEISHU_DOC_TEST_TOKEN=<test_doc_url_or_token>
   FEISHU_MINUTES_TEST_TOKEN=<test_minute_token>
   ```
4. 运行现有 CLI demo，确认真实测试对象可进入 `KnowledgeItem`，且 mock fallback 仍可用。
5. 如果需要复测文档读取，可运行：
   ```bash
   LARK_CLI_NO_PROXY=1 lark-cli docs +fetch --api-version v2 --as user --doc <test_doc_url_or_token> --format json
   ```

## 当前未完成

- 未读取真实测试会议纪要。
- 未启用消息发送、任务创建或 Base 写入。
- 未接入 OpenClaw。
