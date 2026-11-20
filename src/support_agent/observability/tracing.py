"""Arize tracing. Every customer message is one trace ("turn"), grouped into a session per conversation.

LLM calls are captured by the OpenAI instrumentor; workflow steps and tool calls use trace_step().
Without ARIZE_API_KEY and ARIZE_SPACE_ID (or without the packages) everything here is a no-op.
"""
import os
from contextlib import contextmanager, nullcontext

from .. import config  # noqa: F401  loads .env before the Arize keys are read

_tracer = None
_provider = None


def setup_tracing(project_name: str | None = None) -> None:
    """Called once at startup. Install the packages with: pip install -e ".[tracing]"."""
    global _tracer, _provider
    if _tracer is not None:
        return
    api_key, space_id = os.getenv("ARIZE_API_KEY"), os.getenv("ARIZE_SPACE_ID")
    if not api_key or not space_id:
        print("Arize tracing off: set ARIZE_API_KEY and ARIZE_SPACE_ID to turn it on.")
        return
    try:
        from arize.otel import register
        from openinference.instrumentation.openai import OpenAIInstrumentor
    except ImportError:
        print('Arize tracing off: run pip install -e ".[tracing]".')
        return
    endpoint = os.getenv("ARIZE_COLLECTOR_ENDPOINT")
    provider = register(
        space_id=space_id,
        api_key=api_key,
        project_name=project_name or os.getenv("ARIZE_PROJECT_NAME", "retail-support-v1"),
        verbose=False,
        # Not program-wide: FastAPI (under the Gradio UI) traces every web request when a global provider
        # exists, which floods Arize with UNKNOWN "GET /gradio_api/..." spans. Our spans and the OpenAI
        # calls get this provider explicitly instead.
        set_global_tracer_provider=False,
        **({"endpoint": endpoint} if endpoint else {}),
    )
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    _provider, _tracer = provider, provider.get_tracer("support_agent")
    print(f"Arize tracing on: project {project_name or os.getenv('ARIZE_PROJECT_NAME', 'retail-support-v1')}")


def flush(timeout_ms: int = 30000) -> bool:
    """Send any buffered spans now (scripts that exit quickly call this)."""
    return _provider.force_flush(timeout_ms) if _provider is not None else True


def _value(value):
    return value if isinstance(value, (str, bool, int, float)) else str(value)


@contextmanager
def trace_step(name: str, kind: str = "CHAIN", **attributes):
    """Wrap a workflow step (pre-check, intent gate, branch) or a tool call (kind="TOOL").

    CONTRACT: keep this signature. Yields the span (or None when tracing is off) so callers can
    add attributes with set_attributes() once they know the result.
    """
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as span:
        span.set_attribute("openinference.span.kind", kind)
        set_attributes(span, **attributes)
        yield span


def set_attributes(span, **attributes) -> None:
    if span is None:
        return
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key.replace("__", "."), _value(value))


def conversation(session_id: str, customer_id: str | None):
    """Tags every span inside (including the LLM calls) with the session and user, for Arize's Sessions view."""
    if _tracer is None:
        return nullcontext()
    from openinference.instrumentation import using_attributes

    return using_attributes(session_id=session_id, user_id=customer_id or "anonymous")
