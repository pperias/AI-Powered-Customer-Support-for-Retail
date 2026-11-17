from .branches import product_info, refund_status, troubleshooting
from .intent import classify_intent
from .observability import trace_step
from .session import Session
from .tools import orders
from .types import Intent, Reply

BRANCHES = {
    Intent.PRODUCT_INFO: product_info.answer,
    Intent.TROUBLESHOOTING: troubleshooting.answer,
    Intent.REFUND_STATUS: refund_status.answer,
}


def handle_message(session: Session, message: str) -> Reply:
    """One customer message in, one reply out. The intent gate runs on EVERY message."""
    session.history.append({"role": "user", "content": message})
    reply = _route(session, message)
    session.history.append({"role": "assistant", "content": reply.text})
    return reply


def _route(session: Session, message: str) -> Reply:
    # Pre-check: once per session, until an order and an item are selected.
    if session.order_id is None:
        with trace_step("order_precheck"):
            order_id = orders.find_order_id(message)
        if order_id is None:
            return Reply("Please share your order ID so I can look up your purchase.")
        session.order_id = order_id

    if session.item_id is None:
        order = orders.get_order(session.order_id)
        item = orders.select_item(order, message)
        if item is None:
            names = ", ".join(i["name"] for i in order["items"])
            return Reply(f"I found your order. Which item is this about? ({names})")
        session.item_id, session.product_id = item["item_id"], item["product_id"]
        return Reply(f"Thanks, I found your {item['name']}. How can I help?")

    with trace_step("intent_gate"):
        intent = classify_intent(session, message)
    if intent == Intent.ESCALATE:
        return Reply("Connecting you to a human agent.", intent=intent, needs_human=True)
    with trace_step(intent.value):
        reply = BRANCHES[intent](session, message)
    reply.intent = intent
    return reply
