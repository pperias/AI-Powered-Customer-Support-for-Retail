"""Shared types used by all three areas.

Changing this file affects everyone, so open a pull request and ask for a review.
"""
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    PRODUCT_INFO = "product_info"
    TROUBLESHOOTING = "troubleshooting"
    REFUND_STATUS = "refund_status"
    ESCALATE = "escalate"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class Passage:
    """One retrieved chunk of product or policy text (produced by rag/)."""

    text: str
    source: str
    score: float = 0.0


@dataclass
class Reply:
    """What the workflow returns for one customer message."""

    text: str
    intent: Intent | None = None
    needs_human: bool = False  # hand the conversation to a person (escalation or returns flow)
    needs_review: bool = False  # a person must approve this draft before the customer sees it
    handoff_summary: str | None = None  # context for the person taking over
