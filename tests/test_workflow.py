from support_agent.session import Session
from support_agent.types import Intent
from support_agent.workflow import handle_message


def test_asks_for_order_id_first():
    reply = handle_message(Session(), "hello")
    assert "order ID" in reply.text


def test_single_item_order_selects_item_automatically():
    session = Session()
    handle_message(session, "my order is A1002")
    assert session.item_id == "A1002-1"


def test_multi_item_order_asks_which_item():
    session = Session()
    reply = handle_message(session, "A1001")
    assert session.item_id is None and "Which item" in reply.text
    handle_message(session, "the TV")
    assert session.item_id == "A1001-1"


def test_conversation_moves_from_product_info_to_troubleshooting():
    session = Session()
    handle_message(session, "A1001")
    handle_message(session, "the TV")
    assert handle_message(session, "what are the specs").intent == Intent.PRODUCT_INFO
    assert handle_message(session, "where is the HDMI slot").intent == Intent.PRODUCT_INFO
    assert handle_message(session, "I plugged in the power cable and there is no power").intent == Intent.TROUBLESHOOTING


def test_asking_for_a_person_escalates():
    session = Session()
    handle_message(session, "A1002")
    reply = handle_message(session, "I want to talk to a person")
    assert reply.intent == Intent.ESCALATE and reply.needs_human


def test_refund_status_is_flagged_for_human_review():
    session = Session()
    handle_message(session, "A1002")
    reply = handle_message(session, "where is my refund")
    assert reply.intent == Intent.REFUND_STATUS and reply.needs_human
