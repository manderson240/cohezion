"""Wire-format tests for make_bus_publisher.

WHY THESE EXIST: DaemonHealth was mutation-tested 9/9, but make_bus_publisher -- the part
that actually writes to the bus -- had NO coverage at all. It shipped emitting
event_type="CUSTOM" while its own commit message claimed "daemon_heartbeat", so ~170
heartbeats from a real run sat on the bus indistinguishable from every other CUSTOM event.
Nothing failed. A high mutation score on the wrong surface is not coverage.

Every field asserted here has a specific past failure behind it:
  event_type  must be selectable, or the health signal cannot be queried
  timestamp   must be a FLOAT; consumers compare numerically and an ISO string yields an
              HTTP 200 that no consumer will ever match
  payload     must be a JSON STRING, matching the shape existing consumers replay
  priority    must be an int; SurrealDB rejects NONE with a statement-level ERR inside an
              HTTP 200 response
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from cohezion.data_mesh.daemon_health import DaemonHealth, make_bus_publisher


class _FakeResponse:
    status = 200

    def read(self) -> bytes:
        return b"{}"

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _capture(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the publisher against a stubbed transport and return the decoded wire body."""
    sent: dict[str, Any] = {}

    def fake_urlopen(req: Any, *_a: object, **_k: object) -> _FakeResponse:
        sent.update(json.loads(req.data.decode()))
        return _FakeResponse()

    with patch("urllib.request.urlopen", fake_urlopen):
        make_bus_publisher()(payload)
    return sent


def test_event_type_is_daemon_heartbeat_not_custom() -> None:
    """The regression. 'CUSTOM' is storable and was accepted -- it was just unselectable."""
    body = _capture({"daemon": "d", "priority": 1})
    assert body["event_type"] == "daemon_heartbeat"
    assert body["event_type"] != "CUSTOM"


def test_timestamp_is_float_not_string() -> None:
    body = _capture({"daemon": "d", "priority": 1})
    assert isinstance(body["timestamp"], float)


def test_payload_is_a_json_string_not_a_nested_object() -> None:
    body = _capture({"daemon": "d", "priority": 1, "failure_rate": 0.5})
    assert isinstance(body["payload"], str)
    assert json.loads(body["payload"])["failure_rate"] == 0.5


def test_priority_is_int_even_when_payload_omits_it() -> None:
    """SurrealDB rejects a NONE priority with a statement-level ERR inside an HTTP 200."""
    body = _capture({"daemon": "d"})
    assert isinstance(body["priority"], int)


def test_source_carries_the_daemon_name() -> None:
    """A heartbeat that cannot be attributed to a daemon cannot be acted on."""
    assert _capture({"daemon": "research_daemon"})["source"] == "daemon:research_daemon"


def test_unnamed_daemon_does_not_crash_the_publisher() -> None:
    assert _capture({})["source"] == "daemon:unknown"


def test_heartbeat_flows_end_to_end_through_daemon_health() -> None:
    """Discriminating: the constants could be right while DaemonHealth never calls them."""
    sent: dict[str, Any] = {}

    def fake_urlopen(req: Any, *_a: object, **_k: object) -> _FakeResponse:
        sent.update(json.loads(req.data.decode()))
        return _FakeResponse()

    health = DaemonHealth("probe_daemon", publish_fn=make_bus_publisher())
    health.record_failure("boom")
    with patch("urllib.request.urlopen", fake_urlopen):
        health.heartbeat()

    assert sent["event_type"] == "daemon_heartbeat"
    assert sent["source"] == "daemon:probe_daemon"
    inner = json.loads(sent["payload"])
    # Counters are nested; failures live under "counters", not at the top level.
    assert inner["counters"]["failures"] >= 1, (
        "a heartbeat that omits failures reports liveness, not health"
    )
    assert inner["failure_rate"] > 0.0


def test_payload_kind_and_event_type_agree() -> None:
    """The payload always self-described as a heartbeat via "kind" while the QUERYABLE
    column said CUSTOM. That split is exactly what made the bug hard to see: the data was
    self-consistent to anyone already reading it, and invisible to anyone selecting it."""
    body = _capture({"daemon": "d", "kind": "daemon_heartbeat"})
    assert json.loads(body["payload"])["kind"] == body["event_type"]
