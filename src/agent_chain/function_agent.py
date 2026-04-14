"""FunctionAgent -- wrap any callable as a BaseAgent."""

from __future__ import annotations

from typing import Any, Callable

from .agent import BaseAgent, AgentResult
from .async_agent import AsyncBaseAgent
from .utils import new_id


class FunctionAgent(BaseAgent):
    """Wraps a plain ``Callable[[str, dict | None], str]`` as a synchronous agent."""

    def __init__(
        self,
        fn: Callable[..., str],
        *,
        agent_id: str | None = None,
        role: str = "function_agent",
    ) -> None:
        super().__init__(agent_id=agent_id, role=role)
        self._fn = fn

    def execute(self, input_data: str, context: dict[str, Any] | None = None) -> AgentResult:
        output = self._fn(input_data, context)
        return AgentResult(
            agent_id=self.agent_id,
            output=output,
            metadata={"role": self.role, "function": self._fn.__name__},
        )


class AsyncFunctionAgent(AsyncBaseAgent):
    """Wraps an async callable as an async agent.

    Also accepts synchronous callables (they run without await).
    """

    def __init__(
        self,
        fn: Callable[..., Any],
        *,
        agent_id: str | None = None,
        role: str = "function_agent",
    ) -> None:
        super().__init__(agent_id=agent_id, role=role)
        self._fn = fn

    async def execute(self, input_data: str, context: dict[str, Any] | None = None) -> AgentResult:
        import asyncio
        result = self._fn(input_data, context)
        if asyncio.iscoroutine(result):
            result = await result
        return AgentResult(
            agent_id=self.agent_id,
            output=result,
            metadata={"role": self.role, "function": self._fn.__name__},
        )
