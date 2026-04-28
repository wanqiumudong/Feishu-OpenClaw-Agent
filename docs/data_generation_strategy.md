# 数据生成策略

## 生成链路

本 bootstrap 使用四层数据生成思路：

1. 真相层：用 `data/ground_truth/project_truth.json` 定义项目背景、角色、决策、风险、时间线、会议和任务关系。
2. 多类飞书对象扩写：从真相层扩写出 Docs、Minutes、Chat、Tasks、Calendar 和 Base 风格数据。
3. 一致性校验：任务 owner、会议结论、风险状态、回滚阈值和截止时间尽量保持一致。
4. 评测预留：保留 QA 问题、会前资料、会后行动项和推进表差异，用于 smoke test 与 Demo 输出。

## 数据类型

- Docs/Wiki 风格文档：6 份 Markdown。
- Minutes 会议纪要：3 份 Markdown。
- 群聊记录：50 条 JSONL。
- 任务：14 条 JSON。
- 日历事件：4 条 JSON。
- Base 推进总表：CSV + JSON。

## 风险说明

所有数据均为模拟数据，不涉及真实企业信息、真实用户隐私或真实飞书租户内容。人物、项目、会议和任务均为虚构，仅用于比赛 Demo bootstrap。
