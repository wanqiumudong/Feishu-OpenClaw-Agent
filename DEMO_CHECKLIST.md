# MeetingFlow Agent 录屏检查清单

录屏前建议按顺序执行。默认只跑 mock workflow、本地 harness 和小规模 synthetic data smoke，不访问真实飞书，不 push，不 commit。

## 基础环境

| 检查项 | 命令 | 预期输出 | 失败时切换方案 |
|---|---|---|---|
| Python 版本 | `python --version` | Python 3.10 或更高 | 切换到可用 Python 3.10+ 环境；不要临时改项目代码兼容旧版本。 |
| 包可导入 | `PYTHONPATH=src python -c "from main import main; from evaluation.run_eval import main as eval_main; print('ok')"` | `ok` | 先确认在仓库根目录执行；如果已安装包，也可以运行 `python -m pip install -e .`。 |
| 单元测试 | `PYTHONPATH=src python -m unittest discover -s tests` | 所有 tests 通过，通常显示 `OK` | 录屏中先不展示测试；切到 mock demo 四条命令，并在讲解中说明 tests 需修复后再作为证据展示。 |

## 录屏主流程

| 检查项 | 命令 | 预期输出 | 失败时切换方案 |
|---|---|---|---|
| 一键安全预检 | `bash scripts/run_full_demo.sh` | 依次完成 tests、数据摘要、四条 mock demo、full harness、小规模数据生成 smoke | 若 full harness 耗时过长，单独运行下面四条 mock demo；harness 只展示最近一次 `reports/` 结果或跳过。 |
| 数据规模摘要 | `PYTHONPATH=src python -c 'from evaluation.generate_data import main; main()' summary --format markdown` | `MeetingFlow Dataset Summary`，包含 docs、minutes、chat_messages、tasks 等数量 | 如果终端太长，切到 `--format json`，只展示对象计数字段。 |
| QA | `PYTHONPATH=src python -c 'from main import main; main()' qa --question "上次技术评审会的主要风险是什么？"` | 有答案，并出现来源列表 | 如果问题命中不理想，改用 README 中的同一句问题；不要现场换成需要外部数据的问题。 |
| 会前背景包 | `PYTHONPATH=src python -c 'from main import main; main()' pre-meeting --event go_no_go_review` | 输出会议目标、资料、风险和待确认事项 | 如果 event id 输错，回到 `data/calendar/events.json` 只确认可用 id，不修改数据文件。 |
| 会后行动项 | `PYTHONPATH=src python -c 'from main import main; main()' post-meeting --minutes go_no_go_minutes` | 输出任务创建预览，包含 owner、due date、source | 如果字段不全，强调这是预览输出；录屏不要使用 `--create-tasks`。 |
| 推进对账 | `PYTHONPATH=src python -c 'from main import main; main()' reconcile` | 输出新增事项、状态变化或阻塞补全 | 如果输出太长，展示标题和前几条结果即可。不要使用 `--upsert-base`。 |
| Agent 工程化报告 | `PYTHONPATH=src python -c 'from main import main; main()' agent-report` | 输出数据覆盖、AI 分工、工作流 Trace 和写入保护 | 如果时间不够，只展示 `AI 分工` 和 `工作流 Trace` 两段。 |

## Harness 与数据生成

| 检查项 | 命令 | 预期输出 | 失败时切换方案 |
|---|---|---|---|
| Full harness 小规模录屏版 | `PYTHONPATH=src python -c 'from evaluation.run_eval import main; main()' full --scale 20 --output-dir reports/demo_full` | `Full Harness Summary`，包含 Accuracy、Robustness、Scale | 如果时间不够，改跑 `accuracy`：`PYTHONPATH=src python -c 'from evaluation.run_eval import main; main()' accuracy --output-dir reports/demo_accuracy`。 |
| Scale 快速检查 | `PYTHONPATH=src python -c 'from evaluation.run_eval import main; main()' scale --scale 20 --output-dir reports/demo_scale` | `Scale Summary` 或 scale 结果摘要 | 如果机器负载高，降到 `--scale 5`。 |
| 小规模数据生成 smoke | `tmp_dir=$(mktemp -d); PYTHONPATH=src python -c 'from evaluation.generate_data import main; main()' generate --scale 2 --output-dir "$tmp_dir/generated"` | `Generated synthetic dataset ... scale=2` | 如果不想留下临时数据，确认命令写到 `mktemp` 目录后删除临时目录。 |

## 安全边界

| 检查项 | 命令 | 预期输出 | 失败时切换方案 |
|---|---|---|---|
| 强制 mock provider | `MEETINGFLOW_PROVIDER=mock MEETINGFLOW_REAL_WRITE=0 MEETINGFLOW_DRY_RUN=1 PYTHONPATH=src python -c 'from config import Settings; s=Settings.default(); print(s.provider, s.dry_run, s.real_write)'` | `mock True False` | 如果环境变量被 shell 覆盖，先在同一终端重新 export 这三个变量。 |
| 不展示 secrets | `env | rg 'FEISHU|LARK|TOKEN|SECRET|API_KEY'` | 录屏前不要让真实值出现在画面中 | 若有真实值，先清屏或换终端；不要把 token 写进文档、命令历史或录屏画面。 |
| 不执行真实写入 | 人工确认命令行 | 没有 `--send`、`--create-tasks`、`--upsert-base`、`MEETINGFLOW_REAL_WRITE=1` | 如果需要说明真实飞书能力，只展示 README/SUBMISSION 的边界描述，不现场写测试对象。 |

## 录屏失败时的保底顺序

1. README 项目介绍。
2. 数据规模摘要。
3. QA。
4. 会前背景包。
5. 会后行动项。
6. 推进对账。
7. 展示 `EVALUATION.md` 中的 harness 设计，不现场跑完整 harness。
8. 展示 `SUBMISSION.md` 的安全边界，明确真实飞书只做测试对象和 dry-run 范围验证。
