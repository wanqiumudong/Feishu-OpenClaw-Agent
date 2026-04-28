# MeetingFlow Agent

面向飞书 AI 校园挑战赛课题一“办公场景驱动的智能知识助手”的项目仓库。

MeetingFlow Agent 聚焦 **会议 + 项目推进** 场景，围绕“智能会议纪要 2.0 升级项目”构建一个可运行、可展示、可继续接入真实飞书数据源的办公知识助手原型。

当前版本是 **mock-driven bootstrap MVP + 真实飞书文档只读验证**：

- 默认使用本地 mock 办公数据，开箱即可运行。
- 已接入官方 `larksuite/cli` 的只读 provider 边界，并验证过测试飞书文档读取与归一化。
- 会议纪要真实读取、事件触发、消息卡片、任务写入、Base 写入和 OpenClaw channel 仍未完成。

## 工作内容

当前仓库已经完成以下工作：

1. **场景建模**
   - 将赛题方向收敛到“会议与项目推进”。
   - 定义了会前、会后、项目推进对账和带来源问答四类核心工作流。
   - 用“智能会议纪要 2.0 升级项目”作为统一 demo 场景。

2. **mock 办公数据**
   - 本地构造 Docs、会议纪要、群聊消息、任务、日历事件和推进表数据。
   - 数据只用于 demo，不含真实企业信息或真实用户隐私。

3. **最小 Agent 框架**
   - `MockProvider`：读取本地 mock 数据。
   - `LarkCliProvider`：通过官方 `lark-cli` 读取测试飞书文档，并预留会议纪要读取入口，统一归一化为 `KnowledgeItem`。
   - Retriever：基于关键词的轻量检索。
   - Pipelines：QA、会前背景包、会后行动项、推进总表对账。
   - Renderer：生成 Markdown 输出并写入 `outputs/`。

4. **已验证能力**
   - mock 模式下四条 demo 命令可运行。
   - tests 可通过。
   - 官方 `lark-cli` 已完成本机安装、授权和测试文档读取验证。
   - 真实测试文档可进入 QA pipeline，来源会脱敏为 `feishu://docs/...`，不会暴露原始文档 token。

## 当前能力

### 1. 带来源问答

根据本地文档、会议纪要、群聊、任务和推进表回答问题，并输出来源。

```bash
python -m feishu_workbench qa --question "上次技术评审会的主要风险是什么？"
```

### 2. 会前背景包

根据会议事件生成会议目的、参会人、必读资料、历史关键决策、未关闭风险和待确认问题。

```bash
python -m feishu_workbench pre-meeting --event go_no_go_review
```

### 3. 会后行动项

从会议纪要中抽取会议结论、Action Items、负责人、截止时间和来源，生成任务创建预览。

```bash
python -m feishu_workbench post-meeting --minutes go_no_go_minutes
```

### 4. 推进总表对账

根据任务、会议、群聊和推进表线索生成新增事项、状态更新和阻塞补全预览。

```bash
python -m feishu_workbench reconcile
```

## 当前边界

当前版本**不包含**：

- 完整真实飞书组织接入
- 真实会议纪要读取的端到端验证
- 事件订阅和会议结束自动触发
- 飞书机器人消息或卡片投递
- 飞书任务真实创建
- Base 真实写入
- OpenClaw channel
- 多用户权限、生产部署和线上指标

## 目录结构

```text
data/                 # mock 办公数据
docs/                 # 场景、架构、MVP、Demo、接入计划和阶段文档
outputs/              # 本地 demo 输出
src/feishu_workbench/ # 最小 Agent 框架
tests/                # smoke tests 和 provider tests
```

## 部署方法

### 方式 A：本地 mock demo

这是默认部署方式，不需要飞书账号或真实 API 权限。

环境要求：

- Python 3.10+

安装：

```bash
cd feishu_workbench
python -m pip install -e .
```

运行：

```bash
MEETINGFLOW_PROVIDER=mock python -m feishu_workbench qa --question "上次技术评审会的主要风险是什么？"
MEETINGFLOW_PROVIDER=mock python -m feishu_workbench pre-meeting --event go_no_go_review
MEETINGFLOW_PROVIDER=mock python -m feishu_workbench post-meeting --minutes go_no_go_minutes
MEETINGFLOW_PROVIDER=mock python -m feishu_workbench reconcile
```

输出文件：

- `outputs/qa_example.md`
- `outputs/pre_meeting_go_no_go.md`
- `outputs/post_meeting_actions.md`
- `outputs/reconcile_board_summary.md`

### 方式 B：真实飞书文档只读验证

这个模式用于验证官方 `larksuite/cli` 读取真实测试飞书文档。只读模式不会发送消息、不会创建任务、不会写 Base。

环境要求：

- Python 3.10+
- Node.js / npm
- 官方 `@larksuite/cli`
- 一个无敏感信息的测试飞书文档

安装官方 CLI：

```bash
npm install -g @larksuite/cli
lark-cli --version
```

如果 npm postinstall 下载 native binary 卡住，可参考 `docs/lark_cli_setup_check.md` 中记录的手动校验安装方式。

初始化和授权：

```bash
lark-cli config init --new
lark-cli auth login --recommend
lark-cli doctor
```

可选：如果本机配置了代理，但希望 CLI 请求不经过代理，可先确认直连可用，再加：

```bash
export LARK_CLI_NO_PROXY=1
```

准备环境变量：

```bash
cp .env.example .env
```

编辑 `.env`，至少设置：

```bash
MEETINGFLOW_PROVIDER=lark_cli
FEISHU_DOC_TEST_TOKEN=<your_test_doc_token_or_url>
```

当前工程不会自动读取 `.env` 文件。运行前需要把它导入 shell：

```bash
set -a
source .env
set +a
```

验证飞书文档读取：

```bash
lark-cli docs +fetch --api-version v2 --as user --doc "$FEISHU_DOC_TEST_TOKEN" --format json
```

运行 Agent：

```bash
python -m feishu_workbench qa --question "MeetingFlow Agent 的真实飞书文档读取链路测试结论是什么？"
```

如需验证会议纪要，只能使用真实测试会议产生的 `minute_token`：

```bash
export FEISHU_MINUTES_TEST_TOKEN=<your_test_minutes_token>
lark-cli vc +notes --as user --minute-tokens "$FEISHU_MINUTES_TEST_TOKEN" --format json
```

会议纪要读取目前还没有完成端到端验证。

## 测试

```bash
python -m unittest discover -s tests
```

当前测试覆盖：

- mock 数据加载
- QA 流程
- 会前背景包
- 会后行动项
- 推进总表对账
- `LarkCliProvider` 环境变量读取
- `lark-cli docs +fetch v2` payload 归一化

## 项目资料

可进一步阅读：

- `docs/scene_definition.md`：场景定义
- `docs/data_generation_strategy.md`：数据生成策略
- `docs/mvp_scope.md`：当前 MVP 范围
- `docs/architecture.md`：技术架构
- `docs/demo_walkthrough.md`：Demo 演示路径
