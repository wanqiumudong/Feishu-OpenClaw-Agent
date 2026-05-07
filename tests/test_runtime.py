import tempfile
import unittest
from pathlib import Path

from config import Settings
from distribution.card_renderer import render_feishu_card, validate_card
from distribution.sdk_distributor import FeishuSdkDistributor
from orchestration.event_server import handle_mock_event
from orchestration.runtime import AgentRuntime
from providers.mock_provider import MockProvider


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        base = Settings.default()
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            project_root=base.project_root,
            data_dir=base.data_dir,
            output_dir=Path(self.tmp.name) / "outputs",
            reports_dir=Path(self.tmp.name) / "reports",
        )
        self.provider = MockProvider(self.settings)

    def tearDown(self):
        self.tmp.cleanup()

    def test_runtime_executes_workflow_and_writes_trace(self):
        runtime = AgentRuntime(self.settings, self.provider)
        trace = runtime.execute("qa", {"question": "上次技术评审会的主要风险是什么？"})

        self.assertEqual(trace.workflow, "qa")
        self.assertGreaterEqual(len(trace.tool_calls), 2)
        self.assertIn("retrieve.graphrag_context", [call.name for call in trace.tool_calls])
        self.assertTrue((self.settings.reports_dir / "traces" / f"{trace.run_id}.json").exists())

    def test_card_renderer_and_sdk_dry_run(self):
        runtime = AgentRuntime(self.settings, self.provider)
        trace = runtime.execute("pre_meeting", {"event": "go_no_go_review"})
        card = render_feishu_card("pre_meeting", trace.output_markdown, [], title="MeetingFlow")
        delivery = FeishuSdkDistributor(self.settings).send_card(card)

        self.assertEqual(validate_card(card.card), [])
        self.assertTrue(delivery.ok)
        self.assertTrue(delivery.dry_run)

    def test_mock_event_routes_to_workflow(self):
        runtime = AgentRuntime(self.settings, self.provider)
        result = handle_mock_event(self.settings, runtime, {"text": "推进表对账"})

        self.assertEqual(result["workflow"], "reconcile")
        self.assertTrue(result["card_valid"])
        self.assertTrue(result["dry_run"])


if __name__ == "__main__":
    unittest.main()
