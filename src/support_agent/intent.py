from .session import Session
from .types import Intent


def classify_intent(session: Session, message: str) -> Intent:
    """Classify ONE customer message. Runs on every message, not once per session.

    TODO(Priya): replace this keyword placeholder with an LLM classifier (see llm.py) that also
    uses session.history, so a conversation can move from product questions to troubleshooting.
    """
    text = message.lower()
    if any(w in text for w in ("human", "person", "manager", "speak to someone")):
        return Intent.ESCALATE
    if any(w in text for w in ("refund", "return status", "where is my money")):
        return Intent.REFUND_STATUS
    if any(w in text for w in ("no power", "not working", "won't turn on", "doesn't work", "broken", "defective")):
        return Intent.TROUBLESHOOTING
    return Intent.PRODUCT_INFO
