# MeetingFlow Agent Testing Guide

本文档用于复赛前自测和录屏前检查。当前测试分为四层：本地功能测试、批量评测、Bot 服务测试、真实飞书测试。

## 1. 本地功能测试

先安装本地包：

```bash
python -m pip install -e .
```

运行单元测试：

```bash
python -m unittest discover -s tests
```

运行完整本地 demo：

```bash
bash scripts/run_full_demo.sh
```

这一步只使用 mock 数据，默认 dry-run，不会写入真实飞书对象。

通过标准：

- 单元测试全部通过。
- demo 能展示 QA、会前背景包、会后行动项、推进表对账、Evidence Graph、GraphRAG、Agent runtime、卡片预览和 mock 事件触发。
- 输出中没有真实 token、真实企业数据或生产指标。

## 2. 批量评测

运行全量 harness：

```bash
meetingflow-eval full --scale 500
```

也可以拆开运行：

```bash
meetingflow-eval accuracy
meetingflow-eval robustness
meetingflow-eval graphrag --scale 100
meetingflow-eval agent-trace
meetingflow-eval cards
meetingflow-eval events
meetingflow-eval safety
meetingflow-eval scale --scale 500
```

当前 harness 覆盖：

- QA、会前、会后、推进表对账的标准样例。
- 来源命中和来源覆盖。
- GraphRAG Local Search 和 Global Search。
- Agent runtime trace。
- 飞书卡片 JSON schema。
- mock 事件路由。
- dry-run 安全边界。
- 噪声数据和合成规模数据。

通过标准：

- `full --scale 500` 能跑完。
- Accuracy、Robustness、GraphRAG、Agent Trace、Cards、Events、Safety 都通过。
- Scale 部分完成，不出现异常退出。

## 3. Bot 服务测试

运行服务层单元测试：

```bash
python -m unittest tests.test_server -v
```

启动本地服务：

```bash
meetingflow-server --host 0.0.0.0 --port 8080
```

检查健康状态：

```bash
curl http://127.0.0.1:8080/health
```

模拟飞书 challenge：

```bash
curl -X POST http://127.0.0.1:8080/feishu/events \
  -H "Content-Type: application/json" \
  -d '{"challenge":"local-challenge"}'
```

模拟飞书群消息事件：

```bash
curl -X POST http://127.0.0.1:8080/feishu/events \
  -H "Content-Type: application/json" \
  -d '{"header":{"event_type":"im.message.receive_v1"},"event":{"message":{"chat_id":"oc_test_chat","message_id":"om_test","content":"{\"text\":\"推进表对账\"}"},"sender":{"sender_id":{"open_id":"ou_test_user"}}}}'
```

通过标准：

- `/health` 返回 `status=ok`。
- challenge 请求原样返回 challenge。
- mock 消息事件返回 workflow、run_id 和 dry-run delivery。
- 返回内容和日志不暴露真实 `chat_id` 或 `open_id`。

## 4. 真实飞书只读测试

真实测试前先重新登录官方 CLI：

```bash
lark-cli auth login
lark-cli auth status
lark-cli doctor
```

确认只读命令可用：

```bash
lark-cli docs +fetch --help
lark-cli vc +notes --help
```

用测试文档运行 smoke：

```bash
MEETINGFLOW_PROVIDER=feishu \
FEISHU_DOC_URLS="<test-doc-url>" \
meetingflow real-smoke
```

如果有测试会议纪要 token：

```bash
MEETINGFLOW_PROVIDER=feishu \
FEISHU_DOC_URLS="<test-doc-url>" \
FEISHU_MINUTE_TOKENS="<test-minute-token>" \
meetingflow-eval real
```

通过标准：

- `Feishu docs loaded` 或 `Feishu minutes loaded` 大于 0。
- 输出来源显示为 `feishu://...`，不暴露真实 URL、token 或原始 ID。
- mock demo 仍然可以正常运行。

## 5. 真实飞书 Bot 测试

先启动 Bot 后端，并通过 Cloudflare Tunnel 或 ngrok 暴露公网地址：

```bash
meetingflow-server --host 0.0.0.0 --port 8080
cloudflared tunnel --url http://localhost:8080
```

在飞书开发者后台配置事件订阅：

```text
https://<public-domain>/feishu/events
```

订阅事件：

```text
im.message.receive_v1
```

在测试群中 @Bot：

```text
@MeetingFlow 推进表对账
@MeetingFlow 请生成 Go/No-Go 会前背景包
```

通过标准：

- 后端收到事件并生成 run_id。
- Bot 在测试群里回复文本或卡片。
- 默认 dry-run 时不真实发送。
- 打开 `MEETINGFLOW_REAL_WRITE=1` 后只向测试群发送。

## 6. 真实飞书发送测试

先 dry-run，不发真实消息：

```bash
MEETINGFLOW_PROVIDER=mock \
MEETINGFLOW_DRY_RUN=1 \
MEETINGFLOW_REAL_WRITE=0 \
FEISHU_CHAT_ID="<test-chat-id>" \
FEISHU_SEND_AS=bot \
meetingflow qa --question "上次技术评审会的主要风险是什么？" --send-message
```

默认使用 bot 身份发送。如果改成 `FEISHU_SEND_AS=user` 后提示缺少 `im:message.send_as_user`，先重新授权：

```bash
lark-cli auth login --scope "im:message.send_as_user"
```

确认 dry-run 通过后，再发送到测试群：

```bash
MEETINGFLOW_PROVIDER=mock \
MEETINGFLOW_DRY_RUN=0 \
MEETINGFLOW_REAL_WRITE=1 \
FEISHU_CHAT_ID="<test-chat-id>" \
FEISHU_SEND_AS=bot \
meetingflow qa --question "上次技术评审会的主要风险是什么？" --send-message
```

通过标准：

- 测试群能收到 MeetingFlow 输出。
- 发送内容来自 mock demo 或测试对象。
- 不向真实业务群、真实任务列表或真实 Base 写入。

## 7. 提交前安全检查

```bash
git diff --check
```

检查误导性表述：

```bash
MISLEADING_PATTERN="$(printf '%s|%s|%s|%s|%s|%s' \
  '已接真实''飞书' '已接 ''OpenClaw' '真实''用户' '线上''指标' '已''上线' '已完成企业级''部署')"
rg -n "$MISLEADING_PATTERN" \
  README.md PROJECT_BRIEF.md EVALUATION.md SUBMISSION.md src data tests scripts .env.example
```

检查硬编码密钥：

```bash
SECRET_PATTERN="$(printf '%s|%s|%s|%s|%s' \
  'app_''secret' 'access_''token' 'tenant_access_''token' 'user_access_''token' 'sk-[A-Za-z0-9_-]{20,}')"
rg -n "$SECRET_PATTERN" \
  README.md PROJECT_BRIEF.md EVALUATION.md SUBMISSION.md src data tests scripts .env.example
```

如果命中 `.env.example` 的占位符或代码里的 HTTP header 模板，需要人工判断。真实密钥、真实 token、真实 cookie 不能进入仓库。
