import calendar
from datetime import date


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year, month = d.year + total // 12, total % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def is_in_warranty(order_date: str, today: date | None = None, months: int = 12) -> bool:
    """True if the item was ordered within the last `months` months (the team's 12-month rule)."""
    today = today or date.today()
    return today <= _add_months(date.fromisoformat(order_date), months)
