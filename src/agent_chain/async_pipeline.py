"""AsyncPipeline -- async sequential and parallel agent execution with ledger recording."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .agent import AgentResult
from .async_agent import AsyncBaseAgent
from .block import create_block
from .ledger import ImmutableLedger
from .events import EventBus, EventType


@dataclass
class AsyncPipelineStep:
    index: int
    agent_id: str
    role: str
    result: AgentResult
    block_hash: str


class AsyncPipeline:
    """Async sequential pipeline: agents run one after another."""

    def __init__(
        self,
        agents: list[AsyncBaseAgent],
        ledger: ImmutableLedger | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        if not agents:
            raise ValueError("Pipeline requires at least one agent")
        self.agents = list(agents)
        self.ledger = ledger or ImmutableLedger()
        self.event_bus = event_bus or EventBus()
        self._steps: list[AsyncPipelineStep] = []

    @property
    def steps(self) -> list[AsyncPipelineStep]:
        return list(self._steps)

    async def run(self, initial_input: str, context: dict[str, Any] | None = None) -> AgentResult:
        self._steps = []
        current_input = initial_input
        ctx = dict(context) if context else {}

        self.event_bus.emit(EventType.PIPELINE_START, {
            "agent_count": len(self.agents),
            "input_preview": initial_input[:200],
        })

        for i, agent in enumerate(self.agents):
            self.event_bus.emit(EventType.AGENT_START, {
                "agent_id": agent.agent_id, "step": i,
            })

            result = await agent.execute(current_input, context=ctx)

            self.event_bus.emit(EventType.AGENT_END, {
                "agent_id": agent.agent_id, "step": i,
                "output_preview": result.output[:200],
            })

            block = create_block(
                index=self.ledger.height,
                prev_hash=self.ledger.latest.block_hash,
                agent_id=agent.agent_id,
                payload={
                    "step": i,
                    "input": current_input[:500],
                    "output": result.output[:500],
                    "agent_role": agent.role,
                    "metadata": result.metadata,
                },
            )
            self.ledger.append(block)

            self.event_bus.emit(EventType.BLOCK_CREATED, {
                "block_index": block.header.index,
                "block_hash": block.block_hash,
            })

            self._steps.append(AsyncPipelineStep(
                index=i,
                agent_id=agent.agent_id,
                role=agent.role,
                result=result,
                block_hash=block.block_hash,
            ))

            ctx["prev_agent"] = agent.agent_id
            ctx["prev_output"] = result.output[:200]
            current_input = result.output

        self.event_bus.emit(EventType.PIPELINE_END, {
            "total_steps": len(self._steps),
        })
        return self._steps[-1].result
