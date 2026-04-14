"""Async agent variants: AsyncBaseAgent, AsyncLLMAgent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .agent import AgentResult
from .llm.async_base import AsyncLLMBackend
from .utils import new_id, utc_now


class AsyncBaseAgent(ABC):
    """Abstract base for async agents."""

    def __init__(self, *, agent_id: str | None = None, role: str = "agent") -> None:
        self.agent_id = agent_id or f"{role}_{new_id()}"
        self.role = role

    @abstractmethod
    async def execute(self, input_data: str, context: dict[str, Any] | None = None) -> AgentResult:
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id!r} role={self.role!r}>"


class AsyncLLMAgent(AsyncBaseAgent):
    """Async agent powered by an AsyncLLMBackend."""

    def __init__(
        self,
        *,
        backend: AsyncLLMBackend,
        system_prompt: str = "",
        agent_id: str | None = None,
        role: str = "llm_agent",
    ) -> None:
        super().__init__(agent_id=agent_id, role=role)
        self.backend = backend
        self.system_prompt = system_prompt

    async def execute(self, input_data: str, context: dict[str, Any] | None = None) -> AgentResult:
        prompt = input_data
        if context:
            ctx_summary = "\n".join(f"- {k}: {v}" for k, v in context.items())
            prompt = f"Context:\n{ctx_summary}\n\nTask:\n{input_data}"

        output = await self.backend.agenerate(prompt=prompt, system_prompt=self.system_prompt)
        return AgentResult(
            agent_id=self.agent_id,
            output=output,
            metadata={
                "backend": self.backend.name,
                "role": self.role,
            },
        )
