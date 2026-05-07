# 架构方案：会议结构化抽取流水线

## 范围

本方案描述智能会议纪要 2.0 的离线 mock 架构与真实接入时的边界。复赛演示中只使用 mock 数据，不接入真实企业消息、真实 token 或真实人员身份。

## 数据流

1. 会议结束后，纪要文本进入 `transcript_ready` 队列。
2. Extractor 生成摘要、决策、行动项、风险和证据片段。
3. Resolver 将负责人、任务状态和相关文档做轻量归一。
4. Reconciler 对任务表、聊天补充和 priority board 做冲突检查。
5. Preview Publisher 只生成待确认动作，不自动写入正式系统。

## 服务边界

- Extractor 只处理单场会议上下文，不跨会议主动推断。
- Resolver 可以读取项目 docs、minutes、calendar 和 task board，但必须保留 source。
- Reconciler 不直接修改用户任务，只输出冲突、漏项和建议动作。
- Publisher 在演示环境中只写 mock output，不访问真实 Feishu API。

## 性能目标

| 场景 | P95 目标 | 备注 |
| --- | --- | --- |
| 30 分钟会议 | <= 6 秒 | 常规评审会 |
| 60 分钟会议 | <= 9 秒 | 长会议，需要分段摘要 |
| 90 分钟会议 | <= 14 秒 | 暂不作为灰度放量 gate |

## 工程风险

- 长会议分段摘要可能造成行动项重复。
- 人名归一依赖上下文，聊天中的简称可能映射错误。
- priority board 故意存在漏项，不能被当作唯一事实源。

## 当前决策

技术评审决定先保留同步抽取链路，暂不引入异步多模型投票；如果 60 分钟样本连续两轮 P95 超过 9 秒，再切换为分段缓存方案。

source_id: doc_architecture_pipeline
