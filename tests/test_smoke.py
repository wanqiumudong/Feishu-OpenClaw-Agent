import unittest

from config import Settings
from orchestration.agent_report import build_agent_report
from orchestration.evidence_graph import build_evidence_graph
from orchestration.graphrag_answer import answer_with_graphrag
from orchestration.submission_pack import build_submission_pack
from providers.mock_provider import MockProvider
from pipelines.post_meeting_actions import build_post_meeting_actions
from pipelines.pre_meeting_brief import build_pre_meeting_brief
from pipelines.qa import answer_question
from pipelines.reconcile_board import reconcile_board


class BootstrapSmokeTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.default()
        self.provider = MockProvider(self.settings)

    def test_mock_data_loads(self):
        bundle = self.provider.load_bundle()
        self.assertGreaterEqual(len(bundle.docs), 6)
        self.assertGreaterEqual(len(bundle.minutes), 3)
        self.assertGreaterEqual(len(bundle.chat_messages), 40)
        self.assertGreaterEqual(len(bundle.tasks), 12)
        self.assertGreaterEqual(len(bundle.calendar_events), 4)

    def test_qa_returns_answer_with_sources(self):
        result = answer_question(self.provider, "上次技术评审会的主要风险是什么？")
        self.assertIn("答案", result.markdown)
        self.assertGreaterEqual(len(result.sources), 1)

    def test_pre_meeting_brief_generates_markdown(self):
        result = build_pre_meeting_brief(self.provider, "go_no_go_review")
        self.assertIn("会前背景包", result.markdown)
        self.assertIn("未关闭风险", result.markdown)

    def test_post_meeting_actions_generates_preview(self):
        result = build_post_meeting_actions(self.provider, "go_no_go_minutes")
        self.assertIn("任务创建预览", result.markdown)
        self.assertGreaterEqual(len(result.actions), 3)

    def test_reconcile_generates_summary(self):
        result = reconcile_board(self.provider)
        self.assertIn("推进总表对账预览", result.markdown)
        self.assertGreaterEqual(
            len(result.new_items) + len(result.status_updates) + len(result.blocker_updates),
            1,
        )

    def test_agent_report_generates_engineering_trace(self):
        result = build_agent_report(self.provider)
        self.assertIn("工程化报告", result.markdown)
        self.assertIn("工作流 Trace", result.markdown)
        self.assertGreaterEqual(len(result.sources), 4)

    def test_evidence_graph_generates_mermaid_trace(self):
        result = build_evidence_graph(self.provider, "Go/No-Go 灰度发布")
        self.assertIn("Evidence Graph", result.markdown)
        self.assertIn("```mermaid", result.markdown)
        self.assertGreaterEqual(len(result.sources), 1)

    def test_graphrag_answer_uses_graph_expansion(self):
        result = answer_with_graphrag(self.provider, "Go/No-Go 灰度发布有哪些阻塞？")
        self.assertIn("GraphRAG Answer", result.markdown)
        self.assertIn("Graph Retrieval Trace", result.markdown)
        self.assertIn("Microsoft GraphRAG-aligned Context", result.markdown)
        self.assertGreaterEqual(len(result.sources), 3)

    def test_submission_pack_generates_form_sections(self):
        result = build_submission_pack(self.provider, self.settings.project_root)
        self.assertIn("Demo 展示", result.markdown)
        self.assertIn("核心部分代码展示", result.markdown)
        self.assertIn("AI 亮点介绍", result.markdown)


if __name__ == "__main__":
    unittest.main()
