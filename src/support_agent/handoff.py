from .session import Session
from .types import Intent, Reply


def summary(session: Session, reason: str) -> str:
    """Built by code from working memory, so the person taking over does not have to re-ask."""
    last_messages = [m["content"] for m in session.history if m["role"] == "user"][-3:]
    lines = [
        f"Reason: {reason}",
        f"Customer: {session.customer_id or 'unknown'}",
        f"Order: {session.order_id or 'not given'}, item: {session.item_name or 'not chosen'}",
        f"Topics covered: {', '.join(session.topics_covered) or 'none'}",
        f"Troubleshooting steps tried: {len(session.steps_tried)}",
        *[f"  - {step}" for step in session.steps_tried],
        "Last customer messages:",
        *[f"  > {m}" for m in last_messages],
    ]
    return "\n".join(lines)


def to_human(session: Session, reason: str, text: str = "I'm connecting you to a member of our support team.") -> Reply:
    session.handed_off = True
    return Reply(text, intent=Intent.ESCALATE, needs_human=True, handoff_summary=summary(session, reason))
