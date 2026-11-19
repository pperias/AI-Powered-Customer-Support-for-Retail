"""Latency, token and cost capture for eval runs, without changing the app.

install_hooks() wraps the OpenAI SDK's chat and embedding calls. Between start() and stop() in one
thread (one conversation), every call's model, tokens and duration is recorded. Judge calls happen
outside start()/stop(), so they are not counted as app cost.
"""
import threading
import time
from statistics import mean, median, quantiles

# USD per 1M tokens (input, output). Verify against openai.com/api/pricing before quoting costs.
PRICES = {"gpt-4o-mini": (0.15, 0.60), "text-embedding-3-small": (0.02, 0.0)}

_local = threading.local()


def install_hooks() -> None:
    from openai.resources.chat.completions import Completions
    from openai.resources.embeddings import Embeddings

    for cls, kind in ((Completions, "chat"), (Embeddings, "embedding")):
        if getattr(cls.create, "_eval_metrics", False):
            continue
        original = cls.create

        def create(self, *args, _original=original, _kind=kind, **kwargs):
            started = time.perf_counter()
            response = _original(self, *args, **kwargs)
            calls = getattr(_local, "calls", None)
            if calls is not None:
                usage = getattr(response, "usage", None)
                calls.append({
                    "kind": _kind,
                    "model": getattr(response, "model", None) or kwargs.get("model", ""),
                    "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                    "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
                    "seconds": time.perf_counter() - started,
                })
            return response

        create._eval_metrics = True
        cls.create = create


def start() -> None:
    _local.calls = []


def stop() -> list[dict]:
    calls, _local.calls = getattr(_local, "calls", None) or [], None
    return calls


def call_cost(call: dict) -> float | None:
    price = next((p for model, p in PRICES.items() if call["model"].startswith(model)), None)
    if price is None:
        return None
    return (call["input_tokens"] * price[0] + call["output_tokens"] * price[1]) / 1_000_000


def conversation_metrics(calls: list[dict], turn_seconds: list[float]) -> dict:
    costs = [call_cost(c) for c in calls]
    return {
        "turn_seconds": turn_seconds,
        "chat_calls": sum(c["kind"] == "chat" for c in calls),
        "embedding_calls": sum(c["kind"] == "embedding" for c in calls),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "cost_usd": sum(c for c in costs if c is not None),
        "unpriced_models": sorted({c["model"] for c, cost in zip(calls, costs) if cost is None}),
    }


def percentile(values: list[float], pct: int) -> float:
    if len(values) < 2:
        return values[0] if values else 0.0
    return quantiles(values, n=100, method="inclusive")[pct - 1]


def summarize(per_conversation: list[dict]) -> dict:
    """Performance and cost across all conversation runs."""
    turns = [s for m in per_conversation for s in m["turn_seconds"]]
    n_turns = len(turns) or 1
    n_conv = len(per_conversation) or 1
    return {
        "conversations": len(per_conversation),
        "turns": len(turns),
        "turn_latency_p50_s": round(median(turns), 2) if turns else 0,
        "turn_latency_p95_s": round(percentile(turns, 95), 2),
        "turn_latency_max_s": round(max(turns), 2) if turns else 0,
        "conversation_latency_avg_s": round(mean(sum(m["turn_seconds"]) for m in per_conversation), 2)
        if per_conversation else 0,
        "chat_calls_per_turn": round(sum(m["chat_calls"] for m in per_conversation) / n_turns, 2),
        "embedding_calls_total": sum(m["embedding_calls"] for m in per_conversation),
        "tokens_per_conversation_avg": round(
            sum(m["input_tokens"] + m["output_tokens"] for m in per_conversation) / n_conv),
        "cost_per_conversation_avg_usd": round(sum(m["cost_usd"] for m in per_conversation) / n_conv, 6),
        "cost_per_turn_avg_usd": round(sum(m["cost_usd"] for m in per_conversation) / n_turns, 6),
        "cost_total_usd": round(sum(m["cost_usd"] for m in per_conversation), 6),
        "unpriced_models": sorted({x for m in per_conversation for x in m["unpriced_models"]}),
    }
