from support_agent import config
from support_agent.session import Session
from support_agent.types import Intent
from support_agent.workflow import handle_message, send_reviewed


def new_session(*messages: str) -> Session:
    session = Session(customer_id="C100")
    for message in messages:
        handle_message(session, message)
    return session


def test_asks_for_order_id_first():
    reply = handle_message(Session(customer_id="C100"), "hello")
    assert "order ID" in reply.text


def test_single_item_order_selects_item_automatically():
    session = new_session("my order is A1002")
    assert session.item_id == "A1002-1"


def test_multi_item_order_asks_which_item():
    session = Session(customer_id="C100")
    reply = handle_message(session, "A1001")
    assert session.item_id is None and "Which item" in reply.text
    handle_message(session, "the TV")
    assert session.item_id == "A1001-1"


def test_item_can_be_chosen_by_number():
    assert new_session("A1001", "2").item_id == "A1001-2"


def test_order_id_with_punctuation_is_found():
    assert new_session("My order is #A1001!").order_id == "A1001"


def test_question_in_the_item_selecting_message_is_answered():
    reply = handle_message(Session(customer_id="C100"), "A1002 where is my refund")
    assert reply.intent == Intent.REFUND_STATUS and "Wireless Headphones X" in reply.text


def test_customer_can_switch_item():
    session = new_session("A1001", "the TV")
    handle_message(session, "actually my soundbar is not working")
    assert session.item_id == "A1001-2"


def test_conversation_moves_from_product_info_to_troubleshooting():
    session = new_session("A1001", "the TV")
    assert handle_message(session, "what are the specs").intent == Intent.PRODUCT_INFO
    assert handle_message(session, "where is the HDMI slot").intent == Intent.PRODUCT_INFO
    reply = handle_message(session, "I plugged in the power cable and there is no power")
    assert reply.intent == Intent.TROUBLESHOOTING and "Step 1" in reply.text
    assert session.product_id == "tv-55-oled"


def test_asking_for_a_person_escalates_with_summary():
    session = new_session("A1002")
    reply = handle_message(session, "I want to talk to a person")
    assert reply.intent == Intent.ESCALATE and reply.needs_human
    assert "Wireless Headphones X" in reply.handoff_summary


def test_asking_for_a_person_works_before_order_id():
    reply = handle_message(Session(customer_id="C100"), "I need a human")
    assert reply.needs_human


def test_word_inside_another_word_does_not_escalate():
    session = new_session("A1002")
    assert handle_message(session, "I personally like it, what colours exist?").intent == Intent.PRODUCT_INFO


def test_other_customers_order_is_not_visible():
    session = Session(customer_id="C200")
    reply = handle_message(session, "A1001")
    assert session.order_id is None and "couldn't find that order on your account" in reply.text


def test_refund_status_is_held_for_human_review():
    session = new_session("A1002")
    draft = handle_message(session, "where is my refund")
    assert draft.intent == Intent.REFUND_STATUS and draft.needs_review
    assert "pending inspection" in draft.text
    assert session.history[-1]["role"] == "user"  # the draft has not been sent yet
    sent = send_reviewed(session, draft, draft.text)
    assert session.history[-1] == {"role": "assistant", "content": sent.text}


def test_troubleshooting_in_warranty_hands_off_to_returns():
    session = new_session("A1001", "the TV", "my TV won't turn on")
    handle_message(session, "still not working")
    handle_message(session, "still not working")
    reply = handle_message(session, "still not working")
    assert reply.needs_human and "under warranty" in reply.text
    assert "in warranty" in reply.handoff_summary and len(session.steps_tried) == 3


def test_troubleshooting_out_of_warranty_escalates():
    session = new_session("A1001", "soundbar", "my soundbar has no sound")
    for _ in range(3):
        reply = handle_message(session, "still not working")
    assert reply.needs_human and "outside the warranty" in reply.text


def test_fixed_step_ends_troubleshooting():
    session = new_session("A1001", "the TV", "my TV won't turn on")
    reply = handle_message(session, "yes that worked, it's fixed")
    assert "glad" in reply.text.lower() and not reply.needs_human


def test_step_limit_hands_off(monkeypatch):
    monkeypatch.setattr(config, "MAX_TURNS", 3)
    session = new_session("A1002", "what colours exist", "how heavy is it")
    reply = handle_message(session, "and the battery?")
    assert reply.needs_human and "step limit" in reply.handoff_summary


def test_unclear_item_answer_asks_differently():
    session = new_session("A1001")
    reply = handle_message(session, "yes")
    assert "didn't catch which item" in reply.text
    handle_message(session, "1")
    assert session.item_id == "A1001-1"


def test_message_with_no_words_does_not_call_the_gate():
    reply = handle_message(new_session("A1002"), "...")
    assert reply.intent is None and "How can I help" in reply.text


def test_order_ids_and_filler_only_get_a_greeting():
    reply = handle_message(Session(customer_id="C100"), "A1003 or maybe A1002")
    assert "found your Wireless Headphones X" in reply.text
