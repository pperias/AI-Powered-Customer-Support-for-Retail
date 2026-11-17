from .observability import setup_tracing
from .session import Session
from .workflow import handle_message


def main() -> None:
    setup_tracing()
    session = Session()
    print("Retail support (type 'quit' to exit)")
    while True:
        try:
            text = input("you> ").strip()
        except EOFError:
            break
        if text.lower() in {"quit", "exit"}:
            break
        reply = handle_message(session, text)
        print(f"agent> {reply.text}" + ("  [human needed]" if reply.needs_human else ""))


if __name__ == "__main__":
    main()
