"""verify_all_bounded must distinguish UNREACHABLE from EMPTY (act-probe oracle, 2026-09-21).

Both cases currently return ``[ROUTER_UNREACHABLE]`` because ``_get_catalog`` maps a
network failure and a reachable router with zero models to the same ``[]``. An operator
reading "router unreachable" goes to restart a router that is up. Both remain UNSAFE
(cannot vouch for bounds), but the reason must differ.

Tests patch the HTTP boundary, not ``_get_catalog``, so any correct fix passes.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from cohezion.inference import oom_guard


def _unreachable(*_a, **_k):
    raise urllib.error.URLError("connection refused")


def _empty(*_a, **_k):
    return io.BytesIO(json.dumps({"data": []}).encode())


def test_unreachable_router_reports_router_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _unreachable)
    safe, violations = oom_guard.verify_all_bounded("http://127.0.0.1:9")
    assert safe is False
    assert violations == [oom_guard.ROUTER_UNREACHABLE]


def test_reachable_empty_catalog_reports_empty_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _empty)
    safe, violations = oom_guard.verify_all_bounded("http://127.0.0.1:9")
    assert safe is False, "an empty catalog cannot vouch for bounds either"
    assert violations == [oom_guard.EMPTY_CATALOG]


def test_sentinels_are_distinct_strings() -> None:
    assert isinstance(oom_guard.EMPTY_CATALOG, str)
    assert oom_guard.EMPTY_CATALOG != oom_guard.ROUTER_UNREACHABLE


# Added 2026-09-21 after a GREEN local-model fix returned None from _get_catalog on an
# unreachable router: the oracle above passed while pre_load_gate crashed with TypeError.
# The other two _get_catalog callers must keep working when the router is down.
def test_pre_load_gate_survives_unreachable_router(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _unreachable)
    monkeypatch.setattr(oom_guard, "check_ram", lambda *_a, **_k: (True, 100.0))
    allowed, reason = oom_guard.pre_load_gate(
        "Qwen3.6-35B-A3B-GGUF", 0, base_url="http://127.0.0.1:9"
    )
    assert allowed is False and "N3" in reason  # name heuristic still blocks ctx=0 on a 35B
    ok, _ = oom_guard.pre_load_gate("Qwen3-0.6B-GGUF", 4096, base_url="http://127.0.0.1:9")
    assert ok is True


def test_scan_and_harden_reports_offline_on_unreachable_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _unreachable)
    assert oom_guard.scan_and_harden("http://127.0.0.1:9")["router_offline"] is True
