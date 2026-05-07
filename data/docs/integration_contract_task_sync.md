# 任务同步接口契约

## 目标

行动项同步只生成预览建议，不直接写入正式任务系统。接口契约用于约束字段完整性、幂等逻辑和错误处理。

## 字段契约

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| title | 是 | 行动项标题，建议不超过 36 字 |
| owner | 是 | 负责人显示名，演示环境使用 mock 姓名 |
| due_date | 是 | 截止日期，格式 YYYY-MM-DD |
| priority | 是 | P0/P1/P2 |
| source_meeting | 是 | 来源会议 minutes_id |
| evidence | 是 | 证据片段或文档链接 |
| preview_status | 是 | pending_confirmed/rejected/created |

## 幂等规则

- 同一 source_meeting、owner、title 相同视为重复候选。
- 如果 due_date 改变，生成 conflict，而不是覆盖旧任务。
- 如果 priority board 中已经存在相同 item 但状态不同，交给 reconcile 输出冲突。

## 错误处理

- 缺少 owner：进入 needs_owner 状态。
- 缺少 due_date：进入 needs_due_date 状态。
- 缺少 evidence：进入 evidence_missing 状态。
- 权限检查失败：直接阻断，不生成预览。

source_id: doc_integration_contract
