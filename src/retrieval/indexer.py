from models import DataBundle, KnowledgeItem


def build_index(bundle: DataBundle) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    items.extend(bundle.docs)
    items.extend(bundle.minutes)

    for risk in bundle.truth.get("risks", []):
        content = "；".join(
            [
                risk.get("title", ""),
                f"owner：{risk.get('owner', '')}",
                f"status：{risk.get('status', '')}",
                f"阻塞：{risk.get('blocker', '')}",
            ]
        )
        items.append(
            KnowledgeItem(
                id=f"truth_risk_{risk.get('title', '')}",
                title=f"风险：{risk.get('title', '')}",
                kind="truth",
                content=content,
                source_path="data/ground_truth/project_truth.json",
                tags=["risk", risk.get("status", ""), risk.get("owner", "")],
                metadata=risk,
            )
        )

    for index, decision in enumerate(bundle.truth.get("decisions", []), start=1):
        items.append(
            KnowledgeItem(
                id=f"truth_decision_{index:03d}",
                title=f"决策：{decision.get('content', '')[:24]}",
                kind="truth",
                content=decision.get("content", ""),
                source_path="data/ground_truth/project_truth.json",
                tags=["decision", decision.get("date", "")],
                metadata=decision,
            )
        )

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

    for event in bundle.calendar_events:
        content = "；".join(
            [
                event.get("title", ""),
                event.get("purpose", ""),
                f"参会人：{'、'.join(event.get('attendees', []))}",
                f"资料：{'、'.join(event.get('related_docs', []))}",
            ]
        )
        items.append(
            KnowledgeItem(
                id=event["event_id"],
                title=f"日历事件：{event['title']}",
                kind="calendar",
                content=content,
                source_path="data/calendar/events.json",
                tags=["calendar", event["event_id"]],
                metadata=event,
            )
        )
    return items
