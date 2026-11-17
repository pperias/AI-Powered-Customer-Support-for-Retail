"""Web chat for the demo: the customer chat on the left, the support agent console on the right.

Run from the project root: python -m support_agent.ui   (then open http://localhost:8000)
"""
import gradio as gr

from .handoff import summary
from .observability import setup_tracing
from .session import Session
from .types import Reply
from .workflow import handle_message, send_reviewed

CUSTOMERS = ["C100", "C200"]  # mock logins: C100 owns A1001 and A1002, C200 owns A1003
PORT = 8000
WAITING = "One moment, a member of our team is checking this for you."


def memory_view(session: Session) -> dict:
    """The working memory shown in the console, so the demo can show what the agent remembers."""
    return {
        "customer": session.customer_id,
        "order": session.order_id,
        "item": session.item_name,
        "last_intent": session.last_intent,
        "topics_covered": session.topics_covered,
        "steps_tried": len(session.steps_tried),
        "turns": session.turns,
        "handed_off": session.handed_off,
    }


def new_chat(customer: str):
    session = Session(customer_id=customer)
    greeting = [{"role": "assistant", "content": "Hi! I can help with product questions, troubleshooting "
                 "and refund status. What's your order ID?"}]
    return session, greeting, None, gr.update(value="", interactive=False), "", memory_view(session)


def on_send(text: str, chat: list, session: Session, draft: Reply | None):
    text = text.strip()
    if not text:
        return "", chat, session, draft, gr.update(), gr.update(), memory_view(session)
    chat = chat + [{"role": "user", "content": text}]
    if draft is not None:  # a reply is already waiting for review; don't start another turn
        chat.append({"role": "assistant", "content": WAITING})
        return "", chat, session, draft, gr.update(), gr.update(), memory_view(session)

    reply = handle_message(session, text)
    handoff = gr.update()
    if reply.needs_review:
        chat.append({"role": "assistant", "content": WAITING})
        review = gr.update(value=reply.text, interactive=True)
        return "", chat, session, reply, review, handoff, memory_view(session)
    chat.append({"role": "assistant", "content": reply.text})
    if reply.handoff_summary:
        handoff = reply.handoff_summary
    return "", chat, session, None, gr.update(), handoff, memory_view(session)


def on_approve(review_text: str, chat: list, session: Session, draft: Reply | None):
    if draft is None:
        return chat, None, gr.update(), memory_view(session)
    sent = send_reviewed(session, draft, review_text.strip() or draft.text)
    chat = chat + [{"role": "assistant", "content": sent.text}]
    return chat, None, gr.update(value="", interactive=False), memory_view(session)


def on_take_over(chat: list, session: Session, draft: Reply | None):
    text = "A member of our team will take it from here."
    if draft is not None:
        send_reviewed(session, draft, text)
    session.handed_off = True
    chat = chat + [{"role": "assistant", "content": text}]
    return (chat, None, gr.update(value="", interactive=False),
            summary(session, "reviewer took over"), memory_view(session))


def build() -> gr.Blocks:
    with gr.Blocks(title="Retail Support") as demo:
        gr.Markdown("## Retail Support · Version 1")
        session, draft = gr.State(), gr.State()
        with gr.Row():
            with gr.Column(scale=3):
                customer = gr.Dropdown(CUSTOMERS, value=CUSTOMERS[0], label="Signed in as (mock)")
                chat = gr.Chatbot(label="Customer chat", height=480)
                with gr.Row():
                    message = gr.Textbox(placeholder="Type a message, e.g. A1001", show_label=False, scale=5)
                    send = gr.Button("Send", variant="primary", scale=1)
                restart = gr.Button("New chat", size="sm")
            with gr.Column(scale=2):
                gr.Markdown("### Support agent console")
                review = gr.Textbox(label="Refund reply waiting for review (edit if needed)", lines=4,
                                    interactive=False)
                with gr.Row():
                    approve = gr.Button("Approve and send", variant="primary")
                    take_over = gr.Button("Take over")
                handoff = gr.Textbox(label="Handoff summary", lines=10, interactive=False)
                memory = gr.JSON(label="Working memory")

        reset_outputs = [session, chat, draft, review, handoff, memory]
        demo.load(new_chat, customer, reset_outputs)
        customer.change(new_chat, customer, reset_outputs)
        restart.click(new_chat, customer, reset_outputs)

        send_outputs = [message, chat, session, draft, review, handoff, memory]
        message.submit(on_send, [message, chat, session, draft], send_outputs)
        send.click(on_send, [message, chat, session, draft], send_outputs)
        approve.click(on_approve, [review, chat, session, draft], [chat, draft, review, memory])
        take_over.click(on_take_over, [chat, session, draft], [chat, draft, review, handoff, memory])
    return demo


def main() -> None:
    setup_tracing()
    build().launch(server_name="127.0.0.1", server_port=PORT)


if __name__ == "__main__":
    main()
