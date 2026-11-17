from contextlib import contextmanager


def setup_tracing() -> None:
    """Called once at startup. TODO(observability owner): register Arize tracing here."""


@contextmanager
def trace_step(name: str, **attributes):
    """Wrap each workflow step (pre-check, intent gate, branch). Currently a no-op.

    CONTRACT: keep this signature. The observability owner can make it open an Arize span.
    """
    yield
