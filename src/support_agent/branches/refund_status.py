from ..session import Session
from ..tools.returns import get_return_status
from ..types import Reply


def answer(session: Session, message: str) -> Reply:
    """Look up the return and draft a reply. A human reviews it before it is sent."""
    ret = get_return_status(session.order_id, session.item_id)
    if ret is None:
        return Reply("I could not find a return for this item.", needs_human=True)
    return Reply(
        f"Your return is {ret['status'].replace('_', ' ')}. Refund: {ret['refund_status'].replace('_', ' ')}.",
        needs_human=True,
    )
