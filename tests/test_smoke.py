import unittest

from config import Settings
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


if __name__ == "__main__":
    unittest.main()
