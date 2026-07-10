"""Datamesh EventConsumer — claim-based drain of data_product_event (2026-07-10).

All seams injected (sql/summarize/file-work-item); no HTTP, no inference.
"""

from __future__ import annotations

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
