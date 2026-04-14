"""Regression tests for v0.1 bug fixes."""

import pytest

from agent_chain.agent import LLMAgent
from agent_chain.llm.base import MockLLMBackend
from agent_chain.pipeline import AgentPipeline
from agent_chain.ledger import ImmutableLedger, ChainIntegrityError
from agent_chain.consensus import ConsensusEngine


def test_pipeline_reentrant():
    """run() must reset _steps so consecutive runs don't accumulate."""
    agent = LLMAgent(backend=MockLLMBackend(default="ok"), role="w")
    pipeline = AgentPipeline([agent])

    pipeline.run("first")
    assert len(pipeline.steps) == 1

    pipeline.run("second")
    assert len(pipeline.steps) == 1


def test_ledger_from_json_rejects_empty():
    with pytest.raises(ChainIntegrityError, match="empty chain"):
        ImmutableLedger.from_json("[]")


def test_ledger_from_json_rejects_bad_start_index():
    from agent_chain.block import create_block, Block
    import json

    block = create_block(index=5, prev_hash="0" * 64, agent_id="x", payload={})
    data = json.dumps([block.to_dict()])
    with pytest.raises(ChainIntegrityError, match="index 0"):
        ImmutableLedger.from_json(data)


def test_vote_parsing_keyword_anywhere():
    """_parse_vote should find APPROVE/REJECT anywhere in output, not just at start."""
    decision, reason = ConsensusEngine._parse_vote("I think we should APPROVE this result")
    from agent_chain.consensus import VoteDecision
    assert decision == VoteDecision.APPROVE

    decision, reason = ConsensusEngine._parse_vote("After review, REJECT")
    assert decision == VoteDecision.REJECT

    decision, reason = ConsensusEngine._parse_vote("no clear keyword here")
    assert decision == VoteDecision.ABSTAIN
