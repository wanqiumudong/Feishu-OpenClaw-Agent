# MeetingFlow Agent

MeetingFlow Agent 是一个面向飞书 AI 校园挑战赛的办公场景智能助手原型，聚焦 会议与项目推进场景。

它把本地模拟的飞书协作数据整理成四条可运行的 Agent 工作流：

- 带来源问答：根据文档、会议纪要、群聊、任务和推进表回答问题。
- 会前背景包：为指定会议生成目标、参会人、必读资料、历史决策和风险。
- 会后行动项：从会议纪要中抽取决策、负责人、截止时间和任务创建预览。
- 推进总表对账：根据任务、会议和群聊线索生成项目状态更新预览。

## Done
- 默认使用本地 mock 数据，开箱即可运行。
- 真实会议纪要读取、事件触发、消息卡片、任务写入、Base 写入和 OpenClaw channel 仍未完成。

## Repository Layout

```text
data/                 # mock 办公数据，支撑本地 demo
src/                  # Agent 框架、provider、retriever、pipeline 和 renderer
tests/                # smoke tests
pyproject.toml        # Python package 配置
```

运行 demo 后会在本地生成 `outputs/`，该目录不作为展示内容提交。

## Quick Start

环境要求：

- Python 3.10+

安装：

```bash
python -m pip install -e .
```

运行四条 mock demo：

```bash
meetingflow qa --question "上次技术评审会的主要风险是什么？"
meetingflow pre-meeting --event go_no_go_review
meetingflow post-meeting --minutes go_no_go_minutes
meetingflow reconcile
```

每条命令都会在终端打印 Markdown，并在本地写入 `outputs/`。

## Tests

```bash
python -m unittest discover -s tests
```

当前测试覆盖：

- mock 数据加载
- QA 流程
- 会前背景包
- 会后行动项
- 推进总表对账

## TODO
- 真实会议纪要端到端读取
- 事件订阅和自动触发
- 飞书机器人消息或卡片投递
- 飞书任务创建
- Base 写入
- OpenClaw channel
- 多用户权限和生产部署
