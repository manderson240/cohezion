"""Throughput assertion: the feeder must SAY when it found work and fed none.

THE FAILURE THIS ENCODES (2026-07-26, measured): the compound daemon idled 91 consecutive rounds
reporting "No pending tasks" while `cohezion-compound-feeder` ran on schedule, exited 0, and
returned `{"fed": 0, "skipped": 31, "candidates": 31}` every time. Root cause: 71 work-queue items
were written as `type=task, status=pending`, while the feeder queries
`type=improvement` + `status=approved|actioned` — producer and consumer disagreed about the
contract, every POST returned 201, and nothing was ever reachable.

The diagnosis was in the feeder's own return value the whole time and had no consumer. That is a
SIGNAL WITH NO CONSUMER — the mirror image of a consumer with no producer.

DISCRIMINATING DESIGN: `fed == 0` alone is NOT the alarm. A settled queue legitimately feeds
nothing, and an implementation that flagged bare `fed == 0` would cry wolf on every quiet run —
which is how an alarm gets ignored and the next 91-round outage goes unnoticed. The pathological
state is specifically *candidates were found AND all of them were skipped*.
"""

from __future__ import annotations

import logging

from cohezion.compound.compound_feeder import feed_compound_tasks


def _item(i: str) -> dict:
    return {
        "id": i,
        "type": "improvement",
        "relevance": "APPLY",
        "title": f"item {i}",
        "priority": 1,
    }


def _feed(tmp_path, items, limit=5):
    return feed_compound_tasks(
        limit=limit,
        fetch=lambda: items,
        tasks_file=tmp_path / "compound_tasks.json",
        lock_file=tmp_path / "compound_tasks.lock",
    )


def test_starved_when_candidates_found_but_none_fed(tmp_path, caplog):
    """THE 91-ROUND CASE: every candidate already present, so all are skipped."""
    items = [_item("a"), _item("b")]
    first = _feed(tmp_path, items)
    assert first["fed"] == 2 and first["starved"] is False

    with caplog.at_level(logging.WARNING):
        second = _feed(tmp_path, items)  # same items -> all deduped

    assert second["candidates"] == 2
    assert second["fed"] == 0
    assert second["skipped"] == 2
    assert second["starved"] is True, "found work, fed none — this must be visible"
    assert any("STARVED" in r.message for r in caplog.records), (
        "the starved state must be LOGGED, not only returned — the 91-round outage was invisible "
        "precisely because the signal had no consumer"
    )


def test_not_starved_when_queue_is_simply_empty(tmp_path, caplog):
    """DISCRIMINATING: an impl flagging bare `fed == 0` fails here.

    No candidates at all is a quiet, healthy run. Alarming on it trains the operator to ignore the
    alarm, which is how the real outage stays invisible.
    """
    with caplog.at_level(logging.WARNING):
        r = _feed(tmp_path, [])

    assert r["candidates"] == 0
    assert r["fed"] == 0
    assert r["starved"] is False, "empty queue is normal, not pathological"
    assert not any("STARVED" in rec.message for rec in caplog.records)


def test_not_starved_on_partial_progress(tmp_path):
    """Some fed, some skipped -> healthy. Progress is being made."""
    first = _feed(tmp_path, [_item("a")])
    assert first["fed"] == 1

    r = _feed(tmp_path, [_item("a"), _item("b")])  # 'a' dedupes, 'b' is new
    assert r["candidates"] == 2
    assert r["fed"] == 1
    assert r["skipped"] == 1
    assert r["starved"] is False
