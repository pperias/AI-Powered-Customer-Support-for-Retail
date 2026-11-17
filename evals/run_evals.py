"""Starter eval: checks the intent gate against labeled conversations, message by message.

Run from the project root: python evals/run_evals.py
The evals owner extends this (LLM judges, retrieval evals, Arize experiments).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.intent import classify_intent  # noqa: E402
from support_agent.session import Session  # noqa: E402


def main() -> None:
    total = correct = 0
    for line in (ROOT / "evals" / "conversations.jsonl").read_text().splitlines():
        convo = json.loads(line)
        session = Session(order_id=convo["order_id"], item_id=convo["item_id"])
        for turn in convo["turns"]:
            predicted = classify_intent(session, turn["message"]).value
            total += 1
            correct += predicted == turn["expected_intent"]
            if predicted != turn["expected_intent"]:
                print(f"MISS {convo['id']}: {turn['message']!r} -> {predicted}, expected {turn['expected_intent']}")
    print(f"Intent accuracy: {correct}/{total}")


if __name__ == "__main__":
    main()
