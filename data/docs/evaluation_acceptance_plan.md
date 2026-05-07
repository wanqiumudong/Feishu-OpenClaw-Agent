# 评测与验收方案

## 评测目标

评测不以单个 demo 跑通为准，而是覆盖准确性、来源可追踪、状态 reconcile 和规模稳定性四类能力。

## 指标定义

| 指标 | 目标 | 说明 |
| --- | --- | --- |
| action_item_precision | >= 0.88 | 抽取出的行动项是否真实存在于会议或聊天证据中 |
| action_item_recall | >= 0.82 | 关键行动项是否被覆盖 |
| owner_due_date_completeness | >= 0.90 | 负责人和截止时间完整率 |
| source_coverage | >= 0.95 | 每个结论是否有 source |
| conflict_detection_rate | >= 0.85 | 对看板/任务/聊天不一致的识别率 |
| permission_violation | 0 | 权限越权不可接受 |

## 样本分层

- 需求评审类：范围决策、延期项和不上线项。
- 技术评审类：性能、接口、降级和监控。
- 安全评审类：权限、日志、审计和脱敏。
- 客户反馈类：误召回、解释成本和外部会议边界。
- 上线复盘类：指标、回滚、遗留问题和放量决策。

## 验收流程

1. 陈墨冻结评测样本清单。
2. 周岚提供最新 extractor 输出。
3. 王越运行 reconcile 用例并导出冲突列表。
4. 林舟确认产品可接受误差边界。
5. 何澈检查权限相关失败是否为 0。

source_id: doc_evaluation_acceptance
