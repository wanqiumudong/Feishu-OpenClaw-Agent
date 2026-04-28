# 技术架构

## 分层

```text
数据提供层 -> 归一化层 -> 检索层 -> 知识产物生成层 -> 分发渲染层
```

## 数据提供层

`MockProvider` 从本地 `data/` 目录读取 synthetic 数据，输出统一 `DataBundle`。

`LarkCliProvider` 是真实只读接入边界。当前已支持在本地安装并授权 `lark-cli` 后读取测试文档，并将结果归一化为 `KnowledgeItem`；会议纪要读取入口已预留，但仍等待真实 `minute_token` 做端到端验证。消息发送、任务创建和 Base 写入仍保持禁用。

## 归一化层

`retrieval/indexer.py` 把 Docs、Minutes、Chat、Tasks、Base 统一为 `KnowledgeItem`。每个条目包含标题、内容、类型、来源路径、标签和元数据。

## 检索层

`retrieval/retriever.py` 使用关键词打分召回相关资料。当前不使用向量数据库或 LLM，便于离线运行和测试。

## 知识产物生成层

- `qa.py`：带来源问答。
- `pre_meeting_brief.py`：会前背景包。
- `post_meeting_actions.py`：会后行动项和任务创建预览。
- `reconcile_board.py`：推进总表对账预览。

## 分发渲染层

`distribution/renderer.py` 统一渲染 Markdown。后续接入飞书时，可替换为消息卡片、文档写入或 Base 记录写入。

## Future Integration Architecture

后续真实接入不应绕过现有分层。推荐演进方向：

```text
Trigger -> Orchestrator -> Provider -> Retriever -> Pipeline -> Renderer -> Distributor -> Evaluator
```

- Trigger：承接手动 CLI、定时、飞书事件和未来 OpenClaw channel。
- Orchestrator：根据触发类型选择会前、会后、对账或 QA workflow。
- Provider：保留 `MockProvider`，继续加固真实只读 `LarkCliProvider`；必要时再补 `FeishuSdkProvider`。
- Distributor：单独负责机器人文本、飞书卡片、任务 dry-run 和 Base dry-run，避免 pipeline 直接写真实对象。
- Evaluator：记录 QA、会前、会后和对账结果的来源命中、人工评分和耗时。

当前这些模块仍是规划方向，不代表已经完成真实飞书接入或 OpenClaw 接入。
