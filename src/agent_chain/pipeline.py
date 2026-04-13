"""AgentPipeline — sequential agent chaining with automatic block recording."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent import BaseAgent, AgentResult
from .block import create_block
from .ledger import ImmutableLedger


@dataclass
class PipelineStep:
    index: int
    agent: BaseAgent
    result: AgentResult
    block_hash: str


class AgentPipeline:
    """Runs agents in sequence; each result becomes the next agent's input
    and is recorded as a block in the ledger."""

    def __init__(
        self,
        agents: list[BaseAgent],
        ledger: ImmutableLedger | None = None,
    ) -> None:
        if not agents:
            raise ValueError("Pipeline requires at least one agent")
        self.agents = list(agents)
        self.ledger = ledger or ImmutableLedger()
        self._steps: list[PipelineStep] = []

    @property
    def steps(self) -> list[PipelineStep]:
        return list(self._steps)

    def run(self, initial_input: str, context: dict[str, Any] | None = None) -> AgentResult:
        current_input = initial_input
        ctx = dict(context) if context else {}

        for i, agent in enumerate(self.agents):
            result = agent.execute(current_input, context=ctx)

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

            self._steps.append(PipelineStep(
                index=i,
                agent=agent,
                result=result,
                block_hash=block.block_hash,
            ))

            ctx["prev_agent"] = agent.agent_id
            ctx["prev_output"] = result.output[:200]
            current_input = result.output

        return self._steps[-1].result

    def summary(self) -> list[dict[str, Any]]:
        return [
            {
                "step": s.index,
                "agent_id": s.agent.agent_id,
                "role": s.agent.role,
                "output_preview": s.result.output[:120],
                "block_hash": s.block_hash,
            }
            for s in self._steps
        ]
