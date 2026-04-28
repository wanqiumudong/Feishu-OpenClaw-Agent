# Backlog

## P0

| 任务 | 描述 | 涉及文件 | 依赖 | 验收标准 | 难度 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| 整理展示材料 | 补齐录屏脚本、截图清单、3 分钟讲解路径 | `docs/demo_walkthrough.md`、新增 demo script | 当前 outputs | 能按 QA -> 会前 -> 会后 -> 对账讲清楚 | S | 表述夸大 |
| 加固 mock MVP | 保持现有四条 demo 稳定，修正文档不一致 | `README.md`、`docs/`、`tests/` | 当前 mock 数据 | tests 通过，outputs 可复现 | S | 过度重构 |
| 完善 evaluation cases | 把评测草案落成结构化用例 | `docs/evaluation_plan.md`、未来 `data/evaluation/` | 当前 demo 输出 | 至少 10 个用例，有标准答案/评分点 | M | 标注口径不一致 |
| 接入真实文档只读读取 | 用测试文档替换部分 mock docs | `providers/lark_cli_provider.py`、未来 provider config | lark-cli 配置和授权 | 可读取测试文档并转 `KnowledgeItem` | M | 权限和真实 payload 字段需验证 |
| 接入真实会议纪要只读读取 | 用测试会议纪要替换部分 mock minutes | `providers/lark_cli_provider.py` | lark-cli minutes 能力 | 可读取测试纪要并转 `KnowledgeItem` | M | 会议纪要 token 和权限不稳定 |

## P1

| 任务 | 描述 | 涉及文件 | 依赖 | 验收标准 | 难度 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| 日历触发 | 读取日历事件并触发会前背景包 | 未来 `triggers/calendar_trigger.py` | 只读日历权限 | 能 dry-run 生成 workflow 请求 | M | 重复触发 |
| 机器人文本消息分发 | 将 Markdown 发送到测试群 | 未来 `distribution/feishu_distributor.py` | 测试群和发送权限 | 默认 dry-run，测试群可发送 | M | 泄露群 ID 或内容 |
| 卡片模板 | 将会前/会后/对账结果转卡片草案 | 未来 `distribution/card_renderer.py` | Markdown 输出稳定 | 生成可预览 JSON 草案 | M | 卡片过长或字段不兼容 |
| 任务创建 dry-run | 将 ActionPreview 转任务创建请求预览 | `post_meeting_actions.py`、未来 task distributor | 行动项抽取稳定 | 不写真实任务，只输出请求预览 | M | 误创建任务 |
| Base 写入 dry-run | 将对账结果转 Base upsert 预览 | `reconcile_board.py`、未来 base distributor | 对账结果稳定 | 不写真实 Base，只输出请求预览 | M | 字段映射错误 |

## P2

| 任务 | 描述 | 涉及文件 | 依赖 | 验收标准 | 难度 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| 完整事件订阅 | 接会议结束、消息、任务状态事件 | 未来 `triggers/`、SDK provider | SDK/OpenAPI 权限 | 事件可去重、失败可重试 | L | 回调安全和权限复杂 |
| OpenClaw channel | 将稳定 workflow 暴露给 OpenClaw | 未来 channel adapter | 读/生成/分发链路稳定 | 可作为入口调用现有 workflow | L | 入口复杂，影响主线 |
| 轻量知识图谱 / GraphRAG 增强 | 用实体关系增强跨对象检索 | 未来 `retrieval/graph_indexer.py` | 评测用例充足 | QA 来源命中率提升 | L | 过早复杂化 |
| 多用户权限和身份路由 | 区分不同用户和可见内容 | provider/config/auth 模块 | 真实租户权限模型 | 不越权返回资料 | L | 权限边界高风险 |
| 更复杂的评测看板 | 用 Base 或本地表记录评测结果 | 未来 `evaluation/` | gold set 完成 | 可对比版本结果 | M | 指标维护成本 |

## Backlog 使用规则

- P0 只做展示、评测和只读接入。
- P1 才开始分发和 dry-run 写操作。
- P2 放到主线稳定后再做。
- 任何写操作都必须先 dry-run，再测试对象，再人工确认。
