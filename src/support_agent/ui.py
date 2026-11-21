"""Web chat for the demo: the customer chat on the left, the support team's console on the right.

Run from the project root: python -m support_agent.ui   (then open http://localhost:8000)
"""
import gradio as gr

from .observability import setup_tracing
from .session import Session
from .types import Reply
from .workflow import handle_message, send_reviewed

CUSTOMERS = {"C100": "Maya Thompson", "C200": "Daniel Okafor"}  # C100 owns A1001 and A1002, C200 owns A1003
PORT = 8000
WAITING = "One moment, a member of our team is checking this for you."
GREETING = "I can help with product questions, troubleshooting and refund status. What's your order ID?"
QUICK_MESSAGES = [
    "A1001", "1", "What resolution is the display?", "my TV won't turn on", "still nothing",
    "A1002 where is my refund?", "I want to talk to a person",
]
CSS = """
#new-chat { align-self: flex-end; }
.panel-title h3 { margin: 0 0 4px 0; }
.panel-note { color: var(--body-text-color-subdued); font-size: 0.9em; }
.queue-empty { padding: 8px 12px; border-radius: 8px; background: var(--background-fill-secondary); }
.queue-waiting { padding: 8px 12px; border-radius: 8px; background: #fff4d6; color: #6b4e00; font-weight: 600; }
"""


def case_view(session: Session, draft: Reply | None) -> str:
    """The case card a support person sees, built from the agent's working memory for this chat."""
    if session.handed_off:
        status = "🙋 Handed to a person"
    elif draft is not None:
        status = "⏳ Waiting for your approval"
    else:
        status = "🤖 Agent is handling it"
    steps = "".join(f"\n{n}. {step}" for n, step in enumerate(session.steps_tried, 1)) or " none"
    return (
        f"**Status:** {status}  \n"
        f"**Customer:** {CUSTOMERS[session.customer_id]} ({session.customer_id}) · **Order:** {session.order_id or '—'} · "
        f"**Item:** {session.item_name or '—'}  \n"
        f"**Topics so far:** {', '.join(session.topics_covered) or '—'} · **Messages:** {session.turns}\n\n"
        f"**Troubleshooting steps given:**{steps}"
    )


def memory_view(session: Session) -> dict:
    """Raw working memory, for the developer view."""
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


def console(session: Session, draft: Reply | None, handoff=None):
    """Everything on the right-hand side, so the review controls are only usable when a reply waits."""
    if draft is None:
        queue = '<div class="queue-empty">Nothing waiting for review. Refund replies appear here.</div>'
        review = gr.update(value="", interactive=False, visible=False)
    else:
        queue = '<div class="queue-waiting">⏳ 1 refund reply is waiting. Edit it if needed, then approve.</div>'
        review = gr.update(value=draft.text, interactive=True, visible=True)
    approve = gr.update(interactive=draft is not None, visible=draft is not None)
    handoff = gr.update() if handoff is None else gr.update(value=handoff, visible=bool(handoff))
    return queue, review, approve, handoff, case_view(session, draft), memory_view(session)


def new_chat(customer: str):
    session = Session(customer_id=customer)
    greeting = [{"role": "assistant", "content": f"Hi {CUSTOMERS[customer].split()[0]}! " + GREETING}]
    return (session, greeting, None, *console(session, None, handoff=""))


def on_send(text: str, chat: list, session: Session, draft: Reply | None):
    text = text.strip()
    if not text:
        return ("", chat, session, draft, *console(session, draft))
    chat = chat + [{"role": "user", "content": text}]
    if draft is not None:  # a reply is already waiting for review; don't start another turn
        chat.append({"role": "assistant", "content": WAITING})
        return ("", chat, session, draft, *console(session, draft))

    reply = handle_message(session, text)
    if reply.needs_review:
        chat.append({"role": "assistant", "content": WAITING})
        return ("", chat, session, reply, *console(session, reply))
    chat.append({"role": "assistant", "content": reply.text})
    return ("", chat, session, None, *console(session, None, handoff=reply.handoff_summary))


def on_approve(review_text: str, chat: list, session: Session, draft: Reply | None):
    if draft is None:
        return (chat, None, *console(session, None))
    sent = send_reviewed(session, draft, review_text.strip() or draft.text)
    chat = chat + [{"role": "assistant", "content": sent.text}]
    gr.Info("Reply sent to the customer")
    return (chat, None, *console(session, None))


def build() -> gr.Blocks:
    with gr.Blocks(title="Retail Support") as demo:
        gr.Markdown("## 🛍️ Retail Support · Version 1\n"
                    "<span class='panel-note'>Left: what the customer sees. Right: what our support team sees. "
                    "Mock data only.</span>")
        session, draft = gr.State(), gr.State()
        with gr.Row(equal_height=False):
            with gr.Column(scale=3):
                with gr.Row(equal_height=False):
                    customer = gr.Dropdown([(name, cid) for cid, name in CUSTOMERS.items()], value="C100",
                                           label="Signed in as", scale=4)
                    restart = gr.Button("↺ New chat", size="md", scale=1, min_width=120, elem_id="new-chat")
                with gr.Group():
                    chat = gr.Chatbot(label="Customer chat", height=500, layout="bubble", buttons=["copy"])
                    with gr.Row():
                        message = gr.Textbox(placeholder="Type a message, e.g. A1001", show_label=False,
                                             scale=5, autofocus=True, submit_btn=False)
                        send = gr.Button("Send", variant="primary", scale=1)
                gr.Examples(QUICK_MESSAGES, inputs=message, label="Quick messages (click to fill in)")

            with gr.Column(scale=2):
                gr.Markdown("### 🧑‍💼 Support team console", elem_classes="panel-title")
                with gr.Group():
                    gr.Markdown("**Review queue**: in Version 1 a person approves every refund reply.")
                    queue = gr.HTML()
                    review = gr.Textbox(label="Draft reply to the customer", lines=4, visible=False)
                    approve = gr.Button("✓ Approve and send", variant="primary", visible=False)
                handoff = gr.Textbox(label="Handoff summary for the person taking over", lines=9,
                                     interactive=False, visible=False)
                with gr.Group():
                    gr.Markdown("**Case details**")
                    case = gr.Markdown()
                with gr.Accordion("Developer view: raw working memory", open=False):
                    memory = gr.JSON(show_label=False)

        console_outputs = [queue, review, approve, handoff, case, memory]
        reset_outputs = [session, chat, draft, *console_outputs]
        demo.load(new_chat, customer, reset_outputs)
        customer.change(new_chat, customer, reset_outputs)
        restart.click(new_chat, customer, reset_outputs)

        send_inputs = [message, chat, session, draft]
        send_outputs = [message, chat, session, draft, *console_outputs]
        message.submit(on_send, send_inputs, send_outputs)
        send.click(on_send, send_inputs, send_outputs)
        approve.click(on_approve, [review, chat, session, draft], [chat, draft, *console_outputs])
    return demo


def main() -> None:
    setup_tracing()
    build().launch(server_name="127.0.0.1", server_port=PORT, css=CSS,
                   theme=gr.themes.Soft(primary_hue="indigo", radius_size="lg"))


if __name__ == "__main__":
    main()
