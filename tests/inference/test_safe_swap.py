"""Fix-loop dogfood (task #27): safe_swap restores evicted tenants on load failure.

The incident (2026-07-17, Ternary-Bonsai): lemonade LRU-evicts the current
occupant BEFORE attempting a load, and does NOT restore it if the load fails —
leaving the fleet flushed. safe_swap makes the swap transactional: capture the
prior occupant, attempt, and on failure reload what was evicted.

All fns are dependency-injected → no live server needed.
"""

from __future__ import annotations

from cohezion.inference.load_safety import safe_swap


def test_successful_swap_returns_loaded_no_rollback():
    calls = []
    r = safe_swap(
        "new-model",
        prior_occupant=lambda: "old-model",
        load_fn=lambda m: calls.append(m),
        verify_fn=lambda m: True,  # load succeeded
    )
    assert r["ok"] is True and r["loaded"] == "new-model"
    assert r["restored"] is None
    assert calls == ["new-model"]  # loaded once, no rollback reload


def test_failed_load_restores_prior_occupant():
    # DISCRIMINATING: the whole point. On load failure the evicted tenant MUST
    # be reloaded. A non-discriminating test would only check "didn't crash".
    calls = []

    def load_fn(m):
        calls.append(m)
        if m == "new-model":
            raise RuntimeError("llama-server failed to start")  # the Ternary case

    r = safe_swap(
        "new-model",
        prior_occupant=lambda: "old-model",
        load_fn=load_fn,
        verify_fn=lambda m: True,
    )
    assert r["ok"] is False
    assert r["restored"] == "old-model"  # rollback happened
    assert calls == ["new-model", "old-model"]  # attempted, then restored


def test_verify_false_counts_as_failure_and_restores():
    # Load call didn't raise but the model isn't actually ready → still a failure.
    calls = []
    r = safe_swap(
        "new-model",
        prior_occupant=lambda: "old-model",
        load_fn=lambda m: calls.append(m),
        verify_fn=lambda m: m != "new-model",  # new-model never verifies ready
    )
    assert r["ok"] is False and r["restored"] == "old-model"


def test_no_prior_occupant_nothing_to_restore():
    r = safe_swap(
        "new-model",
        prior_occupant=lambda: None,  # empty slot
        load_fn=lambda m: (_ for _ in ()).throw(RuntimeError("fail")),
        verify_fn=lambda m: True,
    )
    assert r["ok"] is False and r["restored"] is None  # nothing was evicted


def test_restore_failure_is_reported_not_raised():
    # If even the rollback reload fails, safe_swap must report it, never raise
    # (a fleet-flush recovery attempt must not itself crash the caller).
    def load_fn(m):
        raise RuntimeError("everything is down")

    r = safe_swap(
        "new-model",
        prior_occupant=lambda: "old-model",
        load_fn=load_fn,
        verify_fn=lambda m: True,
    )
    assert r["ok"] is False and r["restore_failed"] is True
