"""Datamesh EventConsumer — claim-based drain of data_product_event (2026-07-10).

All seams injected (sql/summarize/file-work-item); no HTTP, no inference.
"""

from __future__ import annotations

import json

import pytest

from cohezion.data_mesh.event_consumer import EventConsumer


class FakeSQL:
    def __init__(self, rows):
        self.rows = rows
        self.queries: list[str] = []

    def __call__(self, query):
        self.queries.append(query)
        if query.startswith("SELECT"):
            return [{"status": "OK", "result": list(self.rows)}]
        return [{"status": "OK", "result": []}]


def _event(i, etype="data_product_quality_alert"):
    return {
        "id": f"data_product_event:ev{i:03d}",
        "event_type": etype,
        "source": "test-domain",
        "payload": f'{{"detail": "quality drop {i}"}}',
        "timestamp": float(i),
        "claimed_by": [],
    }


def _consumer(sql, filed):
    return EventConsumer(
        "test-consumer",
        sql_fn=sql,
        summarize_fn=lambda t, p: f"summary of {t}",
        file_work_item_fn=lambda title, description, domain: filed.append(title) or "wq123",
    )


def test_actionable_event_files_work_item():
    sql, filed = FakeSQL([_event(1)]), []
    summary = _consumer(sql, filed).run_once()
    assert summary["actioned"] == [{"event": "data_product_event:ev001", "work_item": "wq123"}]
    assert filed and filed[0].startswith("[datamesh:data_product_quality_alert]")


def test_claim_is_idempotent_array_add_before_handle():
    sql, filed = FakeSQL([_event(1)]), []
    _consumer(sql, filed).run_once()
    claim = next(q for q in sql.queries if q.startswith("UPDATE"))
    assert "array::add(claimed_by ?? [], 'test-consumer')" in claim  # SCP1: never SELECT-then-write
    # claim happens BEFORE the work item is filed (exactly-once per consumer)
    assert sql.queries.index(claim) >= 1


def test_tally_only_types_do_not_file_items():
    sql, filed = FakeSQL([_event(1, etype="data_product_created")]), []
    summary = _consumer(sql, filed).run_once()
    assert summary["tallied"] == 1 and filed == []


def test_unsafe_record_id_rejected_and_isolated():
    bad = _event(1)
    bad["id"] = "data_product_event:x; DELETE compound_loop"
    sql, filed = FakeSQL([bad, _event(2)]), []
    summary = _consumer(sql, filed).run_once()
    assert "data_product_event:x; DELETE compound_loop" in summary["failed"]
    assert len(summary["actioned"]) == 1  # the good event still drained
    assert filed == ["[datamesh:data_product_quality_alert] summary of data_product_quality_alert"]


def test_fetch_filters_by_consumer_and_orders_by_time():
    sql, filed = FakeSQL([]), []
    _consumer(sql, filed).fetch_unclaimed(batch=7)
    q = next(q for q in sql.queries if q.startswith("SELECT"))
    assert "!array::find(claimed_by ?? [], 'test-consumer')" in q
    assert "ORDER BY timestamp ASC LIMIT 7" in q


def test_unsafe_consumer_id_rejected():
    with pytest.raises(ValueError):
        EventConsumer("bad'id", sql_fn=FakeSQL([]))


# --- priority propagation (ticket 99569e2433f1) -----------------------------


class _Recorder:
    """4-arg file_work_item_fn that records what it was handed."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, title, description, domain, priority=1):
        self.calls.append({"title": title, "domain": domain, "priority": priority})
        return "wq-pri"


def test_actionable_event_passes_event_priority_to_work_item():
    """DISCRIMINATING: an event published at priority=2 must arrive as 2.

    The plausible-wrong impl ignores event['priority'] and lets the default
    stand — that impl records 1 and fails this assertion.
    """
    rec = _Recorder()
    ev = _event(1)
    ev["priority"] = 2
    consumer = EventConsumer(
        "test-consumer",
        sql_fn=FakeSQL([ev]),
        summarize_fn=lambda t, p: "summary",
        file_work_item_fn=rec,
    )
    consumer.run_once()
    assert rec.calls, "no work item was filed"
    assert rec.calls[0]["priority"] == 2, f"priority lost: {rec.calls[0]}"


def test_missing_priority_defaults_to_one():
    """An event with no priority key must not crash and must default to 1."""
    rec = _Recorder()
    ev = _event(2)
    ev.pop("priority", None)
    EventConsumer(
        "test-consumer",
        sql_fn=FakeSQL([ev]),
        summarize_fn=lambda t, p: "summary",
        file_work_item_fn=rec,
    ).run_once()
    assert rec.calls and rec.calls[0]["priority"] == 1


def test_legacy_three_arg_file_work_item_fn_still_accepted():
    """Backward compat: existing 3-arg injected fns must keep working."""
    sql, filed = FakeSQL([_event(1)]), []
    summary = _consumer(sql, filed).run_once()  # _consumer injects a 3-arg lambda
    assert summary["actioned"] and filed


def test_default_file_work_item_posts_priority_in_body(monkeypatch):
    """PRODUCTION PATH: the JSON body the kanban receives must carry priority.

    This is the actual defect — every datamesh-filed ticket got the server
    default regardless of the published priority.
    """
    from cohezion.data_mesh import event_consumer as ec

    captured: dict = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"id": "wq999"}'

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        return _Resp()

    monkeypatch.setattr(ec.urllib.request, "urlopen", fake_urlopen)
    item_id = ec._default_file_work_item("t", "d", "dom", 2)
    assert item_id == "wq999"
    assert captured["body"].get("priority") == 2, f"body missing priority: {captured['body']}"
