# MeetingFlow Evaluation

MeetingFlow Agent 的评测不以单次 demo 为准，而是用 harness 检查四类能力是否稳定。

## 评测目标

- 回答是否命中标准问题。
- 输出是否保留正确来源。
- 会前背景包是否覆盖目标、资料、历史决策和风险。
- 会后行动项是否抽对负责人、截止时间和背景。
- 推进表对账是否发现新增事项、状态变化和阻塞。
- 噪声数据下是否仍能给出可用结果。
- 合成大规模数据下是否能正常运行。
- 真实飞书测试对象是否能完成读取和写入 smoke check。
- 证据图是否能把来源、风险、任务和推进表关系解释清楚。
- GraphRAG Local Search 是否能从实体扩展到关系、文本片段和社区报告。
- GraphRAG Global Search 是否能使用社区报告归纳全局主题。
- Agent runtime 是否记录完整 tool trace。
- 飞书卡片 JSON 是否可渲染并通过 dry-run SDK 分发。
- webhook 和 mock 事件是否能路由到正确工作流。
- 写入和分发是否默认保持 dry-run。

## 运行命令

```bash
python -m unittest discover -s tests
python -m unittest tests.test_server -v
meetingflow-eval accuracy
meetingflow-eval robustness
meetingflow-eval scale --scale 200
meetingflow-eval full --scale 500
meetingflow-eval real
meetingflow-eval graphrag --scale 100
meetingflow-eval agent-trace
meetingflow-eval cards
meetingflow-eval events
meetingflow-eval safety
meetingflow evidence-graph --topic "Go/No-Go 灰度发布"
meetingflow submission-pack
```

评测结果会写入本地 `reports/`。该目录用于实验记录，不提交到公开仓。

## 指标

| 指标 | 说明 |
|---|---|
| QA answer hit rate | 标准问题中关键事实是否命中 |
| Source coverage | 检索是否能召回对应来源 |
| Action owner accuracy | 行动项负责人是否正确 |
| Due date accuracy | 截止时间是否正确 |
| Reconcile match | 推进表更新是否识别正确 |
| Robustness score | 噪声和冲突数据下是否保持可用 |
| Scale latency | 合成规模数据下的运行耗时 |
| Real Feishu smoke | 当前本地授权和测试对象是否可用 |
| Evidence graph sanity | 证据图是否包含来源、风险、任务和推进表线索 |
| GraphRAG local context | Local Search 是否包含 text units、entities、relationships 和 community reports |
| GraphRAG global context | Global Search 是否通过 community reports 做全局归纳 |
| Agent trace completeness | runtime 是否记录 run_id、工具调用、输出和 dry-run 状态 |
| Card schema validity | 飞书卡片 JSON 是否包含 header、elements 和 action |
| Event routing accuracy | webhook 和 mock 事件是否触发正确 workflow |
| Bot service health | `/health`、challenge 和消息事件处理是否正常 |
| Dry-run safety | 分发和写入是否默认 dry-run |

## 当前边界

当前 harness 使用 mock 数据作为主评测集。真实飞书评测只面向测试对象，不代表生产环境指标，也不包含用户实测反馈。

LLM 评测采用工程校验和规则评分为主。当前已覆盖 context recall proxy、entity recall proxy、tool correctness、trace completeness 和 dry-run safety。后续可以接入 Ragas 或 DeepEval，补充 faithfulness、answer relevancy 和 LLM-as-judge。
