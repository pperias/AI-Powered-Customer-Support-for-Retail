"""Context for judges and traces: what the store's systems know, and what was said before this message."""
from .session import Session
from .tools import orders
from .tools.warranty import is_in_warranty


def item_facts(session: Session) -> str:
    """The selected item and its warranty status, so a judge can tell facts from inventions."""
    order = orders.get_order(session.order_id, session.customer_id) if session.order_id else None
    item = next((i for i in order["items"] if i["item_id"] == session.item_id), None) if order else None
    if item is None:
        return "No item selected yet."
    status = "in warranty" if is_in_warranty(item["order_date"]) else "out of warranty"
    facts = f"Item: {item['name']}. Ordered {item['order_date']} ({status}, 12-month warranty)."
    if session.steps_tried:
        facts += f" Troubleshooting steps given so far: {len(session.steps_tried)}."
    return facts


def recent_conversation(session: Session, messages: int = 6) -> str:
    """The messages before the current one, oldest first."""
    earlier = session.history[:-1][-messages:]
    if not earlier:
        return "(start of conversation)"
    return "\n".join(f"{'Customer' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in earlier)
