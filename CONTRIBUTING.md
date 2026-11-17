# Contributing

We are three people working in parallel, so each person owns one area and works on a branch.

## Who owns what

| Area | Folders | Owner |
| --- | --- | --- |
| Core agent: chat flow, intent gate, branches, tools | `src/support_agent/` (except `rag/` and `observability/`), `tests/` | Priya |
| RAG: retrieval over product manuals and policies | `src/support_agent/rag/`, `data/docs/` | to fill |
| Observability and evals | `src/support_agent/observability/`, `evals/` | to fill |

The contracts between the areas are in `docs/interfaces.md`. Keep those function signatures stable, and change the inside freely.

## Workflow

1. Pull the latest main: `git pull origin main`
2. Create a branch for your work: `git checkout -b rag/retrieval` (use your area as the prefix)
3. Commit small, clear changes
4. Push the branch and open a pull request
5. Ask one teammate to review, then merge and delete the branch

## Rules

- Do not push directly to `main`.
- Stay inside your own folders. Changes to `types.py` or `docs/interfaces.md` affect everyone, so they need a review from all three of us.
- Never commit secrets. Keys go in `.env`, which git ignores. Add new variable names to `.env.example`.
- Use mock data only, and never real customer data.
- Run the tests before opening a pull request: `python -m pytest`
