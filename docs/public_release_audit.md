# 公开发布检查清单

## 检查范围

本文记录 MeetingFlow Agent bootstrap 仓库在公开发布前的清理边界。

## 公开仓保留内容

- 项目 README：说明工作范围、部署方法、demo 命令、当前边界和安全说明。
- 可复现的本地 mock 办公数据。
- 最小 Agent 框架源码。
- smoke tests 和 provider tests。
- 场景、架构、接入路线、编排计划、权限安全、评测计划、roadmap 和 backlog 文档。
- 基于 mock 数据生成的 demo outputs。

## 公开仓排除内容

- 本地 `.env` 文件。
- 真实飞书 token、cookie、App Secret、user open id、chat id、document token 和原始 API 日志。
- 内部工作日志和过程性草稿。
- 个人阶段汇报草稿。
- Python 缓存、egg-info 元数据、虚拟环境和本地构建产物。

## 当前已验证状态

- mock demo workflow 可在本地运行。
- 官方 `lark-cli` 文档只读路径已用无敏感测试文档验证。
- `LarkCliProvider` 会将真实文档来源脱敏为 `feishu://docs/...`，不暴露原始文档 token。
- 真实会议纪要、事件触发、消息/卡片分发、Task 写入、Base 写入和 OpenClaw channel 仍是后续工作。

## 公开表述边界

本仓库应被理解为 bootstrap 工程 demo，而不是生产级飞书部署。公开材料只能描述已验证行为，不能暗示真实用户使用、线上指标或企业级部署已经完成。
