"""Tests for FunctionAgent and AsyncFunctionAgent."""

import asyncio

import pytest

from agent_chain.function_agent import FunctionAgent, AsyncFunctionAgent
from agent_chain.pipeline import AgentPipeline


def _upper(input_data: str, context=None) -> str:
    return input_data.upper()


def _prefix(input_data: str, context=None) -> str:
    tag = context.get("tag", "RESULT") if context else "RESULT"
    return f"[{tag}] {input_data}"


def test_function_agent_basic():
    agent = FunctionAgent(_upper, role="upper")
    result = agent.execute("hello")
    assert result.output == "HELLO"
    assert result.metadata["function"] == "_upper"


def test_function_agent_with_context():
    agent = FunctionAgent(_prefix, role="prefix")
    result = agent.execute("data", context={"tag": "INFO"})
    assert result.output == "[INFO] data"


def test_function_agent_in_pipeline():
    a1 = FunctionAgent(_upper, role="upper")
    a2 = FunctionAgent(_prefix, role="prefix")
    pipeline = AgentPipeline([a1, a2])
    result = pipeline.run("hello")
    assert result.output == "[RESULT] HELLO"


def test_async_function_agent_sync_fn():
    agent = AsyncFunctionAgent(_upper, role="upper")
    result = asyncio.run(agent.execute("hello"))
    assert result.output == "HELLO"


def test_async_function_agent_async_fn():
    async def _async_upper(input_data: str, context=None) -> str:
        return input_data.upper()

    agent = AsyncFunctionAgent(_async_upper, role="upper")
    result = asyncio.run(agent.execute("test"))
    assert result.output == "TEST"
