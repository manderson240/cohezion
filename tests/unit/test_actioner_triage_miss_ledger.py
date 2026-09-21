"""Unmatched items must not be re-triaged every run (2026-09-21).

Live evidence (daemon health report 2026-09-21): 48 actioner runs in one day each
reported ``processed`` 2,770-2,773 and actioned nothing in 45 of them. ``eligible_items``
returns every APPLY item in reviewed/approved, and an item no triage rule matches was
never recorded anywhere, so every 5-minute run re-examined the same ~2,771 dead items.

The fix records misses in a ledger keyed by a fingerprint of the triage rules. A miss is
skipped only while the rules are unchanged; changing the rules re-examines everything.
Items are never deleted and their queue status is never touched.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from cohezion.actioner import engine
from cohezion.actioner.engine import WorkQueueAPI, run_batch


class FakeAPI(WorkQueueAPI):
    def __init__(self, items):
        super().__init__("http://fake")
        self._items = items
        self.patched: list[tuple[str, str]] = []

    def eligible_items(self):
        return list(self._items)

    def mark_actioned(self, item_id, route):
        self.patched.append((item_id, route))
        return {"id": item_id, "status": "actioned"}


class FakeExecutor:
    def execute_task(self, task_description, skill_name, operation_type, execute_fn):
        output, metrics = execute_fn("guidance")
        return SimpleNamespace(success=True, output=output, metrics=metrics)


def _chat(prompt):
    return json.dumps({"proposal": "wire X into Y", "falsifiable_step": "measure Z drops"})


def _dead(i):
    return {
        "id": f"dead{i:04d}",
        "title": "quantum entanglement in photonic lattices",
        "domain": "quant-ph",
        "relevance": "APPLY",
        "status": "reviewed",
    }


def _run(api, tmp_path, **kw):
    return run_batch(
        FakeExecutor(),
        api,
        _chat,
        proposals_path=tmp_path / "p.jsonl",
        vault_dir=tmp_path / "v",
        **kw,
    )


def test_second_run_over_the_same_queue_examines_nothing(tmp_path):
    api = FakeAPI([_dead(i) for i in range(2771)])
    first = _run(api, tmp_path)
    assert first["processed"] == 2771
    assert len(first["skipped_no_match"]) == 2771

    second = _run(api, tmp_path)
    assert second["processed"] == 0
    assert second["skipped_no_match"] == []
    assert second["skipped_known_miss"] == 2771


def test_new_items_are_still_triaged_after_misses_are_recorded(tmp_path):
    items = [_dead(i) for i in range(5)]
    api = FakeAPI(items)
    _run(api, tmp_path)
    items.append({"id": "live001", "title": "prompt caching for agent tools", "relevance": "APPLY"})
    second = _run(api, tmp_path)
    assert second["processed"] == 1
    assert [a["id"] for a in second["actioned"]] == ["live001"]


def test_changing_the_rules_re_examines_recorded_misses(tmp_path, monkeypatch):
    api = FakeAPI([_dead(i) for i in range(3)])
    _run(api, tmp_path)
    assert _run(api, tmp_path)["processed"] == 0

    monkeypatch.setattr(engine, "_TRIAGE_LOGIC_REVISION", engine._TRIAGE_LOGIC_REVISION + 1)
    third = _run(api, tmp_path)
    assert third["processed"] == 3


def test_dry_run_records_no_misses(tmp_path):
    api = FakeAPI([_dead(i) for i in range(3)])
    _run(api, tmp_path, dry_run=True)
    assert _run(api, tmp_path)["processed"] == 3


def test_recording_a_miss_never_mutates_the_queue(tmp_path):
    api = FakeAPI([_dead(i) for i in range(3)])
    _run(api, tmp_path)
    _run(api, tmp_path)
    assert api.patched == []


def test_batch_cap_does_not_evict_misses_it_never_reached(tmp_path):
    """The batch cap stops the walk early; misses past the stop point must survive."""
    live = [
        {"id": f"live{i:03d}", "title": "prompt caching for agent tools", "relevance": "APPLY"}
        for i in range(3)
    ]
    dead_head, dead_tail = [_dead(i) for i in range(2)], [_dead(i) for i in range(2, 6)]
    api = FakeAPI(dead_head + dead_tail)
    _run(api, tmp_path)  # records all 6 misses

    api._items = dead_head + live + dead_tail  # cap=3 stops before dead_tail
    capped = _run(api, tmp_path, batch_size=3)
    assert capped["skipped_known_miss"] == 2

    api._items = dead_head + dead_tail
    assert _run(api, tmp_path)["processed"] == 0
