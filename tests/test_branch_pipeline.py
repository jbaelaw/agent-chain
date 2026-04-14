"""Tests for BranchPipeline and AsyncFanOutPipeline."""

import asyncio

import pytest

from agent_chain.agent import LLMAgent
from agent_chain.async_agent import AsyncLLMAgent
from agent_chain.llm.base import MockLLMBackend
from agent_chain.llm.async_base import AsyncMockLLMBackend
from agent_chain.branch_pipeline import BranchPipeline, AsyncFanOutPipeline
from agent_chain.ledger import ImmutableLedger


def _run(coro):
    return asyncio.run(coro)


def _agent(response: str, role: str = "w") -> LLMAgent:
    return LLMAgent(backend=MockLLMBackend(default=response), role=role)


def _async_agent(response: str, role: str = "w") -> AsyncLLMAgent:
    return AsyncLLMAgent(backend=AsyncMockLLMBackend(default=response), role=role)


def test_branch_pipeline_routes_correctly():
    def router(input_data, ctx):
        return "fast" if "quick" in input_data.lower() else "thorough"

    branches = {
        "fast": [_agent("fast_result", role="fast")],
        "thorough": [_agent("thorough_step1"), _agent("thorough_step2", role="thorough")],
    }

    pipeline = BranchPipeline(router, branches)
    result = pipeline.run("quick analysis needed")
    assert result.output == "fast_result"
    assert len(pipeline.results) == 1
    assert pipeline.results[0].branch_name == "fast"


def test_branch_pipeline_thorough():
    def router(input_data, ctx):
        return "fast" if "quick" in input_data.lower() else "thorough"

    branches = {
        "fast": [_agent("fast_result")],
        "thorough": [_agent("step1"), _agent("step2")],
    }

    pipeline = BranchPipeline(router, branches)
    result = pipeline.run("deep investigation")
    assert result.output == "step2"
    assert len(pipeline.results) == 2


def test_branch_pipeline_unknown_branch():
    pipeline = BranchPipeline(
        router=lambda i, c: "nonexistent",
        branches={"a": [_agent("x")]},
    )
    with pytest.raises(KeyError, match="nonexistent"):
        pipeline.run("test")


def test_branch_pipeline_empty_branches_raises():
    with pytest.raises(ValueError):
        BranchPipeline(router=lambda i, c: "a", branches={})


def test_branch_pipeline_ledger():
    ledger = ImmutableLedger()
    branches = {"main": [_agent("out1"), _agent("out2")]}
    pipeline = BranchPipeline(lambda i, c: "main", branches, ledger=ledger)
    pipeline.run("input")
    assert ledger.height == 3
    assert ledger.validate_chain() is True


def test_async_fan_out():
    branches = {
        "research": [_async_agent("research_done", role="researcher")],
        "review": [_async_agent("review_done", role="reviewer")],
    }
    pipeline = AsyncFanOutPipeline(branches)
    results = _run(pipeline.run("analyze data"))

    assert "research" in results
    assert "review" in results
    assert results["research"].output == "research_done"
    assert results["review"].output == "review_done"
    assert pipeline.ledger.height >= 3


def test_async_fan_out_ledger():
    ledger = ImmutableLedger()
    branches = {
        "a": [_async_agent("a_out")],
        "b": [_async_agent("b_out")],
    }
    pipeline = AsyncFanOutPipeline(branches, ledger=ledger)
    _run(pipeline.run("go"))
    assert ledger.height == 3
    assert ledger.validate_chain() is True


def test_async_fan_out_empty_raises():
    with pytest.raises(ValueError):
        AsyncFanOutPipeline(branches={})
