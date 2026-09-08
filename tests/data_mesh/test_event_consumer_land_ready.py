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


def test_run_once_counts_land_review_as_actioned(monkeypatch):
    """T2 discriminating (accounting): a land-review outcome is ACTIONED, not tallied.

    First live smoke (2026-08-14): run_once matched only action == "work-item", so a
    successful land review — which files a work item under action == "land-review" —
    reported as "tallied": the loop looked like a no-op while doing its job.
    """
    filed: list[str] = []
    c = _consumer(review_ready=False, filed=filed)
    monkeypatch.setattr(
        c,
        "fetch_unclaimed",
        lambda batch: [
            {
                "id": "data_product_event:t1",
                "event_type": "land_ready",
                "payload": '{"branch":"feat/x"}',
                "source": "scanner",
            }
        ],
    )
    monkeypatch.setattr(c, "claim", lambda rid: None)
    summary = c.run_once(batch=1)
    assert summary["actioned"], "land-review must be counted as actioned"
    assert summary["tallied"] == 0


class TestPriorityThreading:
    """Train-3 port (2026-08-31): event `priority` must reach the filed work item.

    Producer evidence: data_mesh/event_bridge.py defines, writes, and SELECTs a
    `priority` int column on data_product_event — a live producer whose value the
    consumer previously discarded when filing kanban work items.
    """

    def test_priority_reaches_four_arg_filer(self):
        """DISCRIMINATING: priority=3 on the event lands priority=3 in the filer call.

        A consumer that drops the field (the pre-port behavior) passes priority=1
        (the coercion default) or raises TypeError on the 4-arg filer.
        """
        seen: list[tuple] = []
        c = EventConsumer(
            "test-consumer",
            sql_fn=lambda q: [],
            file_work_item_fn=lambda title, desc, domain, priority: (
                seen.append((title, priority)) or "work_item:p"
            ),
        )
        out = c.handle(
            {
                "event_type": "data_product_quality_alert",
                "payload": '{"why":"drift"}',
                "source": "scanner",
                "priority": 3,
            }
        )
        assert out["action"] == "work-item"
        assert seen and seen[0][1] == 3, f"priority must thread through, got {seen}"

    def test_legacy_three_arg_filer_does_not_raise(self):
        """A legacy 3-arg injected filer must keep working (signature-aware dispatch)."""
        filed: list[str] = []
        c = EventConsumer(
            "test-consumer",
            sql_fn=lambda q: [],
            file_work_item_fn=lambda title, desc, domain: filed.append(title) or "work_item:1",
        )
        out = c.handle(
            {
                "event_type": "data_product_quality_alert",
                "payload": "{}",
                "source": "scanner",
                "priority": 5,
            }
        )
        assert out["action"] == "work-item"
        assert filed, "legacy filer must still be invoked"

    def test_garbage_priority_coerces_to_default(self):
        """A free-form/corrupt priority value must never drop the item."""
        seen: list[tuple] = []
        c = EventConsumer(
            "test-consumer",
            sql_fn=lambda q: [],
            file_work_item_fn=lambda title, desc, domain, priority: (
                seen.append((title, priority)) or "work_item:g"
            ),
        )
        out = c.handle(
            {
                "event_type": "domain_health_degraded",
                "payload": "{}",
                "source": "scanner",
                "priority": "urgent-ish",
            }
        )
        assert out["action"] == "work-item"
        assert seen and seen[0][1] == 1, "bad priority must coerce to default, not drop"
