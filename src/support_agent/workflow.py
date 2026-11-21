from . import config, handoff
from .facts import item_facts, recent_conversation
from .branches import product_info, refund_status, troubleshooting
from .intent import classify
from .observability import conversation, set_attributes, trace_step
from .session import Session
from .tools import orders
from .types import Intent, Reply

FILLER_WORDS = {"my", "order", "id", "is", "the", "it", "its", "it's", "about", "for", "hi", "hello", "hey",
                "number", "item", "one", "this", "a", "an", "please", "thanks", "and", "or", "maybe",
                "actually", "s", "regarding", "re", "question", "help", "with", "i", "have", "need", "on"}


def handle_message(session: Session, message: str) -> Reply:
    """One customer message in, one reply out. The intent gate runs on EVERY message.

    A reply with needs_review=True is a draft: show it to a person first, then call send_reviewed().
    """
    session.history.append({"role": "user", "content": message})
    session.turns += 1
    with conversation(session.session_id, session.customer_id), \
            trace_step("turn", input__value=message, turn=session.turns,
                       recent_conversation=recent_conversation(session)) as span:
        reply = _route(session, message)
        set_attributes(span, output__value=reply.text, intent=reply.intent.value if reply.intent else "none",
                       needs_human=reply.needs_human, needs_review=reply.needs_review,
                       order_id=session.order_id, item_id=session.item_id, facts=item_facts(session))
    if not reply.needs_review:
        session.history.append({"role": "assistant", "content": reply.text})
    return reply


def send_reviewed(session: Session, draft: Reply, approved_text: str) -> Reply:
    """Human checkpoint: the reviewer approved or edited a draft, so it can go to the customer."""
    session.history.append({"role": "assistant", "content": approved_text})
    return Reply(approved_text, intent=draft.intent)


def _route(session: Session, message: str) -> Reply:
    if session.handed_off:
        return Reply("A member of our team has your conversation and will reply here shortly.", needs_human=True)
    if session.turns > config.MAX_TURNS:
        return handoff.to_human(session, "step limit reached")

    if not orders.WORD_RE.search(message.lower()):  # "...", "?": nothing to classify
        return Reply("How can I help? You can ask about your product, a problem with it, or a refund.")

    # Intent gate first, so "I need a person" works even before an order ID is given.
    with trace_step("intent_gate", input__value=message) as span:
        result = classify(session, message)
        set_attributes(span, output__value=result.intent.value, confidence=result.confidence,
                       unhappy=result.unhappy, step_result=result.step_result)
    if result.intent == Intent.ESCALATE:
        return handoff.to_human(session, "customer asked for a person")
    if result.unhappy:
        return handoff.to_human(session, "customer is unhappy",
                                "I'm sorry this has been frustrating. I'm connecting you to a member of our support team.")

    # Pre-check (code): an order this customer owns. A new order ID in a later message switches orders.
    with trace_step("order_lookup", kind="TOOL", input__value=message) as span:
        order_id = orders.find_order_id(message, session.customer_id)
        set_attributes(span, output__value=order_id or "not found")
    just_found_order = bool(order_id and order_id != session.order_id)
    if just_found_order:
        session.order_id, session.item_id, session.product_id, session.item_name = order_id, None, None, None
    if session.order_id is None:
        # same reply for "doesn't exist" and "someone else's order", so other customers' orders stay hidden
        if orders.ORDER_ID_RE.search(message):
            return Reply("I couldn't find that order on your account. Please check the order ID "
                         "in your confirmation email.")
        return Reply("Please share your order ID so I can look up your purchase.")

    # Item selection: every message, so "actually my soundbar..." switches item. Once an item is chosen,
    # the LLM decides whether a mention is a switch ("where do I plug in a soundbar?" about the TV is not).
    order = orders.get_order(session.order_id, session.customer_id)
    item = orders.select_item(order, message)
    if session.item_id is not None and result.from_llm:
        item = orders.item_by_name(order, result.help_with)
    just_selected = item is not None and item["item_id"] != session.item_id
    if just_selected:
        session.item_id, session.product_id, session.item_name = item["item_id"], item["product_id"], item["name"]
        session.steps_tried.clear()
    if session.item_id is None:
        names = ", ".join(f"{n}. {i['name']}" for n, i in enumerate(order["items"], 1))
        if just_found_order:
            return Reply(f"I found your order. Which item is this about? ({names})")
        if len(orders.WORD_RE.findall(message)) >= 3:  # a real question, not "yes": keep it for later
            session.pending_question = message
            return Reply(f"Happy to help. Which item is your question about? ({names})")
        return Reply(f"Sorry, I didn't catch which item. Please reply with the number or the name: {names}")
    if just_selected and _only_identifiers(message, order):
        if session.pending_question:  # "what resolution is the display?" then "1": answer the question now
            pending, session.pending_question = session.pending_question, None
            return _route(session, pending)
        return Reply(f"Thanks, I found your {session.item_name}. How can I help?")
    session.pending_question = None

    if result.intent == Intent.OUT_OF_SCOPE:
        return Reply("I can help with product questions, troubleshooting and refund status for your order. "
                     "For anything else, I can connect you with our team.", intent=result.intent)
    if result.confidence < config.MIN_CONFIDENCE:
        session.unclear_turns += 1
        if session.unclear_turns >= config.MAX_UNCLEAR_TURNS:
            return handoff.to_human(session, "intent unclear after a clarifying question")
        return Reply(f"Just to check: is this a question about your {session.item_name}, a problem with it, "
                     "or about a refund?")
    session.unclear_turns = 0

    if result.intent.value not in session.topics_covered and result.intent != Intent.PRODUCT_INFO:
        session.topics_covered.append(result.intent.value)
    with trace_step(result.intent.value):
        if result.intent == Intent.TROUBLESHOOTING:
            reply = troubleshooting.answer(session, message, result.step_result)
        elif result.intent == Intent.REFUND_STATUS:
            reply = refund_status.answer(session, message)
        else:
            reply = product_info.answer(session, message)
    session.last_intent = result.intent.value
    reply.intent = reply.intent or result.intent
    return reply


def _only_identifiers(message: str, order: dict) -> bool:
    """True for "A1001", "the TV", "2": the message picked an order or item but asked nothing."""
    words = orders.WORD_RE.findall(message.lower())
    return all(w in FILLER_WORDS or w in orders.item_words(order) or w.isdigit()
               or orders.ORDER_ID_RE.fullmatch(w) for w in words)
