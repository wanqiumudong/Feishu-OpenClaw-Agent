import argparse
from dataclasses import asdict
import json

from config import Settings
from distribution.card_renderer import render_feishu_card, validate_card
from distribution.feishu_distributor import FeishuDistributor
from distribution.sdk_distributor import FeishuSdkDistributor
from orchestration.agent_report import build_agent_report
from orchestration.evidence_graph import build_evidence_graph
from orchestration.event_server import handle_mock_event
from orchestration.graphrag_answer import answer_with_graphrag
from orchestration.runtime import AgentRuntime
from orchestration.submission_pack import build_submission_pack
from pipelines.post_meeting_actions import build_post_meeting_actions
from pipelines.pre_meeting_brief import build_pre_meeting_brief
from pipelines.qa import answer_question
from pipelines.reconcile_board import reconcile_board
from providers.lark_cli_provider import LarkCliProvider
from providers.feishu_sdk_provider import FeishuSdkProvider
from providers.mock_provider import MockProvider
from utils.io import write_text


def main() -> None:
    parser = argparse.ArgumentParser(prog="meetingflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    qa_parser = subparsers.add_parser("qa", help="Answer a question with mock sources")
    qa_parser.add_argument("--question", required=True)
    _add_send_argument(qa_parser)

    pre_parser = subparsers.add_parser("pre-meeting", help="Generate a pre-meeting brief")
    pre_parser.add_argument("--event", required=True)
    _add_send_argument(pre_parser)

    post_parser = subparsers.add_parser("post-meeting", help="Generate post-meeting actions")
    post_parser.add_argument("--minutes", required=True)
    _add_send_argument(post_parser)
    post_parser.add_argument("--create-tasks", action="store_true", help="Create Feishu test tasks from action previews")

    reconcile_parser = subparsers.add_parser("reconcile", help="Preview priority board reconciliation")
    _add_send_argument(reconcile_parser)
    reconcile_parser.add_argument("--upsert-base", action="store_true", help="Upsert Feishu test Base rows from reconciliation")

    smoke_parser = subparsers.add_parser("real-smoke", help="Check configured real Feishu read/write paths")
    _add_send_argument(smoke_parser, help_text="Send a smoke summary to the configured Feishu test chat")

    report_parser = subparsers.add_parser("agent-report", help="Generate an engineering report for the Agent workflow")
    _add_send_argument(report_parser, help_text="Send the report to the configured Feishu test chat")

    graph_parser = subparsers.add_parser("evidence-graph", help="Generate a source-traced evidence graph")
    graph_parser.add_argument("--topic", default="Go/No-Go 灰度发布")
    _add_send_argument(graph_parser, help_text="Send the graph to the configured Feishu test chat")

    graphrag_parser = subparsers.add_parser("graphrag", help="Answer a question with graph-expanded retrieval")
    graphrag_parser.add_argument("--question", required=True)
    graphrag_parser.add_argument("--mode", choices=["local", "global"], default="local")
    _add_send_argument(graphrag_parser, help_text="Send the answer to the configured Feishu test chat")

    pack_parser = subparsers.add_parser("submission-pack", help="Generate form-ready submission content")
    _add_send_argument(pack_parser, help_text="Send the pack to the configured Feishu test chat")

    run_parser = subparsers.add_parser("run", help="Run a workflow through the Agent runtime")
    run_parser.add_argument("--workflow", required=True)
    run_parser.add_argument("--payload", default="{}")

    subparsers.add_parser("inspect-runtime", help="Inspect registered Agent tools and data coverage")

    card_parser = subparsers.add_parser("card-preview", help="Render a Feishu card JSON from a workflow")
    card_parser.add_argument("--workflow", default="pre_meeting")
    card_parser.add_argument("--payload", default="{}")

    send_card_parser = subparsers.add_parser("send-card", help="Send or dry-run a Feishu card through the SDK boundary")
    send_card_parser.add_argument("--workflow", default="pre_meeting")
    send_card_parser.add_argument("--payload", default="{}")

    event_parser = subparsers.add_parser("event-server", help="Run a mock event through the Agent runtime")
    event_parser.add_argument("--mode", choices=["mock"], default="mock")
    event_parser.add_argument("--text", default="请生成 Go/No-Go 会前背景包")

    subparsers.add_parser("sdk-status", help="Show optional Feishu SDK integration status")

    args = parser.parse_args()
    settings = Settings.default()
    provider = _build_provider(settings)

    if args.command == "qa":
        result = answer_question(provider, args.question)
        output_name = "qa_example.md"
        markdown = result.markdown
    elif args.command == "pre-meeting":
        result = build_pre_meeting_brief(provider, args.event)
        output_name = f"pre_meeting_{_short_id(args.event)}.md"
        markdown = result.markdown
    elif args.command == "post-meeting":
        result = build_post_meeting_actions(provider, args.minutes)
        output_name = "post_meeting_actions.md"
        markdown = result.markdown
    elif args.command == "reconcile":
        result = reconcile_board(provider)
        output_name = "reconcile_board_summary.md"
        markdown = result.markdown
    elif args.command == "real-smoke":
        markdown = _real_smoke(provider)
        output_name = "real_smoke.md"
        result = None
    elif args.command == "agent-report":
        result = build_agent_report(provider)
        output_name = "agent_report.md"
        markdown = result.markdown
    elif args.command == "evidence-graph":
        result = build_evidence_graph(provider, args.topic)
        output_name = "evidence_graph.md"
        markdown = result.markdown
    elif args.command == "graphrag":
        result = answer_with_graphrag(provider, args.question, mode=args.mode)
        output_name = "graphrag_answer.md"
        markdown = result.markdown
    elif args.command == "submission-pack":
        result = build_submission_pack(provider, settings.project_root)
        output_name = "submission_pack.md"
        markdown = result.markdown
    elif args.command == "run":
        runtime = AgentRuntime(settings, provider)
        trace = runtime.execute(args.workflow, _parse_json_payload(args.payload))
        print(json.dumps(asdict(trace), ensure_ascii=False, indent=2))
        return
    elif args.command == "inspect-runtime":
        runtime = AgentRuntime(settings, provider)
        print(json.dumps(runtime.inspect(), ensure_ascii=False, indent=2))
        return
    elif args.command == "card-preview":
        runtime = AgentRuntime(settings, provider)
        trace = runtime.execute(args.workflow, _payload_with_defaults(args.workflow, args.payload))
        card = render_feishu_card(args.workflow, trace.output_markdown, [], title=f"MeetingFlow {args.workflow}")
        print(json.dumps(asdict(card), ensure_ascii=False, indent=2))
        return
    elif args.command == "send-card":
        runtime = AgentRuntime(settings, provider)
        trace = runtime.execute(args.workflow, _payload_with_defaults(args.workflow, args.payload))
        card = render_feishu_card(args.workflow, trace.output_markdown, [], title=f"MeetingFlow {args.workflow}")
        errors = validate_card(card.card)
        delivery = FeishuSdkDistributor(settings).send_card(card)
        print(json.dumps({"card_errors": errors, "delivery": asdict(delivery)}, ensure_ascii=False, indent=2))
        return
    elif args.command == "event-server":
        runtime = AgentRuntime(settings, provider)
        payload = {"type": "mock.message", "text": args.text}
        result_payload = handle_mock_event(settings, runtime, payload)
        print(json.dumps(result_payload, ensure_ascii=False, indent=2))
        return
    elif args.command == "sdk-status":
        print(json.dumps(FeishuSdkProvider(settings).status(), ensure_ascii=False, indent=2))
        return
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    write_text(settings.output_dir / output_name, markdown)
    _maybe_distribute(settings, args, markdown, result)
    print(markdown)


def _short_id(value: str) -> str:
    return value.replace("_review", "")


def _parse_json_payload(raw_value: str) -> dict:
    payload = json.loads(raw_value)
    if not isinstance(payload, dict):
        raise ValueError("--payload must be a JSON object")
    return payload


def _payload_with_defaults(workflow: str, raw_value: str) -> dict:
    payload = _parse_json_payload(raw_value)
    if payload:
        return payload
    defaults = {
        "qa": {"question": "上次技术评审会的主要风险是什么？"},
        "pre_meeting": {"event": "go_no_go_review"},
        "post_meeting": {"minutes": "go_no_go_minutes"},
        "reconcile": {},
        "graphrag_local": {"question": "Go/No-Go 灰度发布有哪些阻塞？"},
        "graphrag_global": {"question": "项目当前主要主题和风险是什么？"},
        "evidence_graph": {"topic": "Go/No-Go 灰度发布"},
        "agent_report": {},
    }
    return defaults.get(workflow, {})


def _build_provider(settings: Settings):
    if settings.provider in {"mock", ""}:
        return MockProvider(settings)
    if settings.provider in {"feishu", "lark_cli"}:
        return LarkCliProvider(settings, fallback=MockProvider(settings))
    raise ValueError(f"Unsupported MEETINGFLOW_PROVIDER: {settings.provider}")


def _maybe_distribute(settings: Settings, args, markdown: str, result) -> None:
    distributor = FeishuDistributor(settings)
    if getattr(args, "send", False):
        delivery = distributor.send_markdown(markdown)
        print(f"\n[feishu] send_message dry_run={delivery.dry_run} ok={delivery.ok}")
        if delivery.error:
            print(f"[feishu] error={delivery.error}")
    if getattr(args, "create_tasks", False) and result is not None:
        for action in getattr(result, "actions", []):
            delivery = distributor.create_task(action)
            print(f"[feishu] create_task dry_run={delivery.dry_run} ok={delivery.ok}")
            if delivery.error:
                print(f"[feishu] error={delivery.error}")
    if getattr(args, "upsert_base", False) and result is not None:
        for row in _reconcile_records(result):
            delivery = distributor.upsert_base_record(row)
            print(f"[feishu] upsert_base_record dry_run={delivery.dry_run} ok={delivery.ok}")
            if delivery.error:
                print(f"[feishu] error={delivery.error}")


def _reconcile_records(result) -> list[dict[str, str]]:
    records = []
    for item in result.new_items:
        records.append({"事项": item.get("title", ""), "状态": "todo", "风险": item.get("reason", ""), "类型": "新增事项"})
    for item in result.status_updates:
        records.append({"事项": item.get("title", ""), "状态": item.get("status", ""), "风险": "", "类型": "状态更新"})
    for item in result.blocker_updates:
        records.append({"事项": item.get("title", ""), "状态": "blocked", "风险": item.get("blocker", ""), "类型": "阻塞补全"})
    return records


def _real_smoke(provider) -> str:
    try:
        bundle = provider.load_bundle()
    except Exception as exc:
        return "\n".join(
            [
                "# MeetingFlow Real Feishu Smoke",
                "",
                "- Status: failed",
                f"- Error: {str(exc).strip()}",
                "",
                "## Next Checks",
                "- Confirm `lark-cli auth status` is valid.",
                "- Confirm the URL points to a supported test object.",
                "- For wiki URLs, the current provider supports wiki nodes backed by docx or slides.",
                "- Do not use real business documents for public demo material.",
            ]
        ) + "\n"

    feishu_docs = [item for item in bundle.docs if item.source_path.startswith("feishu://")]
    feishu_minutes = [item for item in bundle.minutes if item.source_path.startswith("feishu://")]
    lines = [
        "# MeetingFlow Real Feishu Smoke",
        "",
        f"- Feishu docs loaded: {len(feishu_docs)}",
        f"- Feishu minutes loaded: {len(feishu_minutes)}",
        f"- Total docs: {len(bundle.docs)}",
        f"- Total minutes: {len(bundle.minutes)}",
        "",
        "## Loaded Sources",
    ]
    for item in [*feishu_docs, *feishu_minutes]:
        lines.append(f"- {item.kind}: {item.title} ({item.source_path})")
    if not feishu_docs and not feishu_minutes:
        lines.append("- No real Feishu sources configured.")
    return "\n".join(lines) + "\n"


def _add_send_argument(parser, *, help_text: str = "Send the result to the configured Feishu test chat") -> None:
    parser.add_argument("--send", "--send-message", dest="send", action="store_true", help=help_text)
