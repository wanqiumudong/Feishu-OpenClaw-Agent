import unittest

from config import Settings
from distribution.feishu_distributor import FeishuDistributor
from models import ActionPreview, SourceRef
from providers.lark_cli_provider import LarkCliProvider
from providers.mock_provider import MockProvider


class FeishuIntegrationTest(unittest.TestCase):
    def test_lark_cli_provider_normalizes_real_sources_without_token_leak(self):
        calls = []

        def fake_runner(args):
            calls.append(args)
            if args[:2] == ["docs", "+fetch"]:
                return {"data": {"document": {"content": "<title>真实测试文档</title><p>文档正文。</p>"}}}
            if args[:2] == ["vc", "+notes"]:
                return {"data": {"title": "真实测试纪要", "content": "纪要正文。"}}
            raise AssertionError(args)

        base = Settings.default()
        settings = Settings(
            project_root=base.project_root,
            data_dir=base.data_dir,
            output_dir=base.output_dir,
            reports_dir=base.reports_dir,
            provider="feishu",
            feishu_doc_urls=("doc-secret-token",),
            feishu_minute_tokens=("minute-secret-token",),
        )
        provider = LarkCliProvider(settings, fallback=MockProvider(settings), runner=fake_runner)

        bundle = provider.load_bundle()

        doc = next(item for item in bundle.docs if item.title == "真实测试文档")
        minutes = next(item for item in bundle.minutes if item.title == "真实测试纪要")
        self.assertEqual(doc.kind, "doc")
        self.assertEqual(minutes.kind, "minutes")
        self.assertNotIn("doc-secret-token", doc.source_path)
        self.assertNotIn("minute-secret-token", minutes.source_path)
        self.assertEqual(calls[0][:2], ["docs", "+fetch"])
        self.assertEqual(calls[1][:2], ["vc", "+notes"])

    def test_lark_cli_provider_reads_wiki_backed_slides(self):
        calls = []

        def fake_runner(args):
            calls.append(args)
            if args[:3] == ["wiki", "spaces", "get_node"]:
                return {"data": {"node": {"obj_type": "slides", "obj_token": "slides-secret-token"}}}
            if args[:3] == ["slides", "xml_presentations", "get"]:
                return {"data": {"xml_presentation": {"content": "<presentation><slide><text>测试演示文稿</text></slide></presentation>"}}}
            raise AssertionError(args)

        base = Settings.default()
        settings = Settings(
            project_root=base.project_root,
            data_dir=base.data_dir,
            output_dir=base.output_dir,
            reports_dir=base.reports_dir,
            provider="feishu",
            feishu_doc_urls=("https://example.feishu.cn/wiki/wiki-secret-token",),
        )
        provider = LarkCliProvider(settings, fallback=MockProvider(settings), runner=fake_runner)

        bundle = provider.load_bundle()

        slides = next(item for item in bundle.docs if item.kind == "slides")
        self.assertIn("测试演示文稿", slides.content)
        self.assertTrue(slides.source_path.startswith("feishu://slides/"))
        self.assertNotIn("slides-secret-token", slides.source_path)
        self.assertEqual(calls[0][:3], ["wiki", "spaces", "get_node"])
        self.assertEqual(calls[1][:3], ["slides", "xml_presentations", "get"])

    def test_distributor_defaults_to_dry_run_and_masks_ids(self):
        calls = []

        def fake_runner(args):
            calls.append(args)
            return {"ok": True, "chat_id": "oc_secret"}

        base = Settings.default()
        settings = Settings(
            project_root=base.project_root,
            data_dir=base.data_dir,
            output_dir=base.output_dir,
            reports_dir=base.reports_dir,
            dry_run=True,
            real_write=False,
            feishu_chat_id="oc_secret",
            feishu_base_token="base_secret",
            feishu_base_table_id="tbl_secret",
        )
        distributor = FeishuDistributor(settings, runner=fake_runner)

        message = distributor.send_markdown("# hello")
        task = distributor.create_task(
            ActionPreview(
                title="确认灰度",
                owner="胡宇鹏",
                due_date="2026-05-10",
                background="测试背景",
                source=SourceRef(id="m1", title="测试纪要", kind="minutes", path="feishu://minutes/1"),
            )
        )
        record = distributor.upsert_base_record({"事项": "确认灰度", "状态": "todo"})

        self.assertTrue(message.dry_run)
        self.assertTrue(task.dry_run)
        self.assertTrue(record.dry_run)
        self.assertIn("--dry-run", calls[0])
        self.assertIn("--dry-run", calls[1])
        self.assertIn("--dry-run", calls[2])
        self.assertIn("bot", calls[0])
        self.assertIn("--dry-run", message.command)
        self.assertIn("--dry-run", task.command)
        self.assertIn("--dry-run", record.command)
        self.assertNotIn("oc_secret", " ".join(message.command))
        self.assertNotIn("base_secret", " ".join(record.command))


if __name__ == "__main__":
    unittest.main()
