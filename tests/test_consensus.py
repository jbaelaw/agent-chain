"""Tests for ConsensusEngine."""

import pytest

from agent_chain.agent import LLMAgent
from agent_chain.llm.base import MockLLMBackend
from agent_chain.consensus import ConsensusEngine, VoteDecision
from agent_chain.ledger import ImmutableLedger


def _validator(response: str) -> LLMAgent:
    backend = MockLLMBackend(default=response)
    return LLMAgent(backend=backend, role="validator")


def test_consensus_all_approve():
    validators = [_validator("APPROVE looks good") for _ in range(3)]
    engine = ConsensusEngine(validators, threshold=0.5)
    round_ = engine.propose_and_vote(
        proposal_agent_id="proposer_1",
        payload={"answer": "42"},
    )
    assert round_.committed is True
    assert round_.block_hash is not None
    tally = engine.tally(round_)
    assert tally["approve"] == 3


def test_consensus_all_reject():
    validators = [_validator("REJECT bad output") for _ in range(3)]
    engine = ConsensusEngine(validators, threshold=0.5)
    round_ = engine.propose_and_vote(
        proposal_agent_id="p1",
        payload={"answer": "wrong"},
    )
    assert round_.committed is False
    assert round_.block_hash is None
    tally = engine.tally(round_)
    assert tally["reject"] == 3


def test_consensus_mixed_votes_above_threshold():
    validators = [
        _validator("APPROVE ok"),
        _validator("APPROVE fine"),
        _validator("REJECT no"),
    ]
    engine = ConsensusEngine(validators, threshold=0.5)
    round_ = engine.propose_and_vote(proposal_agent_id="p", payload={"x": 1})
    assert round_.committed is True
    tally = engine.tally(round_)
    assert tally["approve"] == 2
    assert tally["reject"] == 1


def test_consensus_mixed_votes_below_threshold():
    validators = [
        _validator("APPROVE ok"),
        _validator("REJECT no"),
        _validator("REJECT nah"),
    ]
    engine = ConsensusEngine(validators, threshold=0.67)
    round_ = engine.propose_and_vote(proposal_agent_id="p", payload={"x": 1})
    assert round_.committed is False


def test_consensus_commits_to_ledger():
    ledger = ImmutableLedger()
    validators = [_validator("APPROVE") for _ in range(2)]
    engine = ConsensusEngine(validators, ledger=ledger, threshold=0.5)
    engine.propose_and_vote(proposal_agent_id="p", payload={"data": "test"})
    assert ledger.height == 2
    assert ledger.validate_chain() is True


def test_consensus_unparseable_vote_becomes_abstain():
    validators = [_validator("I'm not sure what to say")]
    engine = ConsensusEngine(validators, threshold=0.5)
    round_ = engine.propose_and_vote(proposal_agent_id="p", payload={})
    tally = engine.tally(round_)
    assert tally["abstain"] == 1
    assert round_.committed is False


def test_consensus_no_validators_raises():
    with pytest.raises(ValueError, match="(?i)at least one validator"):
        ConsensusEngine([], threshold=0.5)


def test_consensus_invalid_threshold_raises():
    validators = [_validator("APPROVE")]
    with pytest.raises(ValueError, match="Threshold"):
        ConsensusEngine(validators, threshold=0.0)
    with pytest.raises(ValueError, match="Threshold"):
        ConsensusEngine(validators, threshold=1.5)


def test_multiple_rounds():
    validators = [_validator("APPROVE ok") for _ in range(2)]
    engine = ConsensusEngine(validators, threshold=0.5)
    for i in range(3):
        engine.propose_and_vote(proposal_agent_id=f"p{i}", payload={"round": i})
    assert len(engine.rounds) == 3
    assert engine.ledger.height == 4  # genesis + 3 commits
