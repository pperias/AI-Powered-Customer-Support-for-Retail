import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "mock_orders.json"

ORDER_ID_RE = re.compile(r"\b([A-Za-z]\d{4})\b")  # A1001, also inside "#A1001!" or "A1001-2"
WORD_RE = re.compile(r"[a-z0-9]+")


def _load() -> dict:
    return json.loads(DATA_FILE.read_text())


def get_order(order_id: str, customer_id: str | None = None) -> dict | None:
    """Read-only lookup. With a customer_id, another customer's order is treated as not found."""
    for order in _load()["orders"]:
        if order["order_id"] == order_id.upper():
            if customer_id is not None and order.get("customer_id") != customer_id:
                return None
            return order
    return None


def find_order_id(text: str, customer_id: str | None = None) -> str | None:
    """Pre-check helper: return the first order ID in the text that this customer owns."""
    for candidate in ORDER_ID_RE.findall(text):
        if get_order(candidate, customer_id):
            return candidate.upper()
    return None


def select_item(order: dict, text: str) -> dict | None:
    """An order can have many items. Pick the one the customer means, or None if unclear.

    Accepts the item's position ("2"), its item ID, or a keyword from its name ("the TV").
    """
    items = order["items"]
    if len(items) == 1:
        return items[0]
    lowered = text.lower()
    for item in items:
        if item["item_id"].lower() in lowered:
            return item
    choice = lowered.strip().rstrip(".")
    if choice.isdigit():
        index = int(choice) - 1
        return items[index] if 0 <= index < len(items) else None
    words = set(WORD_RE.findall(lowered))
    matches = [i for i in items if words & set(i["keywords"])]
    return matches[0] if len(matches) == 1 else None


def item_by_name(order: dict, name: str | None) -> dict | None:
    """The item the intent gate named, matched loosely ("soundbar 200" or "Soundbar 200")."""
    if not name:
        return None
    lowered = name.lower().strip()
    return next((i for i in order["items"] if i["name"].lower() == lowered or lowered in i["name"].lower()), None)


def item_words(order: dict) -> set[str]:
    """Every word that only identifies an order or item, used to spot messages with no actual question."""
    words = {order["order_id"].lower()}
    for item in order["items"]:
        words |= set(item["keywords"]) | set(WORD_RE.findall(item["name"].lower()))
    return words
