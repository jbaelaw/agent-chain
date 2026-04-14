"""Tests for AsyncPipeline and AsyncConsensusEngine."""

import asyncio

import pytest

from agent_chain.async_agent import AsyncLLMAgent
from agent_chain.llm.async_base import AsyncMockLLMBackend
from agent_chain.async_pipeline import AsyncPipeline
from agent_chain.async_consensus import AsyncConsensusEngine
from agent_chain.ledger import ImmutableLedger
from agent_chain.events import EventBus, EventType


def _run(coro):
    return asyncio.run(coro)


def _make_agent(response: str, role: str = "worker") -> AsyncLLMAgent:
    return AsyncLLMAgent(backend=AsyncMockLLMBackend(default=response), role=role)


def test_async_pipeline_single():
    agent = _make_agent("done")
    pipeline = AsyncPipeline([agent])
    result = _run(pipeline.run("start"))
    assert result.output == "done"
    assert pipeline.ledger.height == 2


def test_async_pipeline_multi():
    agents = [_make_agent(f"step_{i}") for i in range(3)]
    pipeline = AsyncPipeline(agents)
    result = _run(pipeline.run("go"))
    assert result.output == "step_2"
    assert pipeline.ledger.height == 4


def test_async_pipeline_events():
    bus = EventBus()
    events = []
    bus.on_all(lambda et, d: events.append(et))

    agent = _make_agent("ok")
    pipeline = AsyncPipeline([agent], event_bus=bus)
    _run(pipeline.run("x"))

    assert EventType.PIPELINE_START in events
    assert EventType.AGENT_START in events
    assert EventType.AGENT_END in events
    assert EventType.BLOCK_CREATED in events
    assert EventType.PIPELINE_END in events


def test_async_pipeline_reentrant():
    agent = _make_agent("out")
    pipeline = AsyncPipeline([agent])
    _run(pipeline.run("first"))
    assert len(pipeline.steps) == 1
    _run(pipeline.run("second"))
    assert len(pipeline.steps) == 1


def test_async_consensus_all_approve():
    validators = [_make_agent("APPROVE ok") for _ in range(3)]
    engine = AsyncConsensusEngine(validators, threshold=0.5)
    round_ = _run(engine.propose_and_vote(proposal_agent_id="p", payload={"x": 1}))
    assert round_.committed is True
    tally = engine.tally(round_)
    assert tally["approve"] == 3


def test_async_consensus_reject():
    validators = [_make_agent("REJECT no") for _ in range(3)]
    engine = AsyncConsensusEngine(validators, threshold=0.5)
    round_ = _run(engine.propose_and_vote(proposal_agent_id="p", payload={}))
    assert round_.committed is False


def test_async_consensus_concurrent_voting():
    validators = [
        _make_agent("APPROVE yes"),
        _make_agent("REJECT no"),
        _make_agent("APPROVE fine"),
    ]
    engine = AsyncConsensusEngine(validators, threshold=0.5)
    round_ = _run(engine.propose_and_vote(proposal_agent_id="p", payload={"v": 1}))
    assert round_.committed is True
    tally = engine.tally(round_)
    assert tally["approve"] == 2
    assert tally["reject"] == 1


def test_async_pipeline_empty_raises():
    with pytest.raises(ValueError):
        AsyncPipeline([])


def test_async_consensus_empty_raises():
    with pytest.raises(ValueError):
        AsyncConsensusEngine([])
