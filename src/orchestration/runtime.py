from dataclasses import asdict
from time import perf_counter
from typing import Any, Callable
import hashlib

from config import Settings
from distribution.renderer import sources_from_items
from models import AgentTrace, MarkdownResult, ToolCall
from orchestration.agent_report import build_agent_report
from orchestration.evidence_graph import build_evidence_graph
from orchestration.graphrag_answer import answer_with_graphrag
from pipelines.post_meeting_actions import build_post_meeting_actions
from pipelines.pre_meeting_brief import build_pre_meeting_brief
from pipelines.qa import answer_question
from pipelines.reconcile_board import reconcile_board
from retrieval.graphrag import graph_summary, graphrag_retrieve
from utils.io import write_json


ToolFn = Callable[[dict[str, Any]], Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    def run(self, name: str, payload: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name](payload)

    def names(self) -> list[str]:
        return sorted(self._tools)


class AgentRuntime:
    def __init__(self, settings: Settings, provider) -> None:
        self.settings = settings
        self.provider = provider
        self.registry = ToolRegistry()
        self._register_default_tools()

    def execute(self, workflow: str, payload: dict[str, Any]) -> AgentTrace:
        run_id = _run_id(workflow, payload)
        tool_calls: list[ToolCall] = []
        start = perf_counter()

        def run_tool(name: str, tool_payload: dict[str, Any]) -> Any:
            tool_start = perf_counter()
            try:
                output = self.registry.run(name, tool_payload)
                tool_calls.append(
                    ToolCall(
                        name=name,
                        ok=True,
                        elapsed_ms=_elapsed_ms(tool_start),
                        input_summary=_summarize(tool_payload),
                        output_summary=_summarize_output(output),
                    )
                )
                return output
            except Exception as exc:
                tool_calls.append(
                    ToolCall(
                        name=name,
                        ok=False,
                        elapsed_ms=_elapsed_ms(tool_start),
                        input_summary=_summarize(tool_payload),
                        output_summary="",
                        error=str(exc),
                    )
                )
                raise

        result = _dispatch_workflow(workflow, payload, run_tool)
        markdown, source_count = _result_markdown_and_sources(result)
        trace = AgentTrace(
            run_id=run_id,
            workflow=workflow,
            input_payload=payload,
            tool_calls=tool_calls,
            output_markdown=markdown,
            source_count=source_count,
            dry_run=self.settings.dry_run or not self.settings.real_write,
            elapsed_ms=_elapsed_ms(start),
            metadata={"tool_count": len(tool_calls), "tool_names": [call.name for call in tool_calls]},
        )
        write_json(self.settings.reports_dir / "traces" / f"{run_id}.json", asdict(trace))
        return trace

    def inspect(self) -> dict[str, Any]:
        bundle = self.provider.load_bundle()
        return {
            "tools": self.registry.names(),
            "workflows": [
                "qa",
                "pre_meeting",
                "post_meeting",
                "reconcile",
                "graphrag_local",
                "graphrag_global",
                "evidence_graph",
                "agent_report",
            ],
            "data": {
                "docs": len(bundle.docs),
                "minutes": len(bundle.minutes),
                "chat_messages": len(bundle.chat_messages),
                "tasks": len(bundle.tasks),
                "calendar_events": len(bundle.calendar_events),
                "board_rows": len(bundle.board_rows),
            },
            "dry_run": self.settings.dry_run or not self.settings.real_write,
        }

    def _register_default_tools(self) -> None:
        self.registry.register("qa.answer", lambda payload: answer_question(self.provider, payload["question"]))
        self.registry.register("brief.pre_meeting", lambda payload: build_pre_meeting_brief(self.provider, payload["event"]))
        self.registry.register("actions.post_meeting", lambda payload: build_post_meeting_actions(self.provider, payload["minutes"]))
        self.registry.register("board.reconcile", lambda _payload: reconcile_board(self.provider))
        self.registry.register(
            "graphrag.local",
            lambda payload: answer_with_graphrag(self.provider, payload["question"], mode="local"),
        )
        self.registry.register(
            "graphrag.global",
            lambda payload: answer_with_graphrag(self.provider, payload["question"], mode="global"),
        )
        self.registry.register("graph.evidence", lambda payload: build_evidence_graph(self.provider, payload.get("topic", "")))
        self.registry.register("report.agent", lambda _payload: build_agent_report(self.provider))
        self.registry.register("retrieve.graphrag_context", self._graphrag_context)

    def _graphrag_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        bundle = self.provider.load_bundle()
        result = graphrag_retrieve(bundle, payload["question"], mode=payload.get("mode", "local"))
        return {
            "summary": graph_summary(result),
            "sources": [source.title for source in sources_from_items(result.expanded_items)],
        }


def _dispatch_workflow(workflow: str, payload: dict[str, Any], run_tool: Callable[[str, dict[str, Any]], Any]) -> Any:
    if workflow == "qa":
        run_tool("retrieve.graphrag_context", {"question": payload["question"], "mode": "local"})
        return run_tool("qa.answer", payload)
    if workflow == "pre_meeting":
        return run_tool("brief.pre_meeting", payload)
    if workflow == "post_meeting":
        return run_tool("actions.post_meeting", payload)
    if workflow == "reconcile":
        return run_tool("board.reconcile", payload)
    if workflow == "graphrag_local":
        return run_tool("graphrag.local", payload)
    if workflow == "graphrag_global":
        return run_tool("graphrag.global", payload)
    if workflow == "evidence_graph":
        return run_tool("graph.evidence", payload)
    if workflow == "agent_report":
        return run_tool("report.agent", payload)
    raise ValueError(f"Unsupported workflow: {workflow}")


def _result_markdown_and_sources(result: Any) -> tuple[str, int]:
    markdown = getattr(result, "markdown", str(result))
    sources = getattr(result, "sources", [])
    return markdown, len(sources or [])


def _run_id(workflow: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(f"{workflow}:{payload}".encode("utf-8")).hexdigest()[:12]
    return f"run_{workflow}_{digest}"


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


def _summarize(payload: Any) -> str:
    text = str(payload)
    return text[:240]


def _summarize_output(output: Any) -> str:
    if isinstance(output, MarkdownResult):
        return f"markdown_chars={len(output.markdown)}; sources={len(output.sources)}"
    if isinstance(output, dict):
        return _summarize(output)
    markdown = getattr(output, "markdown", "")
    sources = getattr(output, "sources", [])
    if markdown:
        return f"markdown_chars={len(markdown)}; sources={len(sources or [])}"
    return type(output).__name__
