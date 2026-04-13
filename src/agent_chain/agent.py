"""BaseAgent, LLMAgent, and AgentResult definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any

from .llm.base import LLMBackend
from .utils import new_id, utc_now


@dataclass
class AgentResult:
    agent_id: str
    output: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseAgent(ABC):
    """Abstract base for all agents in the chain."""

    def __init__(self, *, agent_id: str | None = None, role: str = "agent") -> None:
        self.agent_id = agent_id or f"{role}_{new_id()}"
        self.role = role

    @abstractmethod
    def execute(self, input_data: str, context: dict[str, Any] | None = None) -> AgentResult:
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id!r} role={self.role!r}>"


class LLMAgent(BaseAgent):
    """Agent powered by an LLM backend."""

    def __init__(
        self,
        *,
        backend: LLMBackend,
        system_prompt: str = "",
        agent_id: str | None = None,
        role: str = "llm_agent",
    ) -> None:
        super().__init__(agent_id=agent_id, role=role)
        self.backend = backend
        self.system_prompt = system_prompt

    def execute(self, input_data: str, context: dict[str, Any] | None = None) -> AgentResult:
        prompt = input_data
        if context:
            ctx_summary = "\n".join(f"- {k}: {v}" for k, v in context.items())
            prompt = f"Context:\n{ctx_summary}\n\nTask:\n{input_data}"

        output = self.backend.generate(prompt=prompt, system_prompt=self.system_prompt)
        return AgentResult(
            agent_id=self.agent_id,
            output=output,
            metadata={
                "backend": self.backend.name,
                "role": self.role,
                "system_prompt_length": len(self.system_prompt),
            },
        )
