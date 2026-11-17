from dataclasses import dataclass, field


@dataclass
class Session:
    """Working memory for one conversation (Version 1 has no memory across sessions)."""

    order_id: str | None = None
    item_id: str | None = None
    product_id: str | None = None
    topics_covered: list[str] = field(default_factory=list)
    steps_tried: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)  # {"role": "user" | "assistant", "content": str}
