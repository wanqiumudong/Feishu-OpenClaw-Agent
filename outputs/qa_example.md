# QA 示例：带来源回答

**问题**：上次技术评审会的主要风险是什么？

## 答案

上次技术评审会主要识别了三类风险：

- 长会议逐字稿过长，可能导致抽取延迟增加。
- 非任务型承诺句容易被误判为行动项。
- 文档和会议纪要标题不一致时，知识链接召回可能不稳定。

## 来源
- [base] 推进表：技术风险同步推进表：`data/base/priority_board.csv`
- [doc] 测试清单：质量评测与上线前检查项：`data/docs/test_checklist_quality.md`
- [minutes] 技术评审会纪要：`data/minutes/tech_review_minutes.md`
- [base] 推进表：误召回样本集：`data/base/priority_board.csv`
- [base] 推进表：长会议压测报告：`data/base/priority_board.csv`
