import json
from datetime import date
from pathlib import Path

from ..handoff import summary
from ..session import Session
from ..tools import orders
from ..tools.warranty import is_in_warranty
from ..types import Reply

STEPS_FILE = Path(__file__).resolve().parents[3] / "data" / "troubleshooting_steps.json"


def steps_for(product_id: str | None) -> list[str]:
    steps = json.loads(STEPS_FILE.read_text())
    return steps.get(product_id or "", steps["default"])


def is_confirmed_defective(session: Session, step_result: str) -> bool:
    """Defective gate (code): every scripted step was tried and the last one did not fix it."""
    return step_result != "fixed" and len(session.steps_tried) >= len(steps_for(session.product_id))


def hand_off(session: Session, today: date | None = None) -> Reply:
    """Warranty check, then hand off. Version 1 never creates the return itself."""
    order = orders.get_order(session.order_id, session.customer_id)
    item = next((i for i in order["items"] if i["item_id"] == session.item_id), None) if order else None
    session.handed_off = True
    if item is None:
        return Reply("I couldn't confirm this item, so I'm connecting you to our support team.", needs_human=True,
                     handoff_summary=summary(session, "defective, item not found"))
    if is_in_warranty(item["order_date"], today):
        return Reply(
            f"Thanks for trying those steps. Your {item['name']} looks defective and is still under warranty "
            "(ordered within the last 12 months). I'm handing you to our returns team to arrange a replacement or return.",
            needs_human=True,
            handoff_summary=summary(session, "defective, in warranty: start a return"),
        )
    return Reply(
        f"Thanks for trying those steps. Your {item['name']} looks defective, but it was ordered more than 12 months "
        "ago, so it is outside the warranty. I'm connecting you to a support agent to discuss your options.",
        needs_human=True,
        handoff_summary=summary(session, "defective, out of warranty"),
    )


def answer(session: Session, message: str, step_result: str = "none") -> Reply:
    """Scripted troubleshooting, one step at a time, tracked in session.steps_tried.

    TODO(RAG owner): the steps could come from rag.retrieve once the manuals are indexed.
    """
    if step_result == "fixed" and session.steps_tried:
        session.steps_tried.clear()
        return Reply("Great, I'm glad that fixed it. Is there anything else I can help with?")
    if is_confirmed_defective(session, step_result):
        return hand_off(session)
    step = steps_for(session.product_id)[len(session.steps_tried)]
    session.steps_tried.append(step)
    number = len(session.steps_tried)
    prefix = "Sorry to hear that. Let's try a few things. " if number == 1 else "Thanks. Next, "
    return Reply(f"{prefix}Step {number}: {step}\n\nDid that fix it?")
