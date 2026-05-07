#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export MEETINGFLOW_PROVIDER=mock
export MEETINGFLOW_DRY_RUN=1
export MEETINGFLOW_REAL_WRITE=0
export MEETINGFLOW_LLM_ENABLED=0

unset FEISHU_DOC_URLS
unset FEISHU_DOC_TEST_TOKEN
unset FEISHU_MINUTE_TOKENS
unset FEISHU_MINUTES_TEST_TOKEN
unset FEISHU_CHAT_ID
unset FEISHU_TASKLIST_ID
unset FEISHU_BASE_TOKEN
unset FEISHU_BASE_TABLE_ID
unset FEISHU_APP_ID
unset FEISHU_APP_SECRET
unset FEISHU_ENCRYPT_KEY
unset FEISHU_VERIFICATION_TOKEN

DEMO_SCALE="${DEMO_SCALE:-20}"
DEMO_DATA_SCALE="${DEMO_DATA_SCALE:-2}"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/meetingflow-demo.XXXXXX")"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

run_meetingflow() {
  python -c 'from main import main; main()' "$@"
}

run_eval() {
  python -c 'from evaluation.run_eval import main; main()' "$@"
}

run_data() {
  python -c 'from evaluation.generate_data import main; main()' "$@"
}

section() {
  printf '\n== %s ==\n' "$1"
}

section "Environment"
python --version
python -c 'from config import Settings; s = Settings.default(); print(f"provider={s.provider} dry_run={s.dry_run} real_write={s.real_write} llm_enabled={s.llm_enabled}")'

section "Unit Tests"
python -m unittest discover -s tests

section "Dataset Summary"
run_data summary --format markdown

section "Mock QA"
run_meetingflow qa --question "上次技术评审会的主要风险是什么？"

section "Pre-meeting Brief"
run_meetingflow pre-meeting --event go_no_go_review

section "Post-meeting Actions"
run_meetingflow post-meeting --minutes go_no_go_minutes

section "Reconcile Board"
run_meetingflow reconcile

section "Evidence Graph"
run_meetingflow evidence-graph --topic "Go/No-Go 灰度发布"

section "GraphRAG Local Search"
run_meetingflow graphrag --mode local --question "Go/No-Go 灰度发布有哪些阻塞？"

section "GraphRAG Global Search"
run_meetingflow graphrag --mode global --question "项目当前主要主题和风险是什么？"

section "Agent Runtime Inspect"
run_meetingflow inspect-runtime

section "Agent Runtime Trace"
run_meetingflow run --workflow qa --payload '{"question":"上次技术评审会的主要风险是什么？"}'

section "Feishu Card Preview"
run_meetingflow card-preview --workflow pre_meeting

section "Mock Event Routing"
run_meetingflow event-server --mode mock --text "请生成 Go/No-Go 会前背景包"

section "Bot Webhook Smoke"
python - <<'PY'
from fastapi.testclient import TestClient

from config import Settings
from server.app import create_app

client = TestClient(create_app(Settings.default()))
print(client.get("/health").json())
print(client.post("/feishu/events", json={"challenge": "local-challenge"}).json())
event = {
    "header": {"event_type": "im.message.receive_v1"},
    "event": {
        "message": {
            "chat_id": "oc_test_chat",
            "message_id": "om_test",
            "content": "{\"text\":\"推进表对账\"}",
        },
        "sender": {"sender_id": {"open_id": "ou_test_user"}},
    },
}
print(client.post("/feishu/events", json=event).json())
PY

section "Agent Engineering Report"
run_meetingflow agent-report

section "Submission Pack"
run_meetingflow submission-pack

section "Full Harness"
run_eval full --scale "$DEMO_SCALE" --output-dir "$TMP_ROOT/reports/full"

section "Synthetic Data Smoke"
run_data generate --scale "$DEMO_DATA_SCALE" --output-dir "$TMP_ROOT/generated-data"
find "$TMP_ROOT/generated-data" -type f | sort | sed "s#^$TMP_ROOT/##"

section "Done"
printf 'Safe demo completed with mock provider, dry-run enabled, and real writes disabled.\n'
