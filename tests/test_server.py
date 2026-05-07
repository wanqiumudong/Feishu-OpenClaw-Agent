import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from config import Settings
from server.app import create_app
from server.event_handler import handle_feishu_event
from server.message_router import route_message


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
        self.assertEqual(route_message("请生成会前背景包").workflow, "pre_meeting")
        self.assertEqual(route_message("请整理会后行动项").workflow, "post_meeting")
        self.assertEqual(route_message("推进表对账").workflow, "reconcile")
        self.assertEqual(route_message("项目全局主题").workflow, "graphrag_global")
        self.assertEqual(route_message("上次技术评审风险是什么").workflow, "graphrag_local")

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

    def test_direct_handler_ignores_unsupported_event(self):
        result = handle_feishu_event(
            {"header": {"event_type": "unknown.event"}, "event": {}},
            {},
            self.settings,
        )

        self.assertEqual(result["status"], "ignored")


if __name__ == "__main__":
    unittest.main()
