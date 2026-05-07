# 评测口径校准会纪要

minutes_id: evaluation_calibration_minutes
event_id: evaluation_calibration
date: 2026-04-24

## 会议目标

确定行动项抽取、风险提示、来源覆盖和 reconcile 的评测口径，避免只用单条 demo case 判断效果。

## 参会人

陈墨、林舟、周岚、王越、何澈

## 关键决策

- action item precision 和 recall 分开统计，不再用单一通过率描述。
- 风险提示必须能回溯到会议纪要或聊天证据，不允许凭项目常识推断。
- source coverage 低于 95% 时不得扩大灰度。
- 权限相关失败不计入平均分，任何失败均为阻断。

## 讨论摘要

陈墨提出评测集需要覆盖需求评审、技术评审、安全评审、客户反馈复盘和上线复盘五类会议。王越要求 reconcile 用例故意保留状态冲突、缺 owner、blocked 无 blocker 和 due date 不一致四种情况。周岚确认 extractor 输出会带 evidence_id，便于人工复核。

## 行动项

- [ ] 陈墨在 2026-04-25 前冻结 60 条人工标注样本。
- [ ] 王越在 2026-04-25 前补充 priority board 冲突样例。
- [ ] 周岚在 2026-04-26 前导出 evidence_id 字段。
- [ ] 何澈在 2026-04-26 前复核权限评测用例。

## 风险

- 客户反馈样本数量不足，可能导致误召回评估偏乐观。

source_id: minutes_evaluation_calibration
