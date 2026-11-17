import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Unit tests use the keyword intent gate and never call the LLM."""
    monkeypatch.setenv("SUPPORT_AGENT_OFFLINE", "1")
