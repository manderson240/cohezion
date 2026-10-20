"""Second-round review fixes for the actioner's admission gate (2026-10-20).

N1: a refusal that is not a MEASURED RAM refusal (router/catalog unreachable, gate error,
    failed load) is an outage and must exit 1 -- deferring it with exit 0 hid a dead
    inference stack as "nothing to do" every 5 minutes.
N2: the 5-minute timer must never evict another session's model. ``ensure_resident``
    alone evicts below 16 GB while the :13305 proxy may refuse the load at 25 GB, so it
    evicted and was then refused, every tick.
"""

from __future__ import annotations

import pytest

from cohezion.actioner.engine import admission_refusal_is_transient, summary_exit_code
from cohezion.inference import hotswap


def _summary(reason):
    return {"failed": {}, "deferred_admission": ["a"], "admission_refused": reason}


@pytest.mark.parametrize(
    "reason",
    [
        "insufficient RAM — refused before evicting: need 6.6GB, budget 4.0GB",
        "insufficient RAM after evicting 0: need 6.6GB, budget 1.0GB",
        'load failed: HTTP 503 {"error": {"type": "admission_refused", "message": "floor"}}',
    ],
)
def test_measured_memory_refusal_is_a_transient_deferral(reason):
    assert admission_refusal_is_transient(reason)
    assert summary_exit_code(_summary(reason)) == 0


@pytest.mark.parametrize(
    "reason",
    [
        "unknown weight size — refusing blind cold load",  # router/catalog unreachable
        "admission gate error: URLError: connection refused",
        "load failed: HTTP 500 boom",
        "load failed: HTTP 503 Service Unavailable",  # relayed from lemond, not a refusal
        'load failed: HTTP 502 {"error": {"type": "upstream_unreachable"}}',
        "load returned 200 but model is not resident",
    ],
)
def test_outage_refusal_exits_nonzero(reason):
    """Discriminating: the pre-fix code exited 0 for every deferred_admission summary."""
    assert not admission_refusal_is_transient(reason)
    assert summary_exit_code(_summary(reason)) == 1


@pytest.fixture
def fleet(monkeypatch):
    """One idle 3 GB model, 20 GB free, a 6.6 GB target: evicting IDLE would make it fit at 16."""
    calls = {"unload": [], "load": []}

    def _boom_post(path, body, timeout):
        calls["load"].append(body["model_name"])
        return 200, "{}"

    monkeypatch.setattr(
        hotswap,
        "resident_models",
        lambda: [{"model_name": "IDLE", "last_use": 1, "is_busy": False, "loaded": True}],
    )
    monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"TARGET": 5.56, "IDLE": 3.0})
    monkeypatch.setattr(hotswap, "free_gb", lambda: 20.0)
    monkeypatch.setattr(
        hotswap, "unload", lambda mid, timeout=30.0: calls["unload"].append(mid) or True
    )
    monkeypatch.setattr(hotswap, "_post", _boom_post)
    monkeypatch.delenv("COHEZION_ADMISSION_FLOOR_GB", raising=False)
    monkeypatch.delenv("COHEZION_RESOURCE_FLOOR_GB", raising=False)
    return calls


def test_admit_without_eviction_never_unloads_and_refuses_as_transient(fleet, monkeypatch):
    monkeypatch.setenv("COHEZION_ADMISSION_FLOOR_GB", "25")
    r = hotswap.admit_without_eviction("TARGET")
    assert r.ok is False and fleet["unload"] == [] and fleet["load"] == []
    assert admission_refusal_is_transient(r.reason), r.reason


def test_plain_ensure_resident_does_evict_in_the_same_state(fleet):
    """Control: proves the fixture can observe an eviction (else the test above is blind)."""
    hotswap.ensure_resident("TARGET")
    assert fleet["unload"] == ["IDLE"]


def test_admit_without_eviction_loads_when_it_fits_above_the_floor(fleet, monkeypatch):
    """Positive control: a refusal-only gate would pass the tests above; this one loads."""
    state = {"loaded": False}
    resident = [{"model_name": "IDLE", "last_use": 1, "is_busy": False, "loaded": True}]
    target = {"model_name": "TARGET", "last_use": 2, "is_busy": False, "loaded": True}
    monkeypatch.setattr(hotswap, "free_gb", lambda: 40.0)  # 40 - 16 floor >= 6.6 needed
    monkeypatch.setattr(
        hotswap, "resident_models", lambda: resident + ([target] if state["loaded"] else [])
    )

    def _post(path, body, timeout):
        state["loaded"] = True
        fleet["load"].append(body["model_name"])
        return 200, "{}"

    monkeypatch.setattr(hotswap, "_post", _post)
    r = hotswap.admit_without_eviction("TARGET")
    assert r.ok and fleet["load"] == ["TARGET"] and fleet["unload"] == []


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, 16.0),
        ({"COHEZION_ADMISSION_FLOOR_GB": "25"}, 25.0),
        ({"COHEZION_RESOURCE_FLOOR_GB": "24"}, 24.0),
        ({"COHEZION_ADMISSION_FLOOR_GB": "8"}, 16.0),
        ({"COHEZION_ADMISSION_FLOOR_GB": "junk"}, 16.0),
    ],
)
def test_admission_floor_matches_the_proxy_chain_and_never_drops_below_16(
    monkeypatch, env, expected
):
    for k in ("COHEZION_ADMISSION_FLOOR_GB", "COHEZION_RESOURCE_FLOOR_GB"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert hotswap.admission_floor_gb() == expected


def test_protection_alone_prevents_an_eviction_that_would_succeed(fleet, monkeypatch):
    """29 GB free, floor 25: evicting the 3 GB idle model WOULD make 6.6 GB fit (4 + 3).

    Pins ``protect`` independently of the floor: without it, the timer unloads IDLE.
    """
    monkeypatch.setenv("COHEZION_ADMISSION_FLOOR_GB", "25")
    monkeypatch.setattr(hotswap, "free_gb", lambda: 29.0)
    r = hotswap.admit_without_eviction("TARGET")
    assert r.ok is False and fleet["unload"] == [] and fleet["load"] == []


def test_proxy_floor_alone_stops_a_load_the_16gb_floor_would_allow(fleet, monkeypatch):
    """30 GB free: fits above 16 (budget 14) but not above the proxy's 25 (budget 5).

    Pins ``admission_floor_gb`` independently of protection: at 16 the load is POSTed and
    the proxy would refuse it with a 503.
    """
    monkeypatch.setenv("COHEZION_ADMISSION_FLOOR_GB", "25")
    monkeypatch.setattr(hotswap, "free_gb", lambda: 30.0)
    r = hotswap.admit_without_eviction("TARGET")
    assert r.ok is False and fleet["load"] == [] and "insufficient RAM" in r.reason
