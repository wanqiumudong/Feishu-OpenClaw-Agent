# MeetingFlow Agent

MeetingFlow Agent 是一个面向飞书办公场景的 Agent 原型，聚焦会议和项目推进。

它解决的是一个很具体的问题：团队信息分散在文档、会议纪要、群聊、任务、日历和推进表里，会前要反复翻资料，会后要手工整理行动项，推进过程中还要不断对账。

当前项目把这些动作整理成四类可运行功能：

- 带来源问答
- 会前背景包
- 会后行动项整理
- 推进总表对账

项目当前既可以本地运行，也可以作为飞书 Bot webhook 后端接收消息事件。

## 功能展示

### 1. 带来源问答

根据文档、会议纪要、群聊、任务和推进表回答问题，并保留来源。

### 2. 会前背景包

围绕指定会议自动整理会议目标、参会人、必读资料、近期决策和未关闭风险。

### 3. 会后行动项整理

从会议纪要中抽取决策、负责人、截止时间和任务预览，减少手工整理成本。

### 4. 推进总表对账

对比任务、群聊和推进表内容，发现新增事项、状态变化和阻塞原因。

### 5. GraphRAG 与证据组织

项目支持 Evidence Graph、GraphRAG Local Search 和 Global Search，用于展示一个问题背后的文档、纪要、任务、风险和推进关系，而不是只给一句结论。

### 6. 飞书 Bot 形态

项目提供 `meetingflow-server`，可以作为飞书 Bot 后端接收事件，再调用同一套 Agent runtime 返回文本或卡片结果。

## 当前状态

当前版本已经完成：

- 本地 mock 数据 demo
- Agent runtime 和 workflow 编排
- GraphRAG 检索与证据图
- 飞书 Bot webhook 服务
- 飞书卡片预览
- 真实飞书测试文档只读 smoke
- dry-run 写入保护
- 单元测试和批量评测 harness

当前还没有完成：

- 真实长连接事件订阅
- 真实任务写入和 Base 写入确认流
- OpenClaw channel
- 多用户权限和生产部署

## 仓库结构

```text
data/                 # mock 办公数据
src/                  # Agent、Bot 服务、provider、retriever、pipeline
tests/                # 单元测试与集成测试
scripts/              # demo 脚本
pyproject.toml        # Python package 配置
```

运行命令后会在本地生成 `outputs/` 和 `reports/`。这两个目录只用于本地演示和评测，不作为公开展示内容。

## 安装

环境要求：

- Python 3.10+

安装命令：

```bash
python -m pip install -e .
```

## 本地运行

先运行四条核心命令：

```bash
meetingflow qa --question "上次技术评审会的主要风险是什么？"
meetingflow pre-meeting --event go_no_go_review
meetingflow post-meeting --minutes go_no_go_minutes
meetingflow reconcile
```

如果需要进一步查看工程能力，可以继续运行：

```bash
meetingflow evidence-graph --topic "Go/No-Go 灰度发布"
meetingflow graphrag --mode local --question "Go/No-Go 灰度发布有哪些阻塞？"
meetingflow graphrag --mode global --question "项目当前主要主题和风险是什么？"
meetingflow inspect-runtime
meetingflow card-preview --workflow pre_meeting
meetingflow agent-report
```

完整脚本：

```bash
bash scripts/run_full_demo.sh
```

## 飞书 Bot 使用方式

如果飞书后台选择“长连接接收事件”，启动长连接客户端：

```bash
meetingflow-feishu-ws
```

如果飞书后台选择“回调地址”模式，启动 HTTP 服务：

```bash
meetingflow-server --host 0.0.0.0 --port 8080
```

回调地址模式需要把飞书开发者后台的事件订阅地址配置为：

```text
https://<public-domain>/feishu/events
```

配置完成后，用户可以在飞书测试群中直接触发 Agent。
本地命令行主要用于开发、调试、评测和录屏。

## 真实飞书验证

项目支持通过官方 `lark-cli` 读取飞书测试对象，当前已完成测试文档读取验证。

示例：

```bash
MEETINGFLOW_PROVIDER=feishu \
FEISHU_DOC_URLS="<test-doc-url>" \
meetingflow real-smoke
```

消息发送和其他写操作默认关闭。只有显式打开 `MEETINGFLOW_REAL_WRITE=1` 时，才会写入测试群或其他测试对象。

## 测试

运行单元测试：

```bash
python -m unittest discover -s tests
```

运行批量评测：

```bash
meetingflow-eval full --scale 10
```

当前评测覆盖：

- QA、会前背景包、会后行动项、推进总表对账
- GraphRAG Local Search 和 Global Search
- Agent trace
- 卡片预览
- 事件路由
- dry-run safety
- 合成数据规模测试
- 真实飞书 smoke check

## 参考

- Microsoft GraphRAG: https://github.com/microsoft/graphrag
- GraphRAG Local Search: https://microsoft.github.io/graphrag/query/local_search/
- GraphRAG Global Search: https://microsoft.github.io/graphrag/query/global_search/
