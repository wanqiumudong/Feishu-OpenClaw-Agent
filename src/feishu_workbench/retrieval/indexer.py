from feishu_workbench.models import DataBundle, KnowledgeItem


def build_index(bundle: DataBundle) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    items.extend(bundle.docs)
    items.extend(bundle.minutes)

    for message in bundle.chat_messages:
        items.append(
            KnowledgeItem(
                id=message["id"],
                title=f"群聊消息 {message['id']} - {message['sender']}",
                kind="chat",
                content=message["text"],
                source_path="data/chats/project_chat.jsonl",
                tags=message.get("tags", []),
                metadata=message,
            )
        )

    for task in bundle.tasks:
        content = "；".join(
            [
                task["title"],
                f"负责人：{task['owner']}",
                f"状态：{task['status']}",
                f"阻塞：{task.get('blocker', '')}",
                f"来源：{task.get('source', '')}",
            ]
        )
        items.append(
            KnowledgeItem(
                id=task["id"],
                title=f"任务：{task['title']}",
                kind="task",
                content=content,
                source_path="data/tasks/tasks.json",
                tags=[task["priority"], task["status"], task["owner"]],
                metadata=task,
            )
        )

    for row in bundle.board_rows:
        items.append(
            KnowledgeItem(
                id=f"board_{row['item']}",
                title=f"推进表：{row['item']}",
                kind="base",
                content="；".join(row.values()),
                source_path="data/base/priority_board.csv",
                tags=[row["priority"], row["status"], row["owner"]],
                metadata=row,
            )
        )
    return items
