"""ConsensusEngine — validator-based voting and verification for blocks."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from .agent import BaseAgent, AgentResult
from .block import Block, create_block
from .ledger import ImmutableLedger
from .utils import utc_now


class VoteDecision(enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    validator_id: str
    decision: VoteDecision
    reason: str
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class ConsensusRound:
    """Tracks a single consensus round for a proposed payload."""
    proposal_agent_id: str
    payload: dict[str, Any]
    votes: list[Vote] = field(default_factory=list)
    committed: bool = False
    block_hash: str | None = None


class ConsensusEngine:
    """Manages proposal -> vote -> commit cycle with configurable threshold."""

    def __init__(
        self,
        validators: list[BaseAgent],
        ledger: ImmutableLedger | None = None,
        threshold: float = 0.5,
    ) -> None:
        if not validators:
            raise ValueError("At least one validator is required")
        if not 0 < threshold <= 1.0:
            raise ValueError("Threshold must be in (0, 1.0]")
        self.validators = list(validators)
        self.ledger = ledger or ImmutableLedger()
        self.threshold = threshold
        self._rounds: list[ConsensusRound] = []

    @property
    def rounds(self) -> list[ConsensusRound]:
        return list(self._rounds)

    def propose_and_vote(
        self,
        *,
        proposal_agent_id: str,
        payload: dict[str, Any],
    ) -> ConsensusRound:
        """Submit a payload for validation; all validators vote."""
        round_ = ConsensusRound(
            proposal_agent_id=proposal_agent_id,
            payload=payload,
        )

        prompt = (
            f"You are a validator. Review this agent output and decide: "
            f"APPROVE, REJECT, or ABSTAIN.\n\n"
            f"Agent: {proposal_agent_id}\n"
            f"Payload: {payload}\n\n"
            f"Reply with exactly one word (APPROVE/REJECT/ABSTAIN) "
            f"followed by a brief reason."
        )

        for validator in self.validators:
            result: AgentResult = validator.execute(prompt)
            decision, reason = self._parse_vote(result.output)
            vote = Vote(
                validator_id=validator.agent_id,
                decision=decision,
                reason=reason,
            )
            round_.votes.append(vote)

        if self._quorum_reached(round_):
            block = self._commit(round_)
            round_.committed = True
            round_.block_hash = block.block_hash

        self._rounds.append(round_)
        return round_

    def _parse_vote(self, output: str) -> tuple[VoteDecision, str]:
        text = output.strip().upper()
        if text.startswith("APPROVE"):
            return VoteDecision.APPROVE, output.strip()
        elif text.startswith("REJECT"):
            return VoteDecision.REJECT, output.strip()
        elif text.startswith("ABSTAIN"):
            return VoteDecision.ABSTAIN, output.strip()
        # Default: treat unrecognised output as abstain
        return VoteDecision.ABSTAIN, f"(unparseable) {output.strip()}"

    def _quorum_reached(self, round_: ConsensusRound) -> bool:
        approve_count = sum(1 for v in round_.votes if v.decision == VoteDecision.APPROVE)
        total = len(round_.votes)
        return total > 0 and (approve_count / total) >= self.threshold

    def _commit(self, round_: ConsensusRound) -> Block:
        block = create_block(
            index=self.ledger.height,
            prev_hash=self.ledger.latest.block_hash,
            agent_id=round_.proposal_agent_id,
            payload={
                "type": "consensus_commit",
                "original_payload": round_.payload,
                "votes": [v.to_dict() for v in round_.votes],
                "approved": True,
            },
        )
        self.ledger.append(block)
        return block

    def tally(self, round_: ConsensusRound) -> dict[str, int]:
        counts: dict[str, int] = {"approve": 0, "reject": 0, "abstain": 0}
        for v in round_.votes:
            counts[v.decision.value] += 1
        return counts
