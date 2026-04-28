# Demo Walkthrough

## 1. 会前触发

运行：

```bash
python -m feishu_workbench pre-meeting --event go_no_go_review
```

预期效果：生成“智能会议纪要 2.0 上线前 Go/No-Go”的会前背景包，包含会议目的、参会人、必读资料、关键决策、未关闭风险、待确认问题和来源。

## 2. 会后触发

运行：

```bash
python -m feishu_workbench post-meeting --minutes go_no_go_minutes
```

预期效果：从 Go/No-Go 会议纪要中抽取行动项，生成任务创建预览，包含事项、负责人、截止时间、背景资料和来源。

## 3. QA 查询

运行：

```bash
python -m feishu_workbench qa --question "上次技术评审会的主要风险是什么？"
```

预期效果：返回技术评审会识别出的主要风险，并附带来源。

## 4. 推进总表更新预览

运行：

```bash
python -m feishu_workbench reconcile
```

预期效果：对比任务、群聊线索和已有推进表，输出新增事项、状态更新和阻塞补全。
