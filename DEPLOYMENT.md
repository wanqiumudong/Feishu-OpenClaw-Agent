# MeetingFlow Agent Deployment Notes

当前推荐部署形态是飞书 Bot 后端服务。CLI 只作为开发调试、评测和录屏入口。

## 1. 本地安装

```bash
python -m pip install -e .
```

准备本地环境变量。不要提交 `.env`。

```bash
cp .env.example .env
set -a
source .env
set +a
```

关键配置：

```bash
FEISHU_APP_ID="<test-app-id>"
FEISHU_APP_SECRET="<test-app-secret>"
FEISHU_VERIFICATION_TOKEN="<test-verification-token>"
FEISHU_ENCRYPT_KEY="<test-encrypt-key-if-enabled>"
MEETINGFLOW_PROVIDER=mock
MEETINGFLOW_DRY_RUN=1
MEETINGFLOW_REAL_WRITE=0
MEETINGFLOW_REPLY_MODE=card
```

当前建议先使用 `mock` provider 跑通 Bot 形态，再逐步替换真实飞书只读数据源。

## 2. 启动 Bot 后端

```bash
meetingflow-server --host 0.0.0.0 --port 8080
```

本地检查：

```bash
curl http://127.0.0.1:8080/health
```

可用接口：

- `GET /health`
- `POST /feishu/events`
- `POST /internal/run`

`/feishu/events` 是飞书事件订阅入口，支持 URL challenge 和群消息事件。

## 3. 暴露公网地址

本机演示可以使用 Cloudflare Tunnel 或 ngrok：

```bash
cloudflared tunnel --url http://localhost:8080
```

拿到公网地址后，飞书事件订阅 URL 填：

```text
https://<public-domain>/feishu/events
```

如果部署到云主机，建议用 systemd 或 Docker 管理进程，并在反向代理层配置 HTTPS。

## 4. 配置飞书应用

在飞书开发者后台完成：

- 启用机器人能力。
- 把机器人加入测试群。
- 配置事件订阅 Request URL。
- 订阅 `im.message.receive_v1`。
- 使用测试租户和测试群，不接真实业务群。

事件 URL 配置时，飞书会发送 challenge 请求。服务会直接返回：

```json
{"challenge":"..."}
```

## 5. 飞书群内使用方式

用户不需要命令行。直接在飞书测试群里输入：

```text
@MeetingFlow 上次技术评审会的主要风险是什么？
@MeetingFlow 请生成 Go/No-Go 会前背景包
@MeetingFlow 请整理会后行动项
@MeetingFlow 推进表对账
@MeetingFlow 项目全局主题和风险是什么？
```

后端会把消息路由到对应 workflow，并用 bot 返回文本或卡片。

## 6. 写入策略

默认配置：

```bash
MEETINGFLOW_DRY_RUN=1
MEETINGFLOW_REAL_WRITE=0
```

该模式只验证事件入口、Agent 执行、卡片渲染和分发参数，不会真实发消息。

确认测试群无误后，才打开真实测试群回复：

```bash
MEETINGFLOW_DRY_RUN=0
MEETINGFLOW_REAL_WRITE=1
```

当前只建议真实回复测试群。任务创建和 Base 写入仍应保持 dry-run 或人工确认。

## 7. Vercel 是否适合

当前不建议把主 Agent 后端直接部署到 Vercel。

原因：

- 核心服务是 Python Agent runtime 和 FastAPI webhook。
- 需要保存飞书应用环境变量。
- 需要稳定接收飞书事件。
- 可能运行较长的 Agent 和评测任务。

Vercel 可以用于项目介绍页、录屏入口或静态评测报告。主 Bot 后端建议放在云主机、容器服务或本机公网隧道。

## 8. 复赛录屏建议

推荐展示顺序：

1. 启动 `meetingflow-server`。
2. 展示 `/health`。
3. 飞书群里 @Bot 触发 QA。
4. 飞书群里 @Bot 触发会前背景包或推进表对账。
5. 展示后端 trace 或 `meetingflow-eval full --scale 500`。
6. 说明当前默认 dry-run 和测试群边界。

不要在录屏或公开仓库中展示真实 App Secret、真实 token 或真实业务数据。
