from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Session:
    """Working memory for one conversation (Version 1 has no memory across sessions)."""

    session_id: str = field(default_factory=lambda: uuid4().hex[:12])  # groups the turns of one chat in Arize
    customer_id: str | None = None  # set by the chat UI after login; only this customer's orders are visible
    order_id: str | None = None
    item_id: str | None = None
    product_id: str | None = None
    item_name: str | None = None
    topics_covered: list[str] = field(default_factory=list)
    steps_tried: list[str] = field(default_factory=list)  # troubleshooting steps already given
    history: list[dict] = field(default_factory=list)  # {"role": "user" | "assistant", "content": str}
    last_intent: str | None = None
    turns: int = 0
    unclear_turns: int = 0  # consecutive low-confidence messages
    handed_off: bool = False
