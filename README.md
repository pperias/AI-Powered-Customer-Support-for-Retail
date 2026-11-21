# AI-Powered Customer Support for Retail

A chat support agent for a consumer retail company. It answers product questions, troubleshoots problems, checks warranty and looks up refund status, so human agents can focus on cases that need judgment.

Version 1 (this repo) is a workflow agent with read-only tools: code decides the steps, the LLM classifies each message and drafts answers, and a person reviews refund status replies. Returns are out of scope and handed to a separate flow. A higher-agency version that also creates returns is designed but not built.

Because a conversation can move from product questions to troubleshooting ("I plugged in the cable and there is no power"), the intent gate runs on every message. See `docs/architecture.md` for the flow and `docs/interfaces.md` for how the three areas connect.

## Team and ownership

| Area | Owner |
| --- | --- |
| Core agent: flow, intent gate, branches, tools | Priya |
| RAG: product manuals and policies | Sid Sahgal |
| Observability (Arize) and evals | Priya |

## Layout

| Path | Purpose |
| --- | --- |
| `src/support_agent/` | The agent: `workflow.py`, `intent.py`, `branches/`, `tools/`, plus `rag/` (retrieval) and `observability/` (Arize tracing) |
| `data/` | Mock orders and `docs/` for manuals and policies |
| `evals/` | Labeled conversations and eval scripts |
| `tests/` | Unit tests |
| `docs/` | Interfaces, architecture, how to share the demo |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ui,tracing,evals]"
cp .env.example .env        # then add your OPENAI_API_KEY (and Arize keys for tracing); never commit .env
```

With `ARIZE_API_KEY` and `ARIZE_SPACE_ID` set, every chat is traced to the Arize project `retail-support-v1`: one trace per customer message, grouped by conversation in the Sessions view, with the intent gate, tool calls and LLM calls inside.

If your shell already has an old `OPENAI_API_KEY` exported, run `unset OPENAI_API_KEY` so the key in `.env` is used.

## Sample run (web UI)

Start the app and open http://localhost:8000 in your browser:

```bash
python -m support_agent.ui
```

The page has two sides. On the left is the **customer chat**, with a "Signed in as" dropdown: Maya Thompson (customer C100) or Daniel Okafor (C200). On the right is the **support team console**: the review queue for refund replies, the handoff summary when the agent hands over, and the case details (status, order, item, steps given). Quick-message buttons under the chat fill in common demo messages.

Pick the customer in "Signed in as", type the messages one at a time, and click **New chat** between scenarios.

### Mock data

| Customer | Order | Items |
| --- | --- | --- |
| C100 | A1001 | 55-inch OLED TV (in warranty), Soundbar 200 (out of warranty) |
| C100 | A1002 | Wireless Headphones X (return in progress) |
| C200 | A1003 | 55-inch OLED TV |

### 1. Troubleshooting, then warranty, then handoff to returns (C100)

```
A1001
1
my TV won't turn on
still nothing
still not working
the light is off, nothing happens
```

The agent finds the order, asks which item (1 is the TV), and gives troubleshooting steps one at a time. After the third step it says the TV is defective and under warranty and hands off to the returns team. The handoff summary on the right lists the order, the item and the steps tried.

### 2. Troubleshooting that fixes the problem (C100)

```
A1001 my soundbar has no sound
it works now
```

The agent picks the soundbar from the first message and starts step 1 straight away. "It works now" ends troubleshooting.

### 3. Defective but out of warranty (C100)

```
A1001
soundbar
no sound
still no sound
still no sound
still no sound
```

After three steps the agent says the soundbar is outside the 12-month warranty and connects the customer to a person.

### 4. Refund status with human review (C100)

```
A1002 where is my refund?
```

The customer sees "One moment, a member of our team is checking this for you." The draft reply appears in the console on the right. Edit it if you like, then click **Approve and send** (the button only appears while a reply is waiting).

### 5. Escalation (C100)

```
A1002
this is ridiculous, I've waited 3 weeks
```

The agent detects an unhappy customer and hands off with a summary. "I want to talk to a person" also hands off at any point, even before an order ID.

### 6. Out of scope (C100)

```
A1002
can you recommend a laptop to buy?
```

The agent says what it can help with and offers the team for anything else.

### 7. Access to the customer's own orders only (C200)

```
A1001
A1003
```

A1001 belongs to C100, so the agent says it could not find that order on the account. A1003 works.

### 8. Changing the subject mid-conversation (C100)

```
A1001
tv
my TV has no power
actually my soundbar has no sound too
```

The agent switches to the soundbar and starts its troubleshooting steps.

### Known limits

- **Product answers come only from the manuals and policies in `data/docs/`.** If the answer isn't there (battery life, TV weight), the agent says so instead of guessing.
- **One request per message.** "My headphones won't charge and where is my refund" gets troubleshooting only. Combined requests would need a higher-agency agent.
- **Troubleshooting steps are scripted per product, not per symptom** (`data/troubleshooting_steps.json`).

To share the running app with a teammate, see `docs/sharing-the-demo.md`.

## Tests and evals

```bash
python -m pytest                              # unit tests (offline, never call the LLM)
python evals/run_evals.py --offline           # 17 conversations that need no LLM, keyword intent gate, free
python evals/run_evals.py                     # all 31 conversations with the LLM, the LLM judge, and speed/cost metrics
python evals/run_evals.py --repeat 3          # run each conversation 3 times to find flaky cases
python evals/run_evals.py --calibrate-judge   # does the LLM judge agree with human labels?
```

See `evals/README.md` for what the evals check and how to add a case.

Read `CONTRIBUTING.md` before your first pull request.
