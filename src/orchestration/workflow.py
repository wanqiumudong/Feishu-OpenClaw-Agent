from models import EvidencePacket, KnowledgeItem


def evidence_from_items(items: list[KnowledgeItem], *, max_chars: int = 700) -> list[EvidencePacket]:
    evidence = []
    for item in items:
        excerpt = " ".join(item.content.split())[:max_chars]
        evidence.append(
            EvidencePacket(
                id=item.id,
                title=item.title,
                kind=item.kind,
                excerpt=excerpt,
                source_path=item.source_path,
            )
        )
    return evidence


def evidence_prompt(items: list[KnowledgeItem], *, max_chars: int = 700) -> str:
    lines = []
    for index, packet in enumerate(evidence_from_items(items, max_chars=max_chars), start=1):
        lines.append(
            f"[{index}] {packet.kind} | {packet.title} | {packet.source_path}\n{packet.excerpt}"
        )
    return "\n\n".join(lines)
