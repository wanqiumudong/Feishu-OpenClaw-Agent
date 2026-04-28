from feishu_workbench.distribution.renderer import render_reconcile_summary
from feishu_workbench.models import ReconcileResult, SourceRef
from feishu_workbench.providers.mock_provider import MockProvider


def reconcile_board(provider: MockProvider) -> ReconcileResult:
    bundle = provider.load_bundle()
    new_items = []
    status_updates = []
    blocker_updates = []

    for task in bundle.tasks:
        board_row = _find_board_row(task["title"], bundle.board_rows)
        if not board_row and task["status"] in {"todo", "blocked", "in_progress"}:
            new_items.append(
                {
                    "title": task["title"],
                    "owner": task["owner"],
                    "source": task["source"],
                    "reason": "任务存在但推进总表缺失",
                }
            )
            continue
        if board_row and board_row["status"] != task["status"]:
            status_updates.append(
                {
                    "title": task["title"],
                    "status": f"{board_row['status']} -> {task['status']}",
                    "source": task["source"],
                }
            )
        if board_row and task.get("blocker") and board_row.get("blocker") != task["blocker"]:
            blocker_updates.append(
                {
                    "title": task["title"],
                    "blocker": task["blocker"],
                    "source": task["source"],
                }
            )

    chat_blockers = [
        message
        for message in bundle.chat_messages
        if "阻塞" in message["text"] or "延期" in message["text"] or "漏了" in message["text"]
    ][:5]
    for message in chat_blockers:
        blocker_updates.append(
            {
                "title": f"群聊线索 {message['id']}",
                "blocker": message["text"],
                "source": "project_chat",
            }
        )

    sources = [
        SourceRef(id="tasks", title="任务列表", kind="task", path="data/tasks/tasks.json"),
        SourceRef(id="board", title="重点事项推进总表", kind="base", path="data/base/priority_board.csv"),
        SourceRef(id="chat", title="项目群聊天记录", kind="chat", path="data/chats/project_chat.jsonl"),
    ]
    result = ReconcileResult(
        markdown="",
        new_items=new_items,
        status_updates=status_updates,
        blocker_updates=blocker_updates,
        sources=sources,
    )
    return ReconcileResult(
        markdown=render_reconcile_summary(result),
        new_items=new_items,
        status_updates=status_updates,
        blocker_updates=blocker_updates,
        sources=sources,
    )


def _find_board_row(task_title: str, board_rows: list[dict]) -> dict | None:
    for row in board_rows:
        item = row["item"]
        if task_title == item or task_title in item or item in task_title:
            return row
    return None
