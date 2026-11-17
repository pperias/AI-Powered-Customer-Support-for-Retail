from ..session import Session
from ..tools.returns import get_return_status
from ..types import Reply


def answer(session: Session, message: str) -> Reply:
    """Look up the return and draft a reply. A human approves the draft before the customer sees it."""
    ret = get_return_status(session.order_id, session.item_id)
    if ret is None:
        text = f"I couldn't find a return for your {session.item_name}. If you sent it back recently, it may not be registered yet."
    else:
        text = (f"Your return for the {session.item_name} is {ret['status'].replace('_', ' ')}. "
                f"Refund status: {ret['refund_status'].replace('_', ' ')}.")
    return Reply(text, needs_review=True)
