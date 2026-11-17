from datetime import date

from ..session import Session
from ..tools import orders
from ..tools.warranty import is_in_warranty
from ..types import Reply


def is_confirmed_defective(session: Session, message: str) -> bool:
    """TODO(Priya): decide from the steps tried and the customer's answers that the product is defective."""
    return False


def hand_off(session: Session, today: date | None = None) -> Reply:
    """Warranty check, then hand off. Version 1 never creates the return itself."""
    order = orders.get_order(session.order_id)
    item = next(i for i in order["items"] if i["item_id"] == session.item_id)
    if is_in_warranty(item["order_date"], today):
        return Reply("This item is within warranty. I am handing you to the returns flow.", needs_human=True)
    return Reply("This item is out of warranty. I am escalating you to a human agent.", needs_human=True)


def answer(session: Session, message: str) -> Reply:
    """Scripted troubleshooting steps from the manual, tracked in session.steps_tried.

    TODO(Priya): get the steps from rag.retrieve and ask one step at a time.
    """
    if is_confirmed_defective(session, message):
        return hand_off(session)
    session.steps_tried.append(message)
    return Reply("(Troubleshooting steps are not implemented yet.)")
