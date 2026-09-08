"""Durability of the work-queue store: atomic write, cross-process lock, corrupt quarantine.

All three defects share ONE shape — *a write path whose failure produces a plausible-looking
success* — which is why they are fixed and tested together rather than as three tickets. The
same shape appeared twice more the same day (the actioner overwriting `notes`, and
`event_bridge` swallowing SurrealDB write failures at DEBUG).

Every test here is written to FAIL against the pre-fix implementation. A test that passes both
ways would certify nothing; see `test_work_queue_notes_preservation.py` for the sibling case.
"""

from __future__ import annotations

import importlib
import json
import multiprocessing
import time

import pytest


# NOT `from cohezion.api import work_queue_router` — the package __init__ re-exports the
# APIRouter OBJECT under that name, which shadows the module.
wq = importlib.import_module("cohezion.api.work_queue_router")


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path / "work-queue.json"
    path.write_text(json.dumps({"items": [], "version": 1}))
    monkeypatch.setattr(wq, "WORK_QUEUE_FILE", path)
    monkeypatch.setattr(wq, "_persist", lambda item: None)
    return path


class TestAtomicWrite:
    def test_failed_write_leaves_the_original_file_parseable(self, store, monkeypatch):
        """DISCRIMINATING: pre-fix `write_text` truncates first, so a mid-write failure
        left invalid JSON — which `_load` then read as an EMPTY QUEUE."""
        wq.create_item(wq.WorkItemCreate(type="research", title="precious", notes="A" * 5000))
        original = store.read_text()

        real_write = wq.Path.write_text

        def explode(self, *a, **kw):
            if self.suffix.startswith(".tmp"):
                raise OSError("disk full mid-write")
            return real_write(self, *a, **kw)

        # NOT monkeypatch.undo() — that reverts EVERY patch from this fixture, including
        # the `store` fixture's WORK_QUEUE_FILE redirect, which sent a previous version of
        # this test at the LIVE 6k-card production queue. Restore only what we replaced.
        wq.Path.write_text = explode
        try:
            with pytest.raises(OSError):
                wq.create_item(wq.WorkItemCreate(type="research", title="doomed"))
        finally:
            wq.Path.write_text = real_write

        assert store.read_text() == original, "a failed write corrupted the live file"
        assert len(wq._load()["items"]) == 1  # still readable, nothing lost

    def test_no_tmp_files_left_behind(self, store):
        wq.create_item(wq.WorkItemCreate(type="research", title="t"))
        assert not list(store.parent.glob("*.tmp-*")), "temp file leaked"


class TestCorruptQuarantine:
    def test_corrupt_file_is_copied_aside_before_load_returns_empty(self, store):
        """DISCRIMINATING: pre-fix, `except Exception: pass` discarded the bytes entirely
        and the next _save made the emptiness permanent. Fail-open is PRESERVED — the
        assertion is that the data survives somewhere, not that _load raises."""
        wq.create_item(wq.WorkItemCreate(type="research", title="irreplaceable", notes="B" * 3000))
        # A real crash mid-write leaves a PARTIAL copy of the data, so truncate rather than
        # replace — an earlier version of this test overwrote the file wholesale and then
        # asserted the quarantine held content the file no longer contained.
        good = store.read_text()
        store.write_text(good[: len(good) // 2])  # half-written file

        result = wq._load()
        assert result == {"items": [], "version": 1}, "fail-open semantics must be preserved"

        quarantined = list(store.parent.glob("*.corrupt-*.json"))
        assert quarantined, "corrupt file was discarded instead of quarantined"
        salvaged = quarantined[0].read_text()
        assert salvaged == good[: len(good) // 2], "quarantine did not preserve the bytes verbatim"
        assert "irreplaceable" in salvaged, "the partial data was not recoverable"

    def test_missing_file_is_not_quarantined(self, store):
        """A absent file is a legitimately empty queue, not corruption — do not spam
        quarantine copies for the normal first-run case."""
        store.unlink()
        assert wq._load() == {"items": [], "version": 1}
        assert not list(store.parent.glob("*.corrupt-*.json"))


def _hammer(path_str: str, tag: str, n: int) -> None:
    """Child process: create n cards through the real locked API."""
    import importlib
    from pathlib import Path

    mod = importlib.import_module("cohezion.api.work_queue_router")
    mod.WORK_QUEUE_FILE = Path(path_str)
    mod._persist = lambda item: None
    for i in range(n):
        mod.create_item(mod.WorkItemCreate(type="research", title=f"{tag}-{i}"))
        time.sleep(0.001)


class TestCrossProcessLock:
    def test_concurrent_writers_do_not_lose_each_others_cards(self, store):
        """This test as written is NOT discriminating; the real evidence is below.

        On a near-empty fixture each read-modify-write is microseconds, so three processes
        never overlap. Mutation-verified 2026-08-10: replacing `_queue_lock` with a no-op
        left this at 36/36 — the MUTANT SURVIVED. Keep this test as a smoke check that
        concurrent writes do not crash, and do not cite it as proof the lock works.

        THE ACTUAL MUTATION RESULT, on a 1,200-card seeded store with an adequate timeout
        (scratchpad/mutate3.py), 3 processes x 8 writes:

            WITH lock    : 18/24 new cards, all 1,200 seed cards INTACT
            WITHOUT lock : -1187/24 — the file ended with THIRTEEN items total

        Without the lock a stale writer wrote back a copy missing ~1,187 of the 1,200
        pre-existing cards. That is not "lost updates", it is near-total destruction of
        the store, and it is what the production file (~7 MB / 6k cards, 3+ concurrent
        writers) is exposed to today.

        TWO CONCLUSIONS, and the second matters more:
        1. The lock PREVENTS THE CATASTROPHIC CASE. Proven, large effect.
        2. The lock IS NOT SUFFICIENT. 6 of 24 writes were still lost with it held, so
           `_queue_lock` does not fully serialise the read-modify-write. Root cause not
           yet identified — do NOT record this defect as fixed.

        The architectural reading: a single ~7 MB JSON document rewritten in full on every
        single-field mutation is the wrong structure for 3+ concurrent writers, and adding
        locking to it is treating a symptom. Per the strategy-pivot rule, the next step is
        a different data structure (per-item files, or an actual database — SurrealDB is
        already a dependency), not a third attempt at tuning the lock.
        """
        per_proc = 12
        ctx = multiprocessing.get_context("fork")
        procs = [
            ctx.Process(target=_hammer, args=(str(store), tag, per_proc))
            for tag in ("alpha", "beta", "gamma")
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=60)

        items = wq._load()["items"]
        assert len(items) == per_proc * 3, (
            f"lost updates: expected {per_proc * 3} cards, found {len(items)}"
        )
        for tag in ("alpha", "beta", "gamma"):
            assert sum(1 for i in items if str(i["title"]).startswith(tag)) == per_proc

    def test_lock_is_fail_open_when_flock_unavailable(self, store, monkeypatch):
        """A queue that refuses writes is worse than one that races — the lock must
        degrade, not block. Without this, a locking bug becomes a total outage."""
        monkeypatch.setattr(
            wq.fcntl, "flock", lambda *a, **kw: (_ for _ in ()).throw(OSError("no flock here"))
        )
        item = wq.create_item(wq.WorkItemCreate(type="research", title="still works"))
        assert item["title"] == "still works"
        assert len(wq._load()["items"]) == 1
