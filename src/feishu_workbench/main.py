import argparse

from feishu_workbench.config import Settings
from feishu_workbench.pipelines.post_meeting_actions import build_post_meeting_actions
from feishu_workbench.pipelines.pre_meeting_brief import build_pre_meeting_brief
from feishu_workbench.pipelines.qa import answer_question
from feishu_workbench.pipelines.reconcile_board import reconcile_board
from feishu_workbench.providers.lark_cli_provider import LarkCliProvider
from feishu_workbench.providers.mock_provider import MockProvider
from feishu_workbench.utils.io import write_text


def main() -> None:
    parser = argparse.ArgumentParser(prog="feishu_workbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    qa_parser = subparsers.add_parser("qa", help="Answer a question with mock sources")
    qa_parser.add_argument("--question", required=True)

    pre_parser = subparsers.add_parser("pre-meeting", help="Generate a pre-meeting brief")
    pre_parser.add_argument("--event", required=True)

    post_parser = subparsers.add_parser("post-meeting", help="Generate post-meeting actions")
    post_parser.add_argument("--minutes", required=True)

    subparsers.add_parser("reconcile", help="Preview priority board reconciliation")

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
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    write_text(settings.output_dir / output_name, markdown)
    print(markdown)


def _short_id(value: str) -> str:
    return value.replace("_review", "")


def _build_provider(settings: Settings):
    if settings.provider == "mock":
        return MockProvider(settings)
    if settings.provider == "lark_cli":
        return LarkCliProvider(settings, fallback=MockProvider(settings))
    raise ValueError(f"Unsupported MEETINGFLOW_PROVIDER: {settings.provider}")
