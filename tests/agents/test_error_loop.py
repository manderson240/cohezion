"""Tests for the orchestration error-loop layer (activates skill_adaptor + livelock bound)."""

from __future__ import annotations

from types import SimpleNamespace

from cohezion.agent.error_loop import (
    ErrorClass,
    ErrorClassifier,
    ReDispatchLedger,
    error_signature,
    reflect,
)
from cohezion.memory.trust_hierarchy import GroundTruthHierarchy


def _tc(name, *, error=None, result=None):
    return SimpleNamespace(tool_name=name, error=error, result=result or {})


def _trace(task_id, depth, tool_calls):
    n = SimpleNamespace(task_id=task_id, depth=depth, tool_calls=tool_calls)
    n.walk = lambda: iter([n])
    return n


# -- error_signature: value-masking (the dedup key) ---------------------------


def test_signature_masks_volatile_tokens():
    a = error_signature("write", "disk full at /tmp/a/1 (0xdeadbeef) after 42 tries")
    b = error_signature("write", "disk full at /var/b/9 (0xcafef00d) after 99 tries")
    assert a == b  # same failure mode -> same signature despite different paths/numbers/hex


def test_signature_distinguishes_skill_and_mode():
    assert error_signature("write", "disk full") != error_signature("read", "disk full")
    assert error_signature("api", "rate limited") != error_signature("api", "not found")


# -- classifier ---------------------------------------------------------------


def test_classifier_maps_known_classes():
    c = ErrorClassifier()
    assert c.classify("solve", "energy NaN at step 3") is ErrorClass.DIVERGENCE
    assert c.classify("bash", "CUDA out of memory") is ErrorClass.RESOURCE
    assert c.classify("api", "HTTP 429 rate limit") is ErrorClass.TRANSIENT
    assert c.classify("api", "model not found") is ErrorClass.PERMANENT
    assert c.classify("x", "weird unexplained thing") is ErrorClass.UNKNOWN


# -- ReDispatchLedger: the persisted livelock bound ---------------------------


def test_ledger_caps_per_signature():
    led = ReDispatchLedger(max_per_signature=3)
    sig = "write:disk full"
    assert [led.allow(sig) for _ in range(4)] == [True, True, True, False]
    assert led.attempts(sig) == 3


def test_ledger_independent_per_signature():
    led = ReDispatchLedger(max_per_signature=1)
    assert led.allow("a:x") is True
    assert led.allow("b:y") is True  # different signature unaffected
    assert led.allow("a:x") is False


def test_ledger_reset_on_success():
    led = ReDispatchLedger(max_per_signature=1)
    led.allow("a:x")
    led.reset("a:x")
    assert led.allow("a:x") is True  # cleared -> can dispatch again


def test_ledger_persists_across_worker_boundary():
    led = ReDispatchLedger(max_per_signature=2)
    led.allow("a:x")
    led.allow("a:x")  # cap reached
    # serialize (orchestrator persists) -> fresh worker would reset, but the ledger does not
    restored = ReDispatchLedger.from_dict(led.to_dict())
    assert restored.allow("a:x") is False  # the bound survived


# -- reflect: the controller decision -----------------------------------------


def test_reflect_commit_on_clean_trace():
    led = ReDispatchLedger()
    out = reflect(_trace("t", 0, [_tc("bash")]), ledger=led)
    assert out["action"] == "commit"


def test_reflect_escalates_permanent_fault():
    led = ReDispatchLedger()
    out = reflect(_trace("t", 0, [_tc("api", error="model not found")]), ledger=led)
    assert out["action"] == "escalate" and out["class"] == "permanent"


def test_reflect_retries_correctable_and_activates_adaptation():
    led = ReDispatchLedger(max_per_signature=3)
    trust = GroundTruthHierarchy()
    out = reflect(
        _trace("t", 0, [_tc("solve", error="energy NaN diverged")]), ledger=led, trust=trust
    )
    assert out["action"] == "retry"
    assert out["class"] == "divergence"
    assert out["adaptation"]["adapted"] is True  # skill_adaptor was activated
    assert len(trust) == 1  # trust composition fired


def test_reflect_abandons_after_redispatch_cap():
    led = ReDispatchLedger(max_per_signature=2)
    t = lambda: _trace("t", 0, [_tc("solve", error="energy NaN diverged")])
    a1 = reflect(t(), ledger=led)
    a2 = reflect(t(), ledger=led)
    a3 = reflect(t(), ledger=led)  # third dispatch of same signature
    assert a1["action"] == "retry" and a2["action"] == "retry"
    assert a3["action"] == "abandon"  # livelock guard fired across (simulated) fresh dispatches
    assert "cap" in a3["reason"]
