"""Tests for AgentPipeline."""

import pytest

from agent_chain.agent import LLMAgent
from agent_chain.llm.base import MockLLMBackend
from agent_chain.pipeline import AgentPipeline
from agent_chain.ledger import ImmutableLedger


def _make_agent(response: str, role: str = "worker") -> LLMAgent:
    backend = MockLLMBackend(default=response)
    return LLMAgent(backend=backend, role=role)


def test_single_agent_pipeline():
    agent = _make_agent("result_A")
    pipeline = AgentPipeline([agent])
    result = pipeline.run("start")
    assert result.output == "result_A"
    assert len(pipeline.steps) == 1
    assert pipeline.ledger.height == 2  # genesis + 1 block


def test_multi_agent_pipeline():
    agents = [_make_agent(f"step_{i}", role=f"role_{i}") for i in range(3)]
    pipeline = AgentPipeline(agents)
    result = pipeline.run("begin")

    assert result.output == "step_2"
    assert len(pipeline.steps) == 3
    assert pipeline.ledger.height == 4  # genesis + 3


def test_pipeline_chaining_passes_output():
    backend = MockLLMBackend(
        responses={"begin": "phase_1_done", "phase_1_done": "phase_2_done"},
        default="fallback",
    )
    a1 = LLMAgent(backend=backend, role="first")
    a2 = LLMAgent(backend=backend, role="second")
    pipeline = AgentPipeline([a1, a2])
    result = pipeline.run("begin")
    assert result.output == "phase_2_done"


def test_pipeline_records_blocks_in_ledger():
    ledger = ImmutableLedger()
    agents = [_make_agent("out") for _ in range(2)]
    pipeline = AgentPipeline(agents, ledger=ledger)
    pipeline.run("go")
    assert ledger.height == 3
    assert ledger.validate_chain() is True


def test_pipeline_summary():
    agents = [_make_agent("res", role="analyst")]
    pipeline = AgentPipeline(agents)
    pipeline.run("data")
    summary = pipeline.summary()
    assert len(summary) == 1
    assert summary[0]["role"] == "analyst"
    assert "block_hash" in summary[0]


def test_empty_pipeline_raises():
    with pytest.raises(ValueError, match="at least one agent"):
        AgentPipeline([])
