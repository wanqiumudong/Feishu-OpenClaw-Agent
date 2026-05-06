import argparse
import csv
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from config import Settings
from pipelines.post_meeting_actions import build_post_meeting_actions
from pipelines.pre_meeting_brief import build_pre_meeting_brief
from pipelines.qa import answer_question
from pipelines.reconcile_board import reconcile_board
from providers.mock_provider import MockProvider
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

    args = parser.parse_args()
    settings = Settings.default()
    output_dir = Path(args.output_dir)

    if args.command == "accuracy":
        summary = run_accuracy_evaluation(settings, output_dir)
    elif args.command == "scale":
        summary = run_scale_benchmark(settings, output_dir, scale=args.scale)
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
    rows.extend(_eval_source_coverage(provider, limit=100))

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


def _eval_qa(provider: MockProvider, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        start = time.perf_counter()
        result = answer_question(provider, case["question"])
        elapsed = _elapsed_ms(start)
        keyword_score = _keyword_score(result.markdown, case.get("expected_keywords", []))
        source_score = _source_score(result.sources, case.get("expected_sources", []))
        score = _average([keyword_score, source_score])
        rows.append(
            _row(
                "qa",
                case["id"],
                score >= 0.6,
                score,
                elapsed,
                f"keywords={keyword_score:.2f}; sources={source_score:.2f}",
                case.get("notes", ""),
            )
        )
    return rows


def _eval_pre_meeting(provider: MockProvider, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        start = time.perf_counter()
        result = build_pre_meeting_brief(provider, case["event_id"])
        elapsed = _elapsed_ms(start)
        keyword_score = _keyword_score(result.markdown, case.get("expected_keywords", []))
        source_score = 1.0 if len(result.sources) >= case.get("min_sources", 0) else 0.0
        score = _average([keyword_score, source_score])
        rows.append(
            _row(
                "pre_meeting",
                case["id"],
                score >= 0.6,
                score,
                elapsed,
                f"keywords={keyword_score:.2f}; min_sources={source_score:.2f}",
                case.get("notes", ""),
            )
        )
    return rows


def _eval_post_meeting(provider: MockProvider, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        start = time.perf_counter()
        result = build_post_meeting_actions(provider, case["minutes_id"])
        elapsed = _elapsed_ms(start)
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
        rows.append(
            _row(
                "post_meeting",
                case["id"],
                score >= 0.6,
                score,
                elapsed,
                f"actions={len(result.actions)}; owners={scores[1]:.2f}; dates={scores[2]:.2f}",
                case.get("notes", ""),
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


def _expand_data(data_dir: Path, *, scale: int) -> None:
    _expand_markdown_folder(data_dir / "docs", scale, "doc")
    _expand_markdown_folder(data_dir / "minutes", scale, "minutes")
    _expand_jsonl_chat(data_dir / "chats" / "project_chat.jsonl", scale)
    _expand_json_list(data_dir / "tasks" / "tasks.json", scale, "id")
    _expand_json_list(data_dir / "calendar" / "events.json", scale, "event_id")
    _expand_csv(data_dir / "base" / "priority_board.csv", scale)


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
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    avg_score = _average([float(row["score"]) for row in rows])
    by_suite = {}
    for row in rows:
        by_suite.setdefault(row["suite"], []).append(row)

    lines = [
        "# Evaluation Summary",
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
    lines.append("Generated from synthetic mock data. It does not use real Feishu tenant data.")
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
