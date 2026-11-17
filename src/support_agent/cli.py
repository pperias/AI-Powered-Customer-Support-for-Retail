import argparse

from .observability import setup_tracing
from .session import Session
from .types import Reply
from .workflow import handle_message, send_reviewed


def review(session: Session, draft: Reply) -> Reply:
    """Stand-in for the human review screen: the reviewer approves, edits, or takes over."""
    print(f"  [review] draft for the customer: {draft.text}")
    decision = input("  [review] Enter to approve, type a new reply to edit, or 'h' to take over: ").strip()
    if decision.lower() == "h":
        session.handed_off = True
        return send_reviewed(session, draft, "A member of our team will take it from here.")
    return send_reviewed(session, draft, decision or draft.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail support chat (Version 1)")
    parser.add_argument("--customer", default="C100", help="logged-in customer (mock: C100 owns A1001 and A1002)")
    args = parser.parse_args()

    setup_tracing()
    session = Session(customer_id=args.customer)
    print(f"Retail support, signed in as {args.customer} (type 'quit' to exit)")
    while True:
        try:
            text = input("you> ").strip()
        except EOFError:
            break
        if text.lower() in {"quit", "exit"}:
            break
        if not text:
            continue
        reply = handle_message(session, text)
        if reply.needs_review:
            reply = review(session, reply)
        print(f"agent> {reply.text}")
        if reply.handoff_summary:
            print("  [handoff to human]\n" + "\n".join(f"  | {line}" for line in reply.handoff_summary.splitlines()))


if __name__ == "__main__":
    main()
