import os
import unittest
from unittest.mock import patch

from config import Settings
from providers.lark_cli_provider import LarkCliProvider
from providers.mock_provider import MockProvider


class LarkCliProviderTest(unittest.TestCase):
    def test_settings_reads_readonly_lark_cli_env(self):
        with patch.dict(
            os.environ,
            {
                "MEETINGFLOW_PROVIDER": "lark_cli",
                "MEETINGFLOW_DRY_RUN": "false",
                "LARK_CLI_BIN": "custom-lark",
                "FEISHU_DOC_TEST_TOKEN": "doc-test-token",
                "FEISHU_MINUTES_TEST_TOKEN": "minutes-test-token",
            },
            clear=False,
        ):
            settings = Settings.default()

        self.assertEqual(settings.provider, "lark_cli")
        self.assertFalse(settings.dry_run)
        self.assertEqual(settings.lark_cli_bin, "custom-lark")
        self.assertEqual(settings.feishu_doc_test_token, "doc-test-token")
        self.assertEqual(settings.feishu_minutes_test_token, "minutes-test-token")

    def test_lark_cli_provider_adds_readonly_items_without_leaking_tokens(self):
        calls = []

        def fake_runner(args):
            calls.append(args)
            if args[0:2] == ["docs", "+fetch"]:
                return {"title": "真实测试文档", "content": "这是测试飞书文档内容。"}
            if args[0:2] == ["vc", "+notes"]:
                return {"title": "真实测试会议纪要", "content": "这是测试会议纪要内容。"}
            raise AssertionError(f"Unexpected lark-cli args: {args}")

        settings = Settings.default()
        settings = Settings(
            project_root=settings.project_root,
            data_dir=settings.data_dir,
            output_dir=settings.output_dir,
            provider="lark_cli",
            dry_run=True,
            lark_cli_bin="lark-cli",
            feishu_doc_test_token="doc-test-token",
            feishu_minutes_test_token="minutes-test-token",
        )
        provider = LarkCliProvider(settings, fallback=MockProvider(settings), runner=fake_runner)

        bundle = provider.load_bundle()

        self.assertGreaterEqual(len(bundle.docs), 7)
        self.assertGreaterEqual(len(bundle.minutes), 4)
        doc = next(item for item in bundle.docs if item.title == "真实测试文档")
        minutes = next(item for item in bundle.minutes if item.title == "真实测试会议纪要")
        self.assertEqual(doc.kind, "doc")
        self.assertEqual(minutes.kind, "minutes")
        self.assertIn("测试飞书文档", doc.content)
        self.assertIn("测试会议纪要", minutes.content)
        self.assertNotIn("doc-test-token", doc.source_path)
        self.assertNotIn("minutes-test-token", minutes.source_path)
        self.assertEqual(
            calls,
            [
                ["docs", "+fetch", "--api-version", "v2", "--as", "user", "--doc", "doc-test-token", "--format", "json"],
                ["vc", "+notes", "--as", "user", "--minute-tokens", "minutes-test-token", "--format", "json"],
            ],
        )

    def test_lark_cli_provider_normalizes_docs_fetch_v2_payload(self):
        payload = {
            "ok": True,
            "data": {
                "document": {
                    "content": (
                        "<title>MeetingFlow Agent 测试文档</title>"
                        "<p>本文档用于验证真实飞书文档读取链路。</p>"
                        "<h2>风险</h2>"
                        "<ul><li>真实会议纪要还需要 minute token 才能验证。</li></ul>"
                    ),
                    "document_id": "doc-token",
                }
            },
        }
        settings = Settings.default()
        provider = LarkCliProvider(settings, fallback=MockProvider(settings), runner=lambda _args: payload)

        item = provider.fetch_doc("doc-test-token")

        self.assertEqual(item.title, "MeetingFlow Agent 测试文档")
        self.assertIn("本文档用于验证真实飞书文档读取链路。", item.content)
        self.assertIn("真实会议纪要还需要 minute token 才能验证。", item.content)
        self.assertNotIn("<title>", item.content)
        self.assertNotIn("<li>", item.content)


if __name__ == "__main__":
    unittest.main()
