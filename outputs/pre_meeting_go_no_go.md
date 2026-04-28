# 会前背景包：智能会议纪要 2.0 上线前 Go/No-Go

- 时间：2026-04-27T16:00:00+08:00 - 2026-04-27T17:00:00+08:00
- 会议目的：确认是否进入 20% 灰度，并明确回滚阈值和最后行动项。
- 参会人：林舟、周岚、陈墨、苏晴、王越

## 必读资料
- release_sop_gray_rollback.md
- faq_user_feedback.md
- test_checklist_quality.md

## 最近关键决策
- 首版只上线结构化摘要、行动项抽取和风险提示，不上线自动周报推送。
- 抽取服务采用异步队列，会议结束后写入结构化结果表，前端只读取已确认字段。
- 本周五进入 20% 灰度，失败率超过 3% 或 P95 延迟超过 12 秒时回滚。

## 未关闭风险
- 转写后处理 P95 延迟偏高（owner：周岚，阻塞：压测样本不足，长会议场景 P95 仍接近 11 秒）
- 行动项抽取误召回（owner：陈墨，阻塞：测试集中非任务型承诺句容易被误判为待办）
- 客服 FAQ 尚未覆盖回滚说明（owner：苏晴，阻塞：灰度沟通口径仍待产品确认）

## 待确认问题
- 是否确认本周五进入 20% 灰度？
- P95 接近 11 秒是否仍可接受？
- 客服 FAQ 回滚说明是否能在灰度前补齐？
- 推进总表中是否还有漏记的行动项？

## 来源
- [doc] 项目概览：智能会议纪要 2.0 升级项目：`data/docs/project_overview.md`
- [minutes] 上线前 Go/No-Go 会议纪要：`data/minutes/go_no_go_minutes.md`
- [minutes] 产品评审会纪要：`data/minutes/product_review_minutes.md`
- [doc] 上线 SOP：灰度发布与回滚流程：`data/docs/release_sop_gray_rollback.md`
- [doc] FAQ：常见问题与用户反馈：`data/docs/faq_user_feedback.md`
- [chat] 群聊消息 msg_047 - 林舟：`data/chats/project_chat.jsonl`
- [minutes] 技术评审会纪要：`data/minutes/tech_review_minutes.md`
- [doc] PRD：智能会议纪要 2.0：`data/docs/prd_meeting_minutes_2.md`
