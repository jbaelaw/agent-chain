"""agent-chain: multi-agent orchestration with hash-linked block chain audit trail."""

from .block import Block, BlockHeader
from .ledger import ImmutableLedger
from .agent import BaseAgent, LLMAgent, AgentResult
from .pipeline import AgentPipeline
from .consensus import ConsensusEngine, Vote, VoteDecision

__all__ = [
    "Block",
    "BlockHeader",
    "ImmutableLedger",
    "BaseAgent",
    "LLMAgent",
    "AgentResult",
    "AgentPipeline",
    "ConsensusEngine",
    "Vote",
    "VoteDecision",
]
