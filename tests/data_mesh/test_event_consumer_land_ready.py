"""Discriminating test: EventConsumer routes a land_ready event to the land runner.

Consumption invariant (verification-depth.md): a consumer that IGNORED land_ready would
fall through to the generic ACTIONABLE/tally path and return action != "land-review".
This proves the new route is CONSUMED — the verdict reaches a kanban work-item — with an
injected review fn (no live inference, no SurrealDB).
"""

from __future__ import annotations

from cohezion.data_mesh.event_consumer import EventConsumer


class _FakeVerdict:
    def __init__(self, ready: bool):
        self._ready = ready

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def title(self) -> str:
        return f"[land-review:{'READY' if self._ready else 'BLOCKED'}] feat/x -> minor"

    def body(self) -> str:
        return "verdict body"


def _consumer(review_ready: bool, filed: list):
    return EventConsumer(
        "test-consumer",
        sql_fn=lambda q: [],  # no SurrealDB (also satisfies _ensure_claim_field)
        file_work_item_fn=lambda title, desc, domain: filed.append(title) or "work_item:1",
        land_review_fn=lambda repo, branch: _FakeVerdict(review_ready),
    )


def test_land_ready_routes_to_runner_and_files_verdict():
    filed: list[str] = []
    c = _consumer(review_ready=False, filed=filed)
    out = c.handle(
        {"event_type": "land_ready", "payload": '{"repo":"/r","branch":"feat/x"}', "source": "hook"}
    )
    # discriminating: if land_ready were ignored, action would be "tally", not "land-review"
    assert out["action"] == "land-review"
    assert out["ready"] is False
    assert filed and "BLOCKED" in filed[0]  # the verdict reached the kanban work-item


def test_land_ready_ready_verdict_files_ready_item():
    filed: list[str] = []
    c = _consumer(review_ready=True, filed=filed)
    out = c.handle({"event_type": "land_ready", "payload": '{"branch":"feat/x"}', "source": "hook"})
    assert out["action"] == "land-review" and out["ready"] is True
    assert "READY" in filed[0]


def test_non_land_ready_event_still_tallies():
    # a control: an unknown event type must NOT hit the land path (route is specific)
    filed: list[str] = []
    c = _consumer(review_ready=True, filed=filed)
    out = c.handle({"event_type": "some_other_event", "payload": "{}", "source": "x"})
    assert out["action"] == "tally" and not filed
