import json

from .orders import DATA_FILE


def get_return_status(order_id: str, item_id: str) -> dict | None:
    """Read-only lookup. Version 1 never creates returns."""
    for ret in json.loads(DATA_FILE.read_text()).get("returns", []):
        if ret["order_id"] == order_id.upper() and ret["item_id"] == item_id:
            return ret
    return None
