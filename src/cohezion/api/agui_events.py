"""
AG-UI Event Types for the Cohezion Genesis Engine.

Implements the AG-UI (Agent-User Interaction) protocol event format
for typed SSE streaming. Maps Cohezion's physics simulation events
to the AG-UI specification.

Reference: https://docs.ag-ui.com/concepts/events
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AGUIEventType(str, Enum):
    """AG-UI protocol event types."""

    # Lifecycle
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"

    # Text messages (narration)
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"

    # Tool calls (phase transitions)
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"

    # State management (universe ticks)
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"

    # Custom (Cohezion-specific)
    CUSTOM = "CUSTOM"


@dataclass
class AGUIEvent:
    """Base AG-UI event following the protocol specification."""

    type: AGUIEventType
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_sse(self) -> str:
        """Format as SSE (Server-Sent Events) data line."""
        return f"data: {self.to_json()}\n\n"

    def to_json(self) -> str:
        """Serialize to JSON string."""
        d = {"type": self.type.value, "timestamp": self.timestamp}
        d.update(self._extra_fields())
        return json.dumps(d)

    def _extra_fields(self) -> dict[str, Any]:
        return {}


@dataclass
class RunStartedEvent(AGUIEvent):
    """Emitted when the Genesis cosmogony begins."""

    type: AGUIEventType = AGUIEventType.RUN_STARTED
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def _extra_fields(self) -> dict[str, Any]:
        return {"threadId": self.thread_id, "runId": self.run_id}


@dataclass
class RunFinishedEvent(AGUIEvent):
    """Emitted when the cosmogony animation completes."""

    type: AGUIEventType = AGUIEventType.RUN_FINISHED
    thread_id: str = ""
    run_id: str = ""
    result: dict[str, Any] = field(default_factory=dict)

    def _extra_fields(self) -> dict[str, Any]:
        return {"threadId": self.thread_id, "runId": self.run_id, "result": self.result}


@dataclass
class TextMessageEvent(AGUIEvent):
    """Narration text streaming event."""

    type: AGUIEventType = AGUIEventType.TEXT_MESSAGE_START
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "assistant"
    delta: str = ""

    def _extra_fields(self) -> dict[str, Any]:
        d: dict[str, Any] = {"messageId": self.message_id, "role": self.role}
        if self.delta:
            d["delta"] = self.delta
        return d


@dataclass
class ToolCallEvent(AGUIEvent):
    """Phase transition event (mapped to AG-UI tool calls)."""

    type: AGUIEventType = AGUIEventType.TOOL_CALL_START
    tool_call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_call_name: str = ""
    content: Any = None

    def _extra_fields(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "toolCallId": self.tool_call_id,
            "toolCallName": self.tool_call_name,
        }
        if self.content is not None:
            d["content"] = self.content
        return d


@dataclass
class StateSnapshotEvent(AGUIEvent):
    """Full universe state snapshot."""

    type: AGUIEventType = AGUIEventType.STATE_SNAPSHOT
    snapshot: dict[str, Any] = field(default_factory=dict)

    def _extra_fields(self) -> dict[str, Any]:
        return {"snapshot": self.snapshot}


@dataclass
class StateDeltaEvent(AGUIEvent):
    """Incremental universe state update (RFC 6902 JSON Patch)."""

    type: AGUIEventType = AGUIEventType.STATE_DELTA
    delta: list[dict[str, Any]] = field(default_factory=list)

    def _extra_fields(self) -> dict[str, Any]:
        return {"delta": self.delta}


@dataclass
class CustomEvent(AGUIEvent):
    """Cohezion-specific event (e.g., HIHO coherence update)."""

    type: AGUIEventType = AGUIEventType.CUSTOM
    name: str = ""
    value: Any = None

    def _extra_fields(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}


# --- Convenience constructors for Genesis events ---


def narration_event(text: str, stage: str) -> list[AGUIEvent]:
    """Create a TEXT_MESSAGE sequence for a narration stage."""
    msg_id = str(uuid.uuid4())
    return [
        TextMessageEvent(type=AGUIEventType.TEXT_MESSAGE_START, message_id=msg_id, role="assistant"),
        TextMessageEvent(type=AGUIEventType.TEXT_MESSAGE_CONTENT, message_id=msg_id, delta=text),
        TextMessageEvent(type=AGUIEventType.TEXT_MESSAGE_END, message_id=msg_id),
    ]


def phase_transition_event(from_sym: str, to_sym: str, temperature: float) -> list[AGUIEvent]:
    """Create a TOOL_CALL sequence for a symmetry breaking transition."""
    call_id = str(uuid.uuid4())
    return [
        ToolCallEvent(
            type=AGUIEventType.TOOL_CALL_START,
            tool_call_id=call_id,
            tool_call_name="symmetry_breaking",
        ),
        ToolCallEvent(
            type=AGUIEventType.TOOL_CALL_RESULT,
            tool_call_id=call_id,
            tool_call_name="symmetry_breaking",
            content={
                "from": from_sym,
                "to": to_sym,
                "temperature": temperature,
                "stage": f"{from_sym} → {to_sym}",
            },
        ),
    ]


def universe_tick_event(
    temperature: float,
    symmetry: str,
    coherence: float,
    order_parameter: float,
    landau_free_energy: float,
) -> StateDeltaEvent:
    """Create a STATE_DELTA for a universe tick update."""
    return StateDeltaEvent(
        delta=[
            {"op": "replace", "path": "/temperature", "value": temperature},
            {"op": "replace", "path": "/symmetry", "value": symmetry},
            {"op": "replace", "path": "/coherence", "value": coherence},
            {"op": "replace", "path": "/orderParameter", "value": order_parameter},
            {"op": "replace", "path": "/landauFreeEnergy", "value": landau_free_energy},
        ]
    )
