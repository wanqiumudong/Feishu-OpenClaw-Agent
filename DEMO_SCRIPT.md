# MeetingFlow Agent 录屏脚本

目标时长：5 到 7 分钟。录屏重点是展示“会议与项目推进工作流 Agent”的工程闭环，而不是包装成已经上线的生产系统。

## 0. 录屏前约定

- 使用本地 mock 数据作为主 demo 数据源。
- 真实飞书只展示测试边界和 dry-run 保护，不展示 token、真实组织数据或真实人员信息。
- 全程不执行 `--send`、`--create-tasks`、`--upsert-base`、`real-smoke` 或任何真实写入命令。
- 如需一键预检，先运行：

```bash
bash scripts/run_full_demo.sh
```

## 1. 项目介绍，约 45 秒

画面：打开 `README.md` 首页。

讲解要点：

- 项目名是 MeetingFlow Agent，面向飞书办公场景中的会议和项目推进。
- 它不是泛化 knowledge base，也不是单轮 chatbot。当前聚焦四个流程：带来源 QA、会前背景包、会后行动项、推进总表对账。
- 工程边界是 mock-driven：先用可复现的本地数据固定流程、来源约束、字段校验和评测，再把真实飞书读取与测试写入隔离在 provider/distributor 层。
- 当前录屏展示的是可复现原型和测试边界，不代表生产部署或用户实测指标。

可展示位置：

```bash
sed -n '1,90p' README.md
```

## 2. 数据规模展示，约 45 秒

画面：终端展示 mock 数据对象数量。

命令：

```bash
PYTHONPATH=src python -c 'from evaluation.generate_data import main; main()' summary --format markdown
```

讲解要点：

- 数据覆盖 docs、minutes、chat messages、tasks、calendar events 和 base-style board rows。
- 这些对象模拟会议前后常见的信息分散状态：文档里有背景，纪要里有决策，群聊里有风险变化，任务和表格里有执行状态。
- 后面的四条 pipeline 都从同一批对象读取，不是每个 demo 单独硬编码输出。

预期画面：出现 `MeetingFlow Dataset Summary`，并列出各类对象数量。

## 3. 带来源 QA，约 60 秒

画面：运行 QA 命令并展示输出的 Sources。

命令：

```bash
PYTHONPATH=src python -c 'from main import main; main()' qa --question "上次技术评审会的主要风险是什么？"
```

讲解要点：

- QA 的目标不是只给一句答案，而是把答案和来源一起给出来。
- 可以强调输出中的 `Sources`：回答来自哪些文档、纪要或群聊线索。
- 这里展示 Agent 的第一层能力：从多源材料中召回依据，并把结论压缩成可读答案。

切换话术：

- “如果评委只看一次问答，这像 RAG；但后面三个流程会展示它如何进入会议和项目动作。”

## 4. 会前背景包，约 60 秒

画面：生成 go/no-go 会议背景包。

命令：

```bash
PYTHONPATH=src python -c 'from main import main; main()' pre-meeting --event go_no_go_review
```

讲解要点：

- 会前背景包把会议目标、参会人、必读资料、历史决策、风险和待确认事项放在同一页。
- 适合录屏时停在“未关闭风险”和“必读资料”两段，说明它减少会前翻资料时间。
- 输出仍然是预览，不直接写入飞书，便于人工确认后再发送。

## 5. 会后行动项，约 60 秒

画面：从会议纪要抽取行动项。

命令：

```bash
PYTHONPATH=src python -c 'from main import main; main()' post-meeting --minutes go_no_go_minutes
```

讲解要点：

- 重点展示 owner、due date、background 和 source。
- 这一步体现从“会议记录”到“执行任务预览”的转换。
- 当前脚本不使用 `--create-tasks`，因此不会创建真实任务。真实测试写入也默认 dry-run，需要本地显式打开才会写测试对象。

## 6. 推进对账，约 60 秒

画面：生成推进总表对账结果。

命令：

```bash
PYTHONPATH=src python -c 'from main import main; main()' reconcile
```

讲解要点：

- 展示新增事项、状态变化和阻塞补全。
- 对账不是改表，而是生成可审核的更新建议。
- 这里体现多源交叉：任务状态、群聊线索、会议纪要和推进表之间互相校验。
- 当前录屏不使用 `--upsert-base`，不会写入测试 Base。

## 7. Harness 评测，约 75 秒

画面：运行 full harness，scale 用小值保证录屏稳定。

命令：

```bash
PYTHONPATH=src python -c 'from evaluation.run_eval import main; main()' full --scale 20 --output-dir reports/demo_full
```

讲解要点：

- 评测不是只跑一条 demo，而是覆盖 accuracy、robustness 和 scale。
- Accuracy 检查标准问题、会前背景包、会后行动项和推进表对账是否命中预期。
- Robustness 检查噪声和冲突数据下是否仍能产出可用结果。
- Scale 使用合成数据扩展对象数量，检查 workflow 在更大 mock 数据下是否能跑通。
- 录屏用 `--scale 20` 是为了时间稳定；提交或本地复核可以提高 scale。

预期画面：出现 `Full Harness Summary`，并包含 Accuracy、Robustness、Scale 三段。

## 8. Agent 工程化报告，约 45 秒

画面：展示 Agent 分层、工作流 trace 和写入保护。

命令：

```bash
PYTHONPATH=src python -c 'from main import main; main()' agent-report
```

讲解要点：

- 这不是另一个 demo，而是把 Agent 的工程结构一次性展开。
- 重点看 AI 分工：Retriever、Evidence Curator、Workflow Planner、Extractor、Reconciler、Distributor、Evaluator。
- 工作流 trace 展示每个流程召回了哪些来源，说明系统不是单点 prompt，而是有证据组织和评测保护。

## 9. 真实飞书测试边界，约 45 秒

画面：回到 `README.md` 或 `SUBMISSION.md` 中的安全边界段落，不运行真实写入。

讲解要点：

- 真实飞书接入被隔离在 provider 和 distributor 层，pipeline 不直接依赖真实接口。
- 当前支持测试对象 smoke check 和 dry-run 写入预览，但录屏默认只展示 mock workflow。
- 不提交 `.env`、token、secret、真实 user id 或真实业务数据。
- 写操作必须同时满足测试对象配置和 `MEETINGFLOW_REAL_WRITE=1`，否则保持 dry-run。
- 事件订阅、飞书卡片、OpenClaw channel、多用户权限和生产部署仍是未完成增强项，不作为当前成果包装。

可展示位置：

```bash
sed -n '45,110p' SUBMISSION.md
```

## 收尾，约 20 秒

收束话术：

- “这次录屏展示的是一个可复现的会议与项目推进 Agent 原型：多源数据进入统一模型，四条工作流输出可审核结果，harness 验证准确性、来源、鲁棒性和规模边界。真实飞书部分当前只在测试对象和 dry-run 范围内验证，不宣称生产上线。”
