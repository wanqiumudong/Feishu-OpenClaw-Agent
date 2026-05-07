import argparse
import json
from pathlib import Path

from config import Settings
from evaluation.run_eval import generate_synthetic_dataset
from providers.mock_provider import MockProvider


def main() -> None:
    parser = argparse.ArgumentParser(prog="meetingflow-data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a scaled synthetic dataset")
    generate.add_argument("--scale", type=int, default=20)
    generate.add_argument("--output-dir", required=True)

    summary = subparsers.add_parser("summary", help="Show current dataset object counts")
    summary.add_argument("--format", choices=["markdown", "json"], default="markdown")

    args = parser.parse_args()
    settings = Settings.default()

    if args.command == "generate":
        output_dir = Path(args.output_dir)
        generate_synthetic_dataset(settings.data_dir, output_dir, scale=args.scale)
        print(f"Generated synthetic dataset at {output_dir} with scale={args.scale}")
    elif args.command == "summary":
        payload = _dataset_summary(settings)
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(_markdown_summary(payload))
    else:
        raise ValueError(f"Unsupported command: {args.command}")


def _dataset_summary(settings: Settings) -> dict:
    bundle = MockProvider(settings).load_bundle()
    return {
        "docs": len(bundle.docs),
        "minutes": len(bundle.minutes),
        "chat_messages": len(bundle.chat_messages),
        "tasks": len(bundle.tasks),
        "calendar_events": len(bundle.calendar_events),
        "board_rows": len(bundle.board_rows),
        "open_risks": len([risk for risk in bundle.truth.get("risks", []) if risk.get("status") == "open"]),
        "decisions": len(bundle.truth.get("decisions", [])),
    }


def _markdown_summary(payload: dict) -> str:
    lines = ["# MeetingFlow Dataset Summary", ""]
    for key, value in payload.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
