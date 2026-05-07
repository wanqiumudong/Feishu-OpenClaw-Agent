import argparse
import csv
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from config import Settings
from distribution.card_renderer import render_feishu_card, validate_card
from distribution.sdk_distributor import FeishuSdkDistributor
from orchestration.event_server import handle_mock_event
from orchestration.runtime import AgentRuntime
from pipelines.post_meeting_actions import build_post_meeting_actions
from pipelines.pre_meeting_brief import build_pre_meeting_brief
from pipelines.qa import answer_question
from pipelines.reconcile_board import reconcile_board
from providers.lark_cli_provider import LarkCliProvider
from providers.mock_provider import MockProvider
from retrieval.graphrag import graphrag_retrieve, graph_summary
from retrieval.indexer import build_index
from retrieval.retriever import retrieve


RESULT_FIELDS = ["suite", "case_id", "passed", "score", "elapsed_ms", "checks", "details"]


def main() -> None:
    parser = argparse.ArgumentParser(prog="meetingflow-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)

    accuracy = subparsers.add_parser("accuracy", help="Run gold-set evaluation")
    accuracy.add_argument("--output-dir", default="reports")

    scale = subparsers.add_parser("scale", help="Run synthetic scale benchmark")
    scale.add_argument("--scale", type=int, default=20)
    scale.add_argument("--output-dir", default="reports")

    full = subparsers.add_parser("full", help="Run accuracy, robustness, and scale evaluation")
    full.add_argument("--scale", type=int, default=300)
    full.add_argument("--output-dir", default="reports")

    robustness = subparsers.add_parser("robustness", help="Run noisy-data workflow checks")
    robustness.add_argument("--output-dir", default="reports")

    graph = subparsers.add_parser("graphrag", help="Run GraphRAG local/global evaluation")
    graph.add_argument("--output-dir", default="reports")
    graph.add_argument("--scale", type=int, default=50)

    agent_trace = subparsers.add_parser("agent-trace", help="Run Agent runtime trace checks")
    agent_trace.add_argument("--output-dir", default="reports")

    cards = subparsers.add_parser("cards", help="Run Feishu card rendering checks")
    cards.add_argument("--output-dir", default="reports")

    events = subparsers.add_parser("events", help="Run mock Feishu event workflow checks")
    events.add_argument("--output-dir", default="reports")

    safety = subparsers.add_parser("safety", help="Run dry-run and secret boundary checks")
    safety.add_argument("--output-dir", default="reports")

    real = subparsers.add_parser("real", help="Run configured real Feishu smoke checks")
    real.add_argument("--output-dir", default="reports")

    args = parser.parse_args()
    settings = Settings.default()
    output_dir = Path(args.output_dir)

    if args.command == "accuracy":
        summary = run_accuracy_evaluation(settings, output_dir)
    elif args.command == "scale":
        summary = run_scale_benchmark(settings, output_dir, scale=args.scale)
    elif args.command == "full":
        summary = run_full_evaluation(settings, output_dir, scale=args.scale)
    elif args.command == "robustness":
        summary = run_robustness_evaluation(settings, output_dir)
    elif args.command == "graphrag":
        summary = run_graphrag_evaluation(settings, output_dir, scale=args.scale)
    elif args.command == "agent-trace":
        summary = run_agent_trace_evaluation(settings, output_dir)
    elif args.command == "cards":
        summary = run_card_evaluation(settings, output_dir)
    elif args.command == "events":
        summary = run_event_evaluation(settings, output_dir)
    elif args.command == "safety":
        summary = run_safety_evaluation(settings, output_dir)
    elif args.command == "real":
        summary = run_real_feishu_smoke(settings, output_dir)
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(summary)


def run_accuracy_evaluation(settings: Settings, output_dir: Path) -> str:
    provider = MockProvider(settings)
    cases_dir = settings.data_dir / "evaluation"
    rows: list[dict[str, Any]] = []

    rows.extend(_eval_qa(provider, _load_cases(cases_dir / "qa_cases.json")))
    rows.extend(_eval_pre_meeting(provider, _load_cases(cases_dir / "pre_meeting_cases.json")))
    rows.extend(_eval_post_meeting(provider, _load_cases(cases_dir / "post_meeting_cases.json")))
    rows.extend(_eval_reconcile(provider, _load_cases(cases_dir / "reconcile_cases.json")))
    rows.extend(_eval_source_coverage(provider, limit=300))
    rows.extend(_eval_graphrag_quality(provider))

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "evaluation_results.csv", rows)
    summary = _accuracy_summary(rows)
    (output_dir / "evaluation_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_scale_benchmark(settings: Settings, output_dir: Path, *, scale: int) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="meetingflow-scale-") as tmp:
        tmp_root = Path(tmp)
        data_dir = tmp_root / "data"
        shutil.copytree(settings.data_dir, data_dir)
        _expand_data(data_dir, scale=max(scale, 1))

        scaled_settings = Settings(
            project_root=settings.project_root,
            data_dir=data_dir,
            output_dir=tmp_root / "outputs",
            reports_dir=tmp_root / "reports",
        )
        provider = MockProvider(scaled_settings)
        timings = _run_timed_workflows(provider)

    rows = [
        {
            "suite": "scale",
            "case_id": item["name"],
            "passed": True,
            "score": "1.00",
            "elapsed_ms": item["elapsed_ms"],
            "checks": f"scale={scale}",
            "details": item["details"],
        }
        for item in timings
    ]
    _write_csv(output_dir / "scale_test_results.csv", rows)
    summary = _scale_summary(rows, scale)
    (output_dir / "scale_test_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_full_evaluation(settings: Settings, output_dir: Path, *, scale: int) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    accuracy = run_accuracy_evaluation(settings, output_dir / "accuracy")
    robustness = run_robustness_evaluation(settings, output_dir / "robustness")
    graph = run_graphrag_evaluation(settings, output_dir / "graphrag", scale=max(scale // 10, 10))
    agent_trace = run_agent_trace_evaluation(settings, output_dir / "agent_trace")
    cards = run_card_evaluation(settings, output_dir / "cards")
    events = run_event_evaluation(settings, output_dir / "events")
    safety = run_safety_evaluation(settings, output_dir / "safety")
    scale_summary = run_scale_benchmark(settings, output_dir / "scale", scale=scale)
    summary = "\n".join(
        [
            "# Full Harness Summary",
            "",
            "## Accuracy",
            _compact_summary(accuracy),
            "",
            "## Robustness",
            _compact_summary(robustness),
            "",
            "## GraphRAG",
            _compact_summary(graph),
            "",
            "## Agent Trace",
            _compact_summary(agent_trace),
            "",
            "## Cards",
            _compact_summary(cards),
            "",
            "## Events",
            _compact_summary(events),
            "",
            "## Safety",
            _compact_summary(safety),
            "",
            "## Scale",
            _compact_summary(scale_summary),
            "",
            "This harness uses synthetic data unless the `real` suite is run separately.",
        ]
    )
    (output_dir / "full_harness_summary.md").write_text(summary + "\n", encoding="utf-8")
    return summary + "\n"


def run_robustness_evaluation(settings: Settings, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="meetingflow-robust-") as tmp:
        tmp_root = Path(tmp)
        data_dir = tmp_root / "data"
        shutil.copytree(settings.data_dir, data_dir)
        _inject_noise(data_dir)
        noisy_settings = Settings(
            project_root=settings.project_root,
            data_dir=data_dir,
            output_dir=tmp_root / "outputs",
            reports_dir=tmp_root / "reports",
        )
        provider = MockProvider(noisy_settings)
        checks = [
            ("qa_noise", lambda: answer_question(provider, "灰度上线还有哪些未关闭阻塞？").markdown, ["阻塞"]),
            ("pre_meeting_noise", lambda: build_pre_meeting_brief(provider, "go_no_go_review").markdown, ["未关闭风险"]),
            ("post_meeting_noise", lambda: build_post_meeting_actions(provider, "go_no_go_minutes").markdown, ["任务创建预览"]),
            ("reconcile_noise", lambda: reconcile_board(provider).markdown, ["阻塞补全"]),
        ]
        for case_id, fn, keywords in checks:
            start = time.perf_counter()
            markdown = fn()
            score = _keyword_score(markdown, keywords)
            rows.append(_row("robustness", case_id, score >= 0.5, score, _elapsed_ms(start), ",".join(keywords), "noisy synthetic data"))

    _write_csv(output_dir / "robustness_results.csv", rows)
    summary = _accuracy_summary(rows).replace("# Evaluation Summary", "# Robustness Summary")
    (output_dir / "robustness_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_graphrag_evaluation(settings: Settings, output_dir: Path, *, scale: int = 50) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = MockProvider(settings)
    rows = _eval_graphrag_quality(provider)
    rows.extend(_eval_graphrag_scale(settings, scale=scale))
    _write_csv(output_dir / "graphrag_results.csv", rows)
    summary = _rows_summary(
        "# GraphRAG Harness Summary",
        rows,
        "This suite checks GraphRAG-style text units, entities, relationships, community reports, local search, and global search.",
    )
    (output_dir / "graphrag_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_agent_trace_evaluation(settings: Settings, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_settings = _settings_with_reports(settings, output_dir / "runtime_reports")
    runtime = AgentRuntime(trace_settings, MockProvider(trace_settings))
    cases = [
        ("qa_trace", "qa", {"question": "上次技术评审会的主要风险是什么？"}, ["retrieve.graphrag_context", "qa.answer"]),
        ("pre_trace", "pre_meeting", {"event": "go_no_go_review"}, ["brief.pre_meeting"]),
        ("post_trace", "post_meeting", {"minutes": "go_no_go_minutes"}, ["actions.post_meeting"]),
        ("reconcile_trace", "reconcile", {}, ["board.reconcile"]),
        ("graphrag_trace", "graphrag_global", {"question": "项目当前主要主题和风险是什么？"}, ["graphrag.global"]),
    ]
    rows = []
    for case_id, workflow, payload, expected_tools in cases:
        start = time.perf_counter()
        try:
            trace = runtime.execute(workflow, payload)
            names = [call.name for call in trace.tool_calls]
            scores = [
                1.0 if trace.run_id else 0.0,
                1.0 if trace.output_markdown else 0.0,
                _set_score(set(names), set(expected_tools)),
                1.0 if all(call.ok for call in trace.tool_calls) else 0.0,
            ]
            score = _average(scores)
            checks = f"run_id={trace.run_id}; tools={','.join(names)}; source_count={trace.source_count}"
        except Exception as exc:
            score = 0.0
            checks = f"exception={str(exc)[:300]}"
        rows.append(_row("agent_trace", case_id, score >= 0.75, score, _elapsed_ms(start), checks, workflow))
    _write_csv(output_dir / "agent_trace_results.csv", rows)
    summary = _rows_summary("# Agent Trace Harness Summary", rows, "This suite checks runtime traces, tool ordering, outputs, and dry-run defaults.")
    (output_dir / "agent_trace_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_card_evaluation(settings: Settings, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = MockProvider(settings)
    cases = [
        ("pre_card", "pre_meeting", build_pre_meeting_brief(provider, "go_no_go_review").markdown, []),
        ("post_card", "post_meeting", build_post_meeting_actions(provider, "go_no_go_minutes").markdown, []),
        ("reconcile_card", "reconcile", reconcile_board(provider).markdown, []),
        ("qa_card", "qa", answer_question(provider, "上次技术评审会的主要风险是什么？").markdown, []),
    ]
    rows = []
    for case_id, workflow, markdown, sources in cases:
        start = time.perf_counter()
        card = render_feishu_card(workflow, markdown, sources, title=f"MeetingFlow {workflow}")
        errors = validate_card(card.card)
        delivery = FeishuSdkDistributor(settings).send_card(card)
        score = _average([1.0 if not errors else 0.0, 1.0 if delivery.ok else 0.0, 1.0 if delivery.dry_run else 0.0])
        rows.append(
            _row(
                "cards",
                case_id,
                score >= 0.99,
                score,
                _elapsed_ms(start),
                f"errors={','.join(errors) or 'none'}; dry_run={delivery.dry_run}",
                workflow,
            )
        )
    _write_csv(output_dir / "card_results.csv", rows)
    summary = _rows_summary("# Card Harness Summary", rows, "This suite checks Feishu card JSON shape and dry-run SDK delivery.")
    (output_dir / "card_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_event_evaluation(settings: Settings, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    event_settings = _settings_with_reports(settings, output_dir / "runtime_reports")
    runtime = AgentRuntime(event_settings, MockProvider(event_settings))
    cases = [
        ("event_pre", "请生成 Go/No-Go 会前背景包", "pre_meeting"),
        ("event_post", "请整理会后行动项", "post_meeting"),
        ("event_board", "推进表对账", "reconcile"),
        ("event_global", "全局主题和风险", "graphrag_global"),
        ("event_local", "Go/No-Go 有哪些阻塞", "graphrag_local"),
    ]
    rows = []
    for case_id, text, expected_workflow in cases:
        start = time.perf_counter()
        try:
            result = handle_mock_event(settings, runtime, {"type": "mock.message", "text": text})
            score = _average(
                [
                    1.0 if result["workflow"] == expected_workflow else 0.0,
                    1.0 if result["run_id"] else 0.0,
                    1.0 if result["card_valid"] else 0.0,
                    1.0 if result["dry_run"] else 0.0,
                ]
            )
            checks = f"workflow={result['workflow']}; run_id={result['run_id']}; dry_run={result['dry_run']}"
        except Exception as exc:
            score = 0.0
            checks = f"exception={str(exc)[:300]}"
        rows.append(_row("events", case_id, score >= 0.99, score, _elapsed_ms(start), checks, text))
    _write_csv(output_dir / "event_results.csv", rows)
    summary = _rows_summary("# Event Harness Summary", rows, "This suite checks mock Feishu event routing into Agent workflows and card dry-runs.")
    (output_dir / "event_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_safety_evaluation(settings: Settings, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    start = time.perf_counter()
    distributor = FeishuSdkDistributor(settings)
    card = render_feishu_card("qa", "# Test\n\nNo sensitive content.", [], title="MeetingFlow Safety")
    delivery = distributor.send_card(card)
    rows.append(
        _row(
            "safety",
            "sdk_card_dry_run_default",
            delivery.ok and delivery.dry_run,
            1.0 if delivery.ok and delivery.dry_run else 0.0,
            _elapsed_ms(start),
            f"dry_run={delivery.dry_run}",
            "SDK card delivery must stay dry-run by default",
        )
    )
    start = time.perf_counter()
    text = str(card.card)
    leaked = any(term in text.lower() for term in ["token", "secret", "cookie"])
    rows.append(_row("safety", "card_has_no_secret_words", not leaked, 0.0 if leaked else 1.0, _elapsed_ms(start), f"leaked={leaked}", "card JSON"))
    _write_csv(output_dir / "safety_results.csv", rows)
    summary = _rows_summary("# Safety Harness Summary", rows, "This suite checks default dry-run behavior and card content safety.")
    (output_dir / "safety_summary.md").write_text(summary, encoding="utf-8")
    return summary


def run_real_feishu_smoke(settings: Settings, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    provider = LarkCliProvider(settings, fallback=MockProvider(settings))
    start = time.perf_counter()
    try:
        bundle = provider.load_bundle()
        feishu_docs = [item for item in bundle.docs if item.source_path.startswith("feishu://docs")]
        feishu_minutes = [item for item in bundle.minutes if item.source_path.startswith("feishu://minutes")]
        configured = bool(settings.feishu_doc_urls or settings.feishu_minute_tokens)
        score = 1.0 if configured and (feishu_docs or feishu_minutes) else 0.0
        rows.append(
            _row(
                "real_feishu",
                "readonly_ingestion",
                score > 0,
                score,
                _elapsed_ms(start),
                f"docs={len(feishu_docs)}; minutes={len(feishu_minutes)}",
                "requires valid lark-cli auth and test object config",
            )
        )
    except Exception as exc:
        rows.append(_row("real_feishu", "readonly_ingestion", False, 0.0, _elapsed_ms(start), "exception", str(exc)[:500]))

    _write_csv(output_dir / "real_feishu_results.csv", rows)
    summary = _rows_summary(
        "# Real Feishu Smoke Summary",
        rows,
        "This suite checks the local lark-cli configuration and test Feishu objects. It does not report online product metrics.",
    )
    (output_dir / "real_feishu_summary.md").write_text(summary, encoding="utf-8")
    return summary


def _eval_qa(provider: MockProvider, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        start = time.perf_counter()
        try:
            result = answer_question(provider, case["question"])
            keyword_score = _keyword_score(result.markdown, case.get("expected_keywords", []))
            source_score = _source_score(result.sources, case.get("expected_sources", []))
            score = _average([keyword_score, source_score])
            checks = f"keywords={keyword_score:.2f}; sources={source_score:.2f}"
            details = case.get("notes", "")
        except Exception as exc:
            score = 0.0
            checks = "exception"
            details = str(exc)[:500]
        elapsed = _elapsed_ms(start)
        rows.append(
            _row(
                "qa",
                case["id"],
                score >= 0.6,
                score,
                elapsed,
                checks,
                details,
            )
        )
    return rows


def _eval_pre_meeting(provider: MockProvider, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        start = time.perf_counter()
        try:
            result = build_pre_meeting_brief(provider, case["event_id"])
            keyword_score = _keyword_score(result.markdown, case.get("expected_keywords", []))
            source_score = 1.0 if len(result.sources) >= case.get("min_sources", 0) else 0.0
            score = _average([keyword_score, source_score])
            checks = f"keywords={keyword_score:.2f}; min_sources={source_score:.2f}"
            details = case.get("notes", "")
        except Exception as exc:
            score = 0.0
            checks = "exception"
            details = str(exc)[:500]
        elapsed = _elapsed_ms(start)
        rows.append(
            _row(
                "pre_meeting",
                case["id"],
                score >= 0.6,
                score,
                elapsed,
                checks,
                details,
            )
        )
    return rows


def _eval_post_meeting(provider: MockProvider, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        start = time.perf_counter()
        try:
            result = build_post_meeting_actions(provider, case["minutes_id"])
            owners = {action.owner for action in result.actions}
            dates = {action.due_date for action in result.actions}
            backgrounds = "\n".join(action.background for action in result.actions)
            scores = [
                1.0 if len(result.actions) >= case.get("min_actions", 0) else 0.0,
                _set_score(owners, set(case.get("expected_owners", []))),
                _set_score(dates, set(case.get("expected_due_dates", []))),
                _keyword_score(backgrounds, case.get("expected_background_keywords", [])),
            ]
            score = _average(scores)
            checks = f"actions={len(result.actions)}; owners={scores[1]:.2f}; dates={scores[2]:.2f}"
            details = case.get("notes", "")
        except Exception as exc:
            score = 0.0
            checks = "exception"
            details = str(exc)[:500]
        elapsed = _elapsed_ms(start)
        rows.append(
            _row(
                "post_meeting",
                case["id"],
                score >= 0.6,
                score,
                elapsed,
                checks,
                details,
            )
        )
    return rows


def _eval_reconcile(provider: MockProvider, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        start = time.perf_counter()
        result = reconcile_board(provider)
        elapsed = _elapsed_ms(start)
        new_items_text = "\n".join(item["title"] for item in result.new_items)
        blockers_text = "\n".join(item["blocker"] for item in result.blocker_updates)
        scores = [
            _keyword_score(new_items_text, case.get("expected_new_item_keywords", [])),
            _keyword_score(blockers_text, case.get("expected_blocker_keywords", [])),
            1.0 if len(result.sources) >= case.get("min_sources", 0) else 0.0,
        ]
        score = _average(scores)
        rows.append(
            _row(
                "reconcile",
                case["id"],
                score >= 0.6,
                score,
                elapsed,
                f"new_items={scores[0]:.2f}; blockers={scores[1]:.2f}; sources={scores[2]:.2f}",
                case.get("notes", ""),
            )
        )
    return rows


def _eval_source_coverage(provider: MockProvider, *, limit: int) -> list[dict[str, Any]]:
    bundle = provider.load_bundle()
    items = build_index(bundle)[:limit]
    rows = []
    for item in items:
        start = time.perf_counter()
        matches = retrieve(items, item.title, limit=5)
        elapsed = _elapsed_ms(start)
        hit = any(match.id == item.id and match.source_path == item.source_path for match in matches)
        rows.append(
            _row(
                "source_coverage",
                item.id,
                hit,
                1.0 if hit else 0.0,
                elapsed,
                f"kind={item.kind}; matches={len(matches)}",
                item.source_path,
            )
        )
    return rows


def _eval_graphrag_quality(provider: MockProvider) -> list[dict[str, Any]]:
    bundle = provider.load_bundle()
    cases = [
        ("graphrag_local_release", "Go/No-Go 灰度发布有哪些阻塞？", "local", ["Go/No-Go", "FAQ", "回滚"]),
        ("graphrag_local_quality", "行动项抽取的质量风险和评测口径是什么？", "local", ["误召回", "评测", "行动项"]),
        ("graphrag_local_security", "会前背景包有哪些权限风险？", "local", ["权限", "安全", "越权"]),
        ("graphrag_global_themes", "项目当前主要主题和风险是什么？", "global", ["灰度", "质量", "权限"]),
        ("graphrag_global_delivery", "项目推进中哪些社区主题最重要？", "global", ["任务", "推进表", "阻塞"]),
    ]
    rows = []
    for case_id, query, mode, keywords in cases:
        start = time.perf_counter()
        try:
            result = graphrag_retrieve(bundle, query, mode=mode, seed_limit=10, limit=14)
            context = result.context
            context_score = 0.0
            if context:
                checks = {
                    "text_units": len(context.text_units) >= 3,
                    "entities": len(context.selected_entities) >= 3,
                    "relationships": len(context.relationships) >= 1,
                    "community_reports": len(context.community_reports) >= (1 if mode == "local" else 3),
                }
                context_score = sum(1 for passed in checks.values() if passed) / len(checks)
                text = "\n".join(item.title + "\n" + item.content for item in result.expanded_items)
                keyword_score = _keyword_score(text, keywords)
                score = _average([context_score, keyword_score])
                check_text = f"{graph_summary(result)}; keyword_score={keyword_score:.2f}"
            else:
                score = 0.0
                check_text = "missing_context"
        except Exception as exc:
            score = 0.0
            check_text = "exception"
            keywords = [str(exc)[:300]]
        rows.append(
            _row(
                "graphrag",
                case_id,
                score >= 0.65,
                score,
                _elapsed_ms(start),
                check_text,
                ";".join(keywords),
            )
        )
    return rows


def _eval_graphrag_scale(settings: Settings, *, scale: int) -> list[dict[str, Any]]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="meetingflow-graphrag-scale-") as tmp:
        tmp_root = Path(tmp)
        data_dir = tmp_root / "data"
        shutil.copytree(settings.data_dir, data_dir)
        _expand_data(data_dir, scale=max(scale, 1))
        scaled_settings = Settings(
            project_root=settings.project_root,
            data_dir=data_dir,
            output_dir=tmp_root / "outputs",
            reports_dir=tmp_root / "reports",
        )
        provider = MockProvider(scaled_settings)
        bundle = provider.load_bundle()
        for mode, query in (
            ("local", "Go/No-Go 灰度发布有哪些阻塞？"),
            ("global", "项目当前主要主题和风险是什么？"),
        ):
            start = time.perf_counter()
            result = graphrag_retrieve(bundle, query, mode=mode, seed_limit=10, limit=14)
            context = result.context
            score = 1.0 if context and context.text_units and context.community_reports else 0.0
            rows.append(
                _row(
                    "graphrag_scale",
                    f"{mode}_scale_{scale}",
                    score > 0,
                    score,
                    _elapsed_ms(start),
                    graph_summary(result),
                    f"scale={scale}",
                )
            )
    return rows


def _expand_data(data_dir: Path, *, scale: int) -> None:
    _expand_markdown_folder(data_dir / "docs", scale, "doc")
    _expand_markdown_folder(data_dir / "minutes", scale, "minutes")
    _expand_jsonl_chat(data_dir / "chats" / "project_chat.jsonl", scale)
    _expand_json_list(data_dir / "tasks" / "tasks.json", scale, "id")
    _expand_json_list(data_dir / "calendar" / "events.json", scale, "event_id")
    _expand_csv(data_dir / "base" / "priority_board.csv", scale)


def _settings_with_reports(settings: Settings, reports_dir: Path) -> Settings:
    return Settings(
        project_root=settings.project_root,
        data_dir=settings.data_dir,
        output_dir=settings.output_dir,
        reports_dir=reports_dir,
        provider=settings.provider,
        dry_run=settings.dry_run,
        real_write=settings.real_write,
        lark_cli_bin=settings.lark_cli_bin,
        feishu_doc_urls=settings.feishu_doc_urls,
        feishu_minute_tokens=settings.feishu_minute_tokens,
        feishu_chat_id=settings.feishu_chat_id,
        feishu_tasklist_id=settings.feishu_tasklist_id,
        feishu_base_token=settings.feishu_base_token,
        feishu_base_table_id=settings.feishu_base_table_id,
        feishu_app_id=settings.feishu_app_id,
        feishu_app_credential=settings.feishu_app_credential,
        feishu_encrypt_key=settings.feishu_encrypt_key,
        feishu_verification_token=settings.feishu_verification_token,
        llm_enabled=settings.llm_enabled,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        llm_api_key=settings.llm_api_key,
        llm_timeout_s=settings.llm_timeout_s,
    )


def generate_synthetic_dataset(source_data_dir: Path, output_data_dir: Path, *, scale: int) -> None:
    if output_data_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing directory: {output_data_dir}")
    shutil.copytree(source_data_dir, output_data_dir)
    _expand_data(output_data_dir, scale=max(scale, 1))


def _expand_markdown_folder(folder: Path, scale: int, prefix: str) -> None:
    originals = sorted(folder.glob("*.md"))
    for copy_id in range(1, scale):
        for path in originals:
            target = folder / f"{path.stem}_{prefix}_{copy_id:03d}.md"
            target.write_text(path.read_text(encoding="utf-8") + f"\n\nscale_copy: {copy_id}\n", encoding="utf-8")


def _expand_jsonl_chat(path: Path, scale: int) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    expanded = []
    for copy_id in range(scale):
        for row in rows:
            item = dict(row)
            item["id"] = f"{row['id']}_{copy_id:03d}"
            expanded.append(item)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in expanded) + "\n", encoding="utf-8")


def _expand_json_list(path: Path, scale: int, id_key: str) -> None:
    rows = json.loads(path.read_text(encoding="utf-8"))
    expanded = []
    for copy_id in range(scale):
        for row in rows:
            item = dict(row)
            item[id_key] = f"{row[id_key]}_{copy_id:03d}"
            expanded.append(item)
    path.write_text(json.dumps(expanded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _expand_csv(path: Path, scale: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    header, rows = lines[0], lines[1:]
    expanded = [header]
    for copy_id in range(scale):
        for row in rows:
            parts = row.split(",")
            parts[0] = f"{parts[0]}_{copy_id:03d}"
            expanded.append(",".join(parts))
    path.write_text("\n".join(expanded) + "\n", encoding="utf-8")


def _run_timed_workflows(provider: MockProvider) -> list[dict[str, Any]]:
    tasks = [
        ("load_bundle", lambda: provider.load_bundle()),
        ("qa", lambda: answer_question(provider, "上次技术评审会的主要风险是什么？")),
        ("pre_meeting", lambda: build_pre_meeting_brief(provider, "go_no_go_review_000")),
        ("post_meeting", lambda: build_post_meeting_actions(provider, "go_no_go_minutes_minutes_001")),
        ("reconcile", lambda: reconcile_board(provider)),
    ]
    rows = []
    for name, fn in tasks:
        start = time.perf_counter()
        result = fn()
        rows.append(
            {
                "name": name,
                "elapsed_ms": _elapsed_ms(start),
                "details": _result_size(result),
            }
        )
    return rows


def _inject_noise(data_dir: Path) -> None:
    noisy_doc = data_dir / "docs" / "zzz_noise_status_conflict.md"
    noisy_doc.write_text(
        "# 噪声文档：状态冲突记录\n\n"
        "这是一份用于鲁棒性测试的噪声资料。它故意混入过期状态、重复行动项和不完整负责人。\n"
        "- 旧说法：灰度已经完成。\n"
        "- 新线索：客服 FAQ 仍有回滚说明缺口。\n"
        "- 待确认：谁负责补齐外部沟通材料。\n",
        encoding="utf-8",
    )
    chat_path = data_dir / "chats" / "project_chat.jsonl"
    with chat_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "id": "noise_conflict_001",
                    "sender": "测试用户",
                    "text": "这里有一条噪声：看起来像承诺但其实只是猜测，可能导致行动项误抽取。",
                    "tags": ["noise", "robustness"],
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def _result_size(result: Any) -> str:
    if hasattr(result, "markdown"):
        return f"markdown_chars={len(result.markdown)}"
    if hasattr(result, "docs"):
        return (
            f"docs={len(result.docs)}, minutes={len(result.minutes)}, "
            f"chat={len(result.chat_messages)}, tasks={len(result.tasks)}"
        )
    return type(result).__name__


def _load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _accuracy_summary(rows: list[dict[str, Any]]) -> str:
    return _rows_summary("# Evaluation Summary", rows, "Generated from synthetic mock data. It does not use real Feishu tenant data.")


def _rows_summary(title: str, rows: list[dict[str, Any]], footer: str) -> str:
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    avg_score = _average([float(row["score"]) for row in rows])
    by_suite = {}
    for row in rows:
        by_suite.setdefault(row["suite"], []).append(row)

    lines = [
        title,
        "",
        f"- Cases: {total}",
        f"- Passed: {passed}",
        f"- Average score: {avg_score:.2f}",
        "",
        "## Suites",
    ]
    for suite, suite_rows in sorted(by_suite.items()):
        suite_passed = sum(1 for row in suite_rows if row["passed"])
        suite_score = _average([float(row["score"]) for row in suite_rows])
        lines.append(f"- {suite}: {suite_passed}/{len(suite_rows)}, score {suite_score:.2f}")
    lines.append("")
    lines.append(footer)
    return "\n".join(lines) + "\n"


def _scale_summary(rows: list[dict[str, Any]], scale: int) -> str:
    lines = [
        "# Scale Test Summary",
        "",
        f"- Scale multiplier: {scale}",
        "",
        "## Timings",
    ]
    for row in rows:
        lines.append(f"- {row['case_id']}: {row['elapsed_ms']} ms, {row['details']}")
    lines.append("")
    lines.append("The benchmark uses temporary synthetic data and does not persist generated data.")
    return "\n".join(lines) + "\n"


def _compact_summary(text: str) -> str:
    lines = [line for line in text.splitlines() if line.startswith("- Cases:") or line.startswith("- Passed:") or line.startswith("- Average") or line.startswith("- Scale")]
    return "\n".join(lines) if lines else text.splitlines()[0]


def _row(suite: str, case_id: str, passed: bool, score: float, elapsed_ms: int, checks: str, details: str) -> dict[str, Any]:
    return {
        "suite": suite,
        "case_id": case_id,
        "passed": passed,
        "score": f"{score:.2f}",
        "elapsed_ms": elapsed_ms,
        "checks": checks,
        "details": details,
    }


def _keyword_score(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    hits = sum(1 for keyword in keywords if keyword in text)
    return hits / len(keywords)


def _source_score(sources: list[Any], expected: list[str]) -> float:
    if not expected:
        return 1.0
    text = "\n".join(f"{source.title}\n{source.path}" for source in sources)
    hits = sum(1 for keyword in expected if keyword in text)
    return hits / len(expected)


def _set_score(actual: set[str], expected: set[str]) -> float:
    if not expected:
        return 1.0
    return len(actual & expected) / len(expected)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


if __name__ == "__main__":
    main()
