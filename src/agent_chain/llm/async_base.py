"""Async LLM backend abstract base and async mock."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .base import LLMBackend


class AsyncLLMBackend(ABC):
    """Async counterpart of LLMBackend."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def agenerate(self, prompt: str, system_prompt: str = "") -> str:
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"


class AsyncMockLLMBackend(AsyncLLMBackend):
    """Async deterministic mock for testing."""

    def __init__(self, *, responses: dict[str, str] | None = None, default: str = "mock response") -> None:
        self._responses = responses or {}
        self._default = default
        self._call_log: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return "async_mock"

    @property
    def call_log(self) -> list[dict[str, str]]:
        return list(self._call_log)

    async def agenerate(self, prompt: str, system_prompt: str = "") -> str:
        self._call_log.append({"prompt": prompt, "system_prompt": system_prompt})
        for keyword, response in self._responses.items():
            if keyword.lower() in prompt.lower():
                return response
        return self._default


class SyncToAsyncAdapter(AsyncLLMBackend):
    """Wraps a synchronous LLMBackend for use in async pipelines."""

    def __init__(self, backend: LLMBackend) -> None:
        self._backend = backend

    @property
    def name(self) -> str:
        return self._backend.name

    async def agenerate(self, prompt: str, system_prompt: str = "") -> str:
        return self._backend.generate(prompt=prompt, system_prompt=system_prompt)
