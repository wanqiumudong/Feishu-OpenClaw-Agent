# 需求追踪矩阵：智能会议纪要 2.0

## 目标

本矩阵用于把 PRD、评审会议、测试验收和上线检查串成可追踪链路。每个需求必须能够回答三个问题：来自哪里、由谁验收、上线后如何观察。

## 需求清单

| req_id | 需求 | 负责人 | 验收口径 | 来源 |
| --- | --- | --- | --- | --- |
| REQ-01 | 会议摘要按“背景、结论、未决问题”输出 | 林舟 | 20 条人工样本中 17 条以上被产品接受 | product_review_minutes |
| REQ-02 | 行动项抽取必须包含负责人、截止时间、事项、来源链接 | 周岚 | 字段完整率 >= 90% | prd_meeting_minutes_2 |
| REQ-03 | 风险提示只引用会议中明确表达的阻塞，不做推断式扩写 | 陈墨 | 误召回率 <= 8% | evaluation_calibration_minutes |
| REQ-04 | 同一会议生成的任务默认进入预览态，不自动写入正式任务系统 | 王越 | 预览确认日志覆盖率 100% | requirement_alignment_minutes |
| REQ-05 | 灰度用户可看到“为什么生成该行动项”的证据片段 | 苏晴 | 客服 FAQ 中解释成本下降 | customer_feedback_review_minutes |
| REQ-06 | 私密会议、跨部门会议和外部客户会议走权限过滤 | 何澈 | 权限越权用例 0 个 | security_review_minutes |
| REQ-07 | 60 分钟会议处理链路 P95 <= 9 秒 | 周岚 | 压测报告连续两轮达标 | architecture_review_minutes |
| REQ-08 | 回滚开关支持 10 分钟内关闭任务同步 | 赵一诺 | 灰度演练通过 | release_sop_gray_rollback |

## 变更控制

- 任何新增上线能力必须补充 req_id、owner、source、acceptance case。
- 自动周报、跨空间聚合、客户群自动发送仍在非本轮范围内。
- 如果会议纪要和任务看板冲突，以带来源证据的会议纪要为优先事实源，再由项目经理确认。

## 当前缺口

- REQ-05 的证据片段 UI 还缺少移动端截图。
- REQ-07 的 60 分钟会议样本仍集中在内部评审类会议，客户复盘样本不足。
- REQ-08 的回滚演练只覆盖任务同步，尚未覆盖摘要生成降级。

source_id: doc_requirements_traceability
