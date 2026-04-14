"""BranchPipeline -- conditional branching and parallel fan-out execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from .agent import BaseAgent, AgentResult
from .async_agent import AsyncBaseAgent
from .block import create_block
from .ledger import ImmutableLedger


RouterFn = Callable[[str, dict[str, Any]], str]


@dataclass
class BranchResult:
    branch_name: str
    result: AgentResult
    block_hash: str


class BranchPipeline:
    """Synchronous conditional branching: a router function selects which
    named branch to execute based on the current input/context."""

    def __init__(
        self,
        router: RouterFn,
        branches: dict[str, list[BaseAgent]],
        ledger: ImmutableLedger | None = None,
    ) -> None:
        if not branches:
            raise ValueError("At least one branch is required")
        self.router = router
        self.branches = dict(branches)
        self.ledger = ledger or ImmutableLedger()
        self._results: list[BranchResult] = []

    @property
    def results(self) -> list[BranchResult]:
        return list(self._results)

    def run(self, input_data: str, context: dict[str, Any] | None = None) -> AgentResult:
        self._results = []
        ctx = dict(context) if context else {}
        branch_name = self.router(input_data, ctx)

        if branch_name not in self.branches:
            raise KeyError(
                f"Router returned unknown branch {branch_name!r}. "
                f"Available: {list(self.branches.keys())}"
            )

        agents = self.branches[branch_name]
        current_input = input_data

        for agent in agents:
            result = agent.execute(current_input, context=ctx)

            block = create_block(
                index=self.ledger.height,
                prev_hash=self.ledger.latest.block_hash,
                agent_id=agent.agent_id,
                payload={
                    "branch": branch_name,
                    "input": current_input[:500],
                    "output": result.output[:500],
                    "agent_role": agent.role,
                },
            )
            self.ledger.append(block)

            self._results.append(BranchResult(
                branch_name=branch_name,
                result=result,
                block_hash=block.block_hash,
            ))

            ctx["prev_agent"] = agent.agent_id
            current_input = result.output

        return self._results[-1].result


class AsyncFanOutPipeline:
    """Run multiple async agent branches in parallel and collect all results."""

    def __init__(
        self,
        branches: dict[str, list[AsyncBaseAgent]],
        ledger: ImmutableLedger | None = None,
    ) -> None:
        if not branches:
            raise ValueError("At least one branch is required")
        self.branches = dict(branches)
        self.ledger = ledger or ImmutableLedger()
        self._results: dict[str, list[BranchResult]] = {}

    @property
    def results(self) -> dict[str, list[BranchResult]]:
        return dict(self._results)

    async def run(self, input_data: str, context: dict[str, Any] | None = None) -> dict[str, AgentResult]:
        self._results = {}

        async def _run_branch(name: str, agents: list[AsyncBaseAgent]) -> tuple[str, AgentResult]:
            ctx = dict(context) if context else {}
            current = input_data
            branch_results: list[BranchResult] = []

            for agent in agents:
                result = await agent.execute(current, context=ctx)
                branch_results.append(BranchResult(
                    branch_name=name,
                    result=result,
                    block_hash="",
                ))
                ctx["prev_agent"] = agent.agent_id
                current = result.output

            self._results[name] = branch_results
            return name, branch_results[-1].result

        tasks = [_run_branch(name, agents) for name, agents in self.branches.items()]
        pairs = await asyncio.gather(*tasks)

        for name, branch_results in self._results.items():
            for br in branch_results:
                block = create_block(
                    index=self.ledger.height,
                    prev_hash=self.ledger.latest.block_hash,
                    agent_id=br.result.agent_id,
                    payload={
                        "branch": name,
                        "output": br.result.output[:500],
                    },
                )
                self.ledger.append(block)
                br.block_hash = block.block_hash

        return {name: result for name, result in pairs}
