"""LLM backend abstract base and mock implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """Abstract interface for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"


class MockLLMBackend(LLMBackend):
    """Deterministic mock for testing and demos."""

    def __init__(self, *, responses: dict[str, str] | None = None, default: str = "mock response") -> None:
        self._responses = responses or {}
        self._default = default
        self._call_log: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return "mock"

    @property
    def call_log(self) -> list[dict[str, str]]:
        return list(self._call_log)

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        self._call_log.append({"prompt": prompt, "system_prompt": system_prompt})
        for keyword, response in self._responses.items():
            if keyword.lower() in prompt.lower():
                return response
        return self._default
