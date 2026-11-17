# Interfaces between the three areas

Keep these signatures stable. Change anything inside them freely.

## RAG (owner: RAG)

```python
# src/support_agent/rag/interface.py
def retrieve(query: str, product_id: str | None = None, k: int = 4) -> list[Passage]
```

- `Passage(text, source, score)` is defined in `src/support_agent/types.py`.
- Put source documents in `data/docs/`. `product_id` values come from `data/mock_orders.json`.
- Used by the product information and troubleshooting branches.

## Observability (owner: observability and evals)

```python
# src/support_agent/observability/tracing.py
def setup_tracing() -> None                     # called once at startup
def trace_step(name: str, **attributes)         # context manager around each workflow step
```

- Steps traced today: `order_precheck`, `intent_gate`, and one span per branch.
- Add a span for each LLM call and each tool call inside your own folder.

## Evals (owner: observability and evals)

- `evals/conversations.jsonl`: one conversation per line, with `expected_intent` for every message.
- `evals/run_evals.py`: run from the project root with `python evals/run_evals.py`.

## Core agent (owner: Priya)

- `workflow.handle_message(session, message) -> Reply`: one message in, one reply out. The intent gate runs on every message.
- `Session` holds the working memory: order, item, topics covered and steps tried.
- Tools are read-only in Version 1: order lookup, warranty check and return status. Returns are handed off to a separate flow.
