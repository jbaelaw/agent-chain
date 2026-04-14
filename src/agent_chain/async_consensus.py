"""AsyncConsensusEngine -- async validator voting with concurrent vote collection."""

from __future__ import annotations

import asyncio
from typing import Any

from .agent import AgentResult
from .async_agent import AsyncBaseAgent
from .block import Block, create_block
from .consensus import Vote, VoteDecision, ConsensusRound, ConsensusEngine
from .ledger import ImmutableLedger
from .events import EventBus, EventType


class AsyncConsensusEngine:
    """Async consensus: validators vote concurrently."""

    def __init__(
        self,
        validators: list[AsyncBaseAgent],
        ledger: ImmutableLedger | None = None,
        threshold: float = 0.5,
        event_bus: EventBus | None = None,
    ) -> None:
        if not validators:
            raise ValueError("At least one validator is required")
        if not 0 < threshold <= 1.0:
            raise ValueError("Threshold must be in (0, 1.0]")
        self.validators = list(validators)
        self.ledger = ledger or ImmutableLedger()
        self.threshold = threshold
        self.event_bus = event_bus or EventBus()
        self._rounds: list[ConsensusRound] = []

    @property
    def rounds(self) -> list[ConsensusRound]:
        return list(self._rounds)

    async def propose_and_vote(
        self,
        *,
        proposal_agent_id: str,
        payload: dict[str, Any],
    ) -> ConsensusRound:
        round_ = ConsensusRound(
            proposal_agent_id=proposal_agent_id,
            payload=payload,
        )

        self.event_bus.emit(EventType.CONSENSUS_START, {
            "proposal_agent_id": proposal_agent_id,
            "validator_count": len(self.validators),
        })

        prompt = (
            f"You are a validator. Review this agent output and decide: "
            f"APPROVE, REJECT, or ABSTAIN.\n\n"
            f"Agent: {proposal_agent_id}\n"
            f"Payload: {payload}\n\n"
            f"Reply with exactly one word (APPROVE/REJECT/ABSTAIN) "
            f"followed by a brief reason."
        )

        async def _collect_vote(validator: AsyncBaseAgent) -> Vote:
            result: AgentResult = await validator.execute(prompt)
            decision, reason = ConsensusEngine._parse_vote(result.output)
            vote = Vote(
                validator_id=validator.agent_id,
                decision=decision,
                reason=reason,
            )
            self.event_bus.emit(EventType.CONSENSUS_VOTE, {
                "validator_id": validator.agent_id,
                "decision": decision.value,
            })
            return vote

        votes = await asyncio.gather(*[_collect_vote(v) for v in self.validators])
        round_.votes = list(votes)

        approve_count = sum(1 for v in round_.votes if v.decision == VoteDecision.APPROVE)
        total = len(round_.votes)
        quorum = total > 0 and (approve_count / total) >= self.threshold

        if quorum:
            block = create_block(
                index=self.ledger.height,
                prev_hash=self.ledger.latest.block_hash,
                agent_id=proposal_agent_id,
                payload={
                    "type": "consensus_commit",
                    "original_payload": payload,
                    "votes": [v.to_dict() for v in round_.votes],
                    "approved": True,
                },
            )
            self.ledger.append(block)
            round_.committed = True
            round_.block_hash = block.block_hash
            self.event_bus.emit(EventType.CONSENSUS_COMMIT, {
                "block_hash": block.block_hash,
            })
        else:
            self.event_bus.emit(EventType.CONSENSUS_REJECT, {
                "approve_count": approve_count,
                "total": total,
                "threshold": self.threshold,
            })

        self._rounds.append(round_)
        return round_

    def tally(self, round_: ConsensusRound) -> dict[str, int]:
        counts: dict[str, int] = {"approve": 0, "reject": 0, "abstain": 0}
        for v in round_.votes:
            counts[v.decision.value] += 1
        return counts
