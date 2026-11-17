# AI-Powered Customer Support for Retail

A chat support agent for a consumer retail company. It answers product questions, troubleshoots problems, checks warranty and looks up refund status, so human agents can focus on cases that need judgment.

We build two versions and compare them. Version 1 is a workflow agent with read-only tools: code decides the steps, the LLM classifies each message and drafts answers, and a person reviews refund status replies. Returns are out of scope and handed to a separate flow. Version 2 is a higher-agency single agent that also handles returns.

Because a conversation can move from product questions to troubleshooting ("I plugged in the cable and there is no power"), the intent gate runs on every message. See `docs/architecture.md` for the flow and `docs/interfaces.md` for how the three areas connect.

## Team and ownership

| Area | Owner |
| --- | --- |
| Core agent: flow, intent gate, branches, tools | Priya |
| RAG: product manuals and policies | to fill |
| Observability (Arize) and evals | to fill |

## Layout

| Path | Purpose |
| --- | --- |
| `src/support_agent/` | The agent: `workflow.py`, `intent.py`, `branches/`, `tools/`, plus `rag/` and `observability/` stubs |
| `data/` | Mock orders and `docs/` for manuals and policies |
| `evals/` | Labeled conversations and eval scripts |
| `tests/` | Unit tests |
| `docs/` | Interfaces, architecture, how to share the demo |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # then add your own keys; never commit .env
python -m pytest            # run the tests
python -m support_agent.cli # try the chat in the terminal (RAG is a stub for now)
pip install -e ".[ui]" && python -m support_agent.ui  # web chat at http://localhost:8000
python evals/run_evals.py   # starter intent eval
```

The chat signs in as customer `C100` (change with `--customer`). Try order `A1001` (a TV in warranty and a soundbar out of warranty) or `A1002` (headphones with a return in progress). `A1003` belongs to another customer, so `C100` cannot see it. Refund status replies are drafts: the terminal asks you, as the reviewer, to approve or edit them before the customer sees them.

With `OPENAI_API_KEY` set, the intent gate uses the LLM; without it (or with `SUPPORT_AGENT_OFFLINE=1`, which the tests set) it uses keyword matching. See `docs/demo-script.md` for conversations to try. Read `CONTRIBUTING.md` before your first pull request.
