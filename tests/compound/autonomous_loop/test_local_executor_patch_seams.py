"""Patch-seam differential for local_executor (behaviour oracle for the 2026-09-22 split).

Tests across the suite patch ``local_executor.<name>`` (``_chat_complete``, ``_classify_node``,
``_recover_model``, ``warmup_tiers``, ``check_ram``). If one of these names is ever moved so
that its CALLER resolves it from another module's globals, the patch becomes a silent no-op
and the test reaches the real router. A ``dir()``/signature comparison cannot see that: it
checks declaration, not reachability. These tests set each seam on ``local_executor`` and
assert the executor's observable behaviour changes. The network is blocked, so a dead seam
fails loudly here instead of issuing a live inference call.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest

from cohezion.compound.autonomous_loop import local_executor as le


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _refuse(*_a, **_k):
        raise AssertionError("network reached: a local_executor patch seam is dead")

    monkeypatch.setattr(urllib.request, "urlopen", _refuse)


def _task():
    return SimpleNamespace(id="t1", description="say hi", category="general", verification="")


def _fake_chat(calls, answer="answer", verdict="FAIL"):
    def fake(base_url, model, prompt, max_tokens=512, timeout=60.0):
        calls.append(model)
        text = verdict if "strict QA verifier" in prompt else answer
        return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": 7}}

    return fake


def test_chat_complete_seam_reaches_dev_and_judge_lanes(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(le, "_chat_complete", _fake_chat(calls))
    monkeypatch.setattr(le, "_classify_node", lambda _d: "gpu")
    res = le.LocalImprovementExecutor().execute_task(_task(), "")
    assert res["output"] == "answer"
    assert res["judge_pass"] is False  # the judge lane used the patched seam too
    assert len(calls) == 2


def test_classify_node_seam_selects_the_tier_model(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(le, "_chat_complete", _fake_chat(calls))
    monkeypatch.setattr(le, "_classify_node", lambda _d: "npu")
    res = le.LocalImprovementExecutor().execute_task(_task(), "")
    assert res["node"] == "npu"
    assert calls[0] == le._TIER_MODEL["npu"]


def test_recover_model_seam_is_used_on_npu_500(monkeypatch):
    recovered: list[str] = []
    calls: list[str] = []
    ok = _fake_chat(calls)

    def flaky(base_url, model, prompt, max_tokens=512, timeout=60.0):
        if model == le._TIER_MODEL["npu"]:
            raise urllib.error.HTTPError("u", 500, "stale", {}, None)  # type: ignore[arg-type]
        return ok(base_url, model, prompt, max_tokens, timeout)

    monkeypatch.setattr(le, "_chat_complete", flaky)
    monkeypatch.setattr(le, "_classify_node", lambda _d: "npu")
    monkeypatch.setattr(le, "_recover_model", lambda _b, m, *a, **k: recovered.append(m) or False)
    res = le.LocalImprovementExecutor().execute_task(_task(), "")
    assert recovered == [le._TIER_MODEL["npu"]]
    assert res["tried_models"] == [le._TIER_MODEL["npu"], le._DEFAULT_MODEL]


def test_warmup_and_ram_seams_are_used_by_start(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(le, "warmup_tiers", lambda *_a, **_k: seen.append("warmup") or {})
    monkeypatch.setattr(le, "check_ram", lambda *_a, **_k: seen.append("ram") or (True, 99.0))
    ex = le.LocalImprovementExecutor()
    ex.start("")
    assert seen == ["ram", "warmup"]
    assert ex._started is True
