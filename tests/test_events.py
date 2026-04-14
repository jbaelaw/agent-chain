"""Tests for EventBus."""

from agent_chain.events import EventBus, EventType


def test_event_bus_emit_and_listen():
    bus = EventBus()
    received = []
    bus.on(EventType.AGENT_START, lambda et, d: received.append((et, d)))
    bus.emit(EventType.AGENT_START, {"agent_id": "a1"})
    assert len(received) == 1
    assert received[0][0] == EventType.AGENT_START
    assert received[0][1]["agent_id"] == "a1"


def test_event_bus_on_all():
    bus = EventBus()
    received = []
    bus.on_all(lambda et, d: received.append(et))
    bus.emit(EventType.AGENT_START)
    bus.emit(EventType.BLOCK_CREATED)
    assert received == [EventType.AGENT_START, EventType.BLOCK_CREATED]


def test_event_bus_no_listener():
    bus = EventBus()
    bus.emit(EventType.PIPELINE_END, {"x": 1})


def test_event_bus_multiple_listeners():
    bus = EventBus()
    counts = {"a": 0, "b": 0}
    bus.on(EventType.BLOCK_CREATED, lambda et, d: counts.__setitem__("a", counts["a"] + 1))
    bus.on(EventType.BLOCK_CREATED, lambda et, d: counts.__setitem__("b", counts["b"] + 1))
    bus.emit(EventType.BLOCK_CREATED)
    assert counts == {"a": 1, "b": 1}


def test_event_bus_clear():
    bus = EventBus()
    received = []
    bus.on(EventType.AGENT_END, lambda et, d: received.append(1))
    bus.on_all(lambda et, d: received.append(2))
    bus.clear()
    bus.emit(EventType.AGENT_END)
    assert received == []


def test_pipeline_emits_events():
    from agent_chain.agent import LLMAgent
    from agent_chain.llm.base import MockLLMBackend
    from agent_chain.pipeline import AgentPipeline

    bus = EventBus()
    events = []
    bus.on_all(lambda et, d: events.append(et))

    agent = LLMAgent(backend=MockLLMBackend(default="ok"), role="w")
    pipeline = AgentPipeline([agent], event_bus=bus)
    pipeline.run("go")

    assert EventType.PIPELINE_START in events
    assert EventType.AGENT_START in events
    assert EventType.AGENT_END in events
    assert EventType.BLOCK_CREATED in events
    assert EventType.PIPELINE_END in events


def test_consensus_emits_events():
    from agent_chain.agent import LLMAgent
    from agent_chain.llm.base import MockLLMBackend
    from agent_chain.consensus import ConsensusEngine

    bus = EventBus()
    events = []
    bus.on_all(lambda et, d: events.append(et))

    validators = [LLMAgent(backend=MockLLMBackend(default="APPROVE ok"), role="v") for _ in range(2)]
    engine = ConsensusEngine(validators, threshold=0.5, event_bus=bus)
    engine.propose_and_vote(proposal_agent_id="p", payload={"x": 1})

    assert EventType.CONSENSUS_START in events
    assert EventType.CONSENSUS_VOTE in events
    assert EventType.CONSENSUS_COMMIT in events
