"""work-queue read-modify-write must be atomic across concurrent writers
(adversarial review, 2026-09-01/03).

WORK_QUEUE_FILE (~/.cohezion/work-queue.json) is written by TWO independent
processes on the identical path: this API server, and cohezion-labs/
research_daemon.py's local-fallback path when the API is unreachable. Both did
unlocked whole-file read-modify-write (`q = _load(); ...; _save(q)`) with zero
coordination — a write from either side could silently clobber the other's, and
research_daemon.py's own consume_queue() held a stale in-memory snapshot across
a multi-minute LLM-analysis loop before overwriting the whole file with it.

Fix: every read-modify-write endpoint now goes through cohezion.concurrency.
file_lock.ConfigManager (already used elsewhere, its own suite green), the SAME
flock-on-the-file-itself primitive research_daemon.py's `_atomic_queue_update`
also uses — so the two processes genuinely coordinate on one lock instead of
hoping not to collide.

The concurrency tests below are NOT mocked: they use real threads and a
deliberately widened race window inside the actual lock, so a regression back
to unlocked `_load()`/`_save()` loses an item RELIABLY, not just under timing
luck.

IMPORTANT (verified empirically while writing this suite, 2026-09-03): calling
the endpoints through `TestClient.post()`/`.patch()` from multiple threads did
NOT reproduce the race even against the OLD unlocked implementation — Starlette's
TestClient appears to serialize requests enough that true interleaving never
happens at that layer, which would have made a TestClient-based concurrency
test pass regardless of whether the fix was present (a green test proving
nothing). Confirmed by direct measurement: calling the router's endpoint
FUNCTIONS directly from real Python threads (bypassing TestClient for the
timing-sensitive part) DOES reproduce data loss against the old code and DOES
pass against the new locked code. The tests below call `wqr.create_item(...)`/
`wqr.patch_item(...)` directly for exactly this reason.
"""

from __future__ import annotations

import importlib
import inspect
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


wqr = importlib.import_module("cohezion.api.work_queue_router")


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Isolated queue file so tests never touch ~/.cohezion/work-queue.json."""
    monkeypatch.setattr(wqr, "WORK_QUEUE_FILE", tmp_path / "work-queue.json")
    monkeypatch.setattr(wqr, "_persist", lambda _item: None)
    app = FastAPI()
    app.include_router(wqr.router)
    return TestClient(app)


# ── Wiring (structural): the endpoints actually call the locked primitive ─────
def test_create_item_uses_atomic_update_not_load_then_save():
    """DISCRIMINATING: a version reverted to `q = _load(); q['items'].append(item);
    _save(q)` fails this — it never calls _atomic_update at all."""
    src = inspect.getsource(wqr.create_item)
    assert "_atomic_update" in src, "create_item no longer routes through the lock"
    assert "_save(" not in src, "create_item still writes via the unlocked _save()"


def test_patch_item_uses_atomic_update_not_load_then_save():
    src = inspect.getsource(wqr.patch_item)
    assert "_atomic_update" in src, "patch_item no longer routes through the lock"
    assert "_save(" not in src, "patch_item still writes via the unlocked _save()"


def test_delete_item_uses_atomic_update_not_load_then_save():
    src = inspect.getsource(wqr.delete_item)
    assert "_atomic_update" in src, "delete_item no longer routes through the lock"
    assert "_save(" not in src, "delete_item still writes via the unlocked _save()"


# ── Behavioral (real concurrency, no mocks, no HTTP layer) ─────────────────────
# Calls the endpoint FUNCTIONS directly from real threads rather than through
# TestClient.post()/.patch() -- see the module docstring for why: TestClient
# was measured to serialize requests enough that the race never manifested
# through it, even against the deliberately-reverted old unlocked code.
def test_concurrent_creates_do_not_lose_an_item(client, monkeypatch):
    """REAL threads, REAL fcntl.flock contention, calling create_item directly.

    Wraps the router's real `_atomic_update` with a small sleep held WHILE the
    lock is held, deterministically widening the race window so three
    concurrent creates are forced to interleave if locking is broken — this is
    not a timing-luck test. DISCRIMINATING: reverting create_item to unlocked
    `_load()`/`_save()` loses at least one of the three items here, reliably
    (measured directly while writing this test: {'C'} survived out of
    {'A','B','C'} against the old code, under this exact harness).
    """
    real_atomic_update = wqr._atomic_update

    def slow_atomic_update(mutate_fn):
        def _slow_mutate(q):
            result = mutate_fn(q)
            time.sleep(0.05)  # held INSIDE the lock — this is the widened race window
            return result

        return real_atomic_update(_slow_mutate)

    monkeypatch.setattr(wqr, "_atomic_update", slow_atomic_update)

    def create(title: str) -> None:
        wqr.create_item(wqr.WorkItemCreate(title=title))

    threads = [threading.Thread(target=create, args=(t,)) for t in ("A", "B", "C")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    q = wqr._load()
    titles = {i["title"] for i in q.get("items", [])}
    assert titles == {"A", "B", "C"}, f"lost an item under concurrent writes: {titles}"


def test_concurrent_patch_and_create_do_not_lose_either(client, monkeypatch):
    """A patch to an existing item and a brand-new create, racing on the same
    file, must both survive — proves the lock covers heterogeneous
    read-modify-write operations, not just same-endpoint repeats."""
    existing = wqr.create_item(wqr.WorkItemCreate(title="existing"))
    existing_id = existing["id"]

    real_atomic_update = wqr._atomic_update

    def slow_atomic_update(mutate_fn):
        def _slow_mutate(q):
            result = mutate_fn(q)
            time.sleep(0.05)
            return result

        return real_atomic_update(_slow_mutate)

    monkeypatch.setattr(wqr, "_atomic_update", slow_atomic_update)

    def do_patch() -> None:
        wqr.patch_item(existing_id, wqr.WorkItemPatch(status="approved"))

    def do_create() -> None:
        wqr.create_item(wqr.WorkItemCreate(title="new-item"))

    t1 = threading.Thread(target=do_patch)
    t2 = threading.Thread(target=do_create)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    q = wqr._load()
    by_title = {i["title"]: i for i in q.get("items", [])}
    assert "new-item" in by_title, "the concurrent create was lost"
    assert by_title.get("existing", {}).get("status") == "approved", (
        "the concurrent patch was lost or overwritten"
    )
