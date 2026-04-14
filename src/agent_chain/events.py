"""EventBus -- publish/subscribe hooks for agent lifecycle events."""

from __future__ import annotations

import enum
from collections import defaultdict
from typing import Any, Callable


class EventType(enum.Enum):
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    BLOCK_CREATED = "block_created"
    CONSENSUS_START = "consensus_start"
    CONSENSUS_VOTE = "consensus_vote"
    CONSENSUS_COMMIT = "consensus_commit"
    CONSENSUS_REJECT = "consensus_reject"
    PIPELINE_START = "pipeline_start"
    PIPELINE_STEP = "pipeline_step"
    PIPELINE_END = "pipeline_end"


Listener = Callable[[EventType, dict[str, Any]], None]


class EventBus:
    """Global or per-pipeline event dispatcher.

    Listeners are plain callables: ``def on_event(event_type, data): ...``
    """

    def __init__(self) -> None:
        self._listeners: dict[EventType, list[Listener]] = defaultdict(list)
        self._global_listeners: list[Listener] = []

    def on(self, event_type: EventType, listener: Listener) -> None:
        self._listeners[event_type].append(listener)

    def on_all(self, listener: Listener) -> None:
        self._global_listeners.append(listener)

    def emit(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        payload = data or {}
        for fn in self._listeners.get(event_type, []):
            fn(event_type, payload)
        for fn in self._global_listeners:
            fn(event_type, payload)

    def clear(self) -> None:
        self._listeners.clear()
        self._global_listeners.clear()
