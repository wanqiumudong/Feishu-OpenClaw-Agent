import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from config import Settings
from server.app import create_app
from server.event_handler import handle_feishu_event
from server.message_router import build_capability_markdown, normalize_message_text, route_message
from server.ws_client import build_message_payload


class ServerTest(unittest.TestCase):
    def setUp(self):
        base = Settings.default()
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            project_root=base.project_root,
            data_dir=base.data_dir,
            output_dir=Path(self.tmp.name) / "outputs",
            reports_dir=Path(self.tmp.name) / "reports",
            dry_run=True,
            real_write=False,
            feishu_chat_id="oc_secret_chat",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_health_returns_runtime_status(self):
        client = TestClient(create_app(self.settings))

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["dry_run"])
        self.assertIn("registered_workflows", payload)

    def test_challenge_request_returns_challenge(self):
        client = TestClient(create_app(self.settings))

        response = client.post("/feishu/events", json={"challenge": "challenge-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"challenge": "challenge-token"})

    def test_route_message_selects_workflows(self):
        self.assertEqual(route_message("@_user_1 你能做什么").workflow, "help")
        self.assertEqual(route_message("help").workflow, "help")
        self.assertEqual(route_message("请生成会前背景包").workflow, "pre_meeting")
        self.assertEqual(route_message("明天评审会前需要准备什么").workflow, "pre_meeting")
        self.assertEqual(route_message("请整理会后行动项").workflow, "post_meeting")
        self.assertEqual(route_message("这次会议有哪些负责人和截止时间").workflow, "post_meeting")
        self.assertEqual(route_message("推进表对账").workflow, "reconcile")
        self.assertEqual(route_message("有哪些事项状态不一致").workflow, "reconcile")
        self.assertEqual(route_message("项目全局主题").workflow, "graphrag_global")
        self.assertEqual(route_message("上次技术评审风险是什么").workflow, "graphrag_local")

    def test_capability_markdown_is_generated_from_route_catalog(self):
        markdown = build_capability_markdown()

        self.assertIn("会前背景包", markdown)
        self.assertIn("会后行动项", markdown)
        self.assertIn("推进总表对账", markdown)
        self.assertIn("全局主题分析", markdown)

    def test_normalize_message_text_removes_feishu_mentions(self):
        self.assertEqual(normalize_message_text("@_user_1 你能做什么"), "你能做什么")

    def test_message_event_runs_agent_and_dry_run_reply(self):
        client = TestClient(create_app(self.settings))
        event = {
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "chat_id": "oc_secret_chat",
                    "message_id": "om_test_message",
                    "content": "{\"text\":\"推进表对账\"}",
                },
                "sender": {"sender_id": {"open_id": "ou_secret_user"}},
            },
        }

        response = client.post("/feishu/events", json=event)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["workflow"], "reconcile")
        self.assertTrue(payload["delivery"]["dry_run"])
        self.assertTrue(payload["delivery"]["ok"])
        self.assertNotIn("oc_secret_chat", str(payload))
        self.assertNotIn("ou_secret_user", str(payload))

    def test_message_event_help_reply_does_not_run_runtime(self):
        client = TestClient(create_app(self.settings))
        event = {
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "chat_id": "oc_secret_chat",
                    "message_id": "om_test_message",
                    "content": "{\"text\":\"@_user_1 你能做什么\"}",
                },
                "sender": {"sender_id": {"open_id": "ou_secret_user"}},
            },
        }

        response = client.post("/feishu/events", json=event)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["workflow"], "help")
        self.assertEqual(payload["tool_calls"], 0)
        self.assertTrue(payload["delivery"]["ok"])

    def test_direct_handler_ignores_unsupported_event(self):
        result = handle_feishu_event(
            {"header": {"event_type": "unknown.event"}, "event": {}},
            {},
            self.settings,
        )

        self.assertEqual(result["status"], "ignored")

    def test_ws_event_payload_conversion(self):
        class SenderId:
            open_id = "ou_secret_user"
            user_id = "u_secret_user"
            union_id = "on_secret_user"

        class Sender:
            sender_id = SenderId()

        class Message:
            chat_id = "oc_secret_chat"
            message_id = "om_test"
            content = '{"text":"请生成会前背景包"}'

        class Data:
            sender = Sender()
            message = Message()

        class Event:
            event = Data()

        payload = build_message_payload(Event())

        self.assertEqual(payload["header"]["event_type"], "im.message.receive_v1")
        self.assertEqual(payload["event"]["message"]["chat_id"], "oc_secret_chat")
        self.assertEqual(payload["event"]["message"]["content"], '{"text":"请生成会前背景包"}')


if __name__ == "__main__":
    unittest.main()
