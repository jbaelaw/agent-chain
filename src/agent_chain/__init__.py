"""agent-chain: multi-agent orchestration with hash-linked block chain audit trail."""

__version__ = "0.2.0"

from .block import Block, BlockHeader
from .ledger import ImmutableLedger, ChainIntegrityError
from .agent import BaseAgent, LLMAgent, AgentResult
from .async_agent import AsyncBaseAgent, AsyncLLMAgent
from .pipeline import AgentPipeline
from .async_pipeline import AsyncPipeline
from .consensus import ConsensusEngine, Vote, VoteDecision, ConsensusRound
from .async_consensus import AsyncConsensusEngine
from .function_agent import FunctionAgent, AsyncFunctionAgent
from .branch_pipeline import BranchPipeline, AsyncFanOutPipeline
from .merkle import merkle_root, chain_merkle_root
from .events import EventBus, EventType

__all__ = [
    "Block",
    "BlockHeader",
    "ImmutableLedger",
    "ChainIntegrityError",
    "BaseAgent",
    "LLMAgent",
    "AgentResult",
    "AsyncBaseAgent",
    "AsyncLLMAgent",
    "AgentPipeline",
    "AsyncPipeline",
    "ConsensusEngine",
    "AsyncConsensusEngine",
    "ConsensusRound",
    "Vote",
    "VoteDecision",
    "FunctionAgent",
    "AsyncFunctionAgent",
    "BranchPipeline",
    "AsyncFanOutPipeline",
    "merkle_root",
    "chain_merkle_root",
    "EventBus",
    "EventType",
]
