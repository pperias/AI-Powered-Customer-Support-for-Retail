# Evals

Owner: observability and evals. `conversations.jsonl` holds labeled conversations (one JSON object per line) with the expected intent for every message, including conversations that change intent midway. `run_evals.py` is a starter that scores the intent gate. Extend it with retrieval evals, LLM judges and Arize experiments.
