import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "mock_orders.json"


def _load() -> dict:
    return json.loads(DATA_FILE.read_text())


def get_order(order_id: str) -> dict | None:
    for order in _load()["orders"]:
        if order["order_id"] == order_id.upper():
            return order
    return None


def find_order_id(text: str) -> str | None:
    """Pre-check helper: return the first word in the text that is a known order ID."""
    for word in text.replace(",", " ").replace(".", " ").split():
        if get_order(word):
            return word.upper()
    return None


def select_item(order: dict, text: str) -> dict | None:
    """An order can have many items. Pick the one the customer means, or None if unclear."""
    items = order["items"]
    if len(items) == 1:
        return items[0]
    lowered = text.lower()
    matches = [i for i in items if any(k in lowered for k in i["keywords"])]
    return matches[0] if len(matches) == 1 else None
