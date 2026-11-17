from typing import Protocol

from . import config


class LLM(Protocol):
    def complete(self, messages: list[dict]) -> str: ...


class OpenAIChat:
    """Thin wrapper so the rest of the code never imports the OpenAI SDK directly."""

    def __init__(self, model: str | None = None):
        from openai import OpenAI  # imported here so tests run without the package

        self._client = OpenAI()
        self._model = model or config.MODEL

    def complete(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(model=self._model, messages=messages)
        return response.choices[0].message.content or ""
