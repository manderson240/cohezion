"""Discriminating tests for the routing-decision log (2026-06-05, backlog item 2).

Every `get_best_for_task` decision is recorded `(task_class, chosen_model, lane,
fell_back, outcome?)` to a JSONL corpus, reusing the resolution_log pattern (fail-soft,
pytest-skipped unless a path is injected). Each test fails a plausible wrong impl:
  - a logger that writes to the REAL corpus during pytest (pollutes the dataset),
  - wiring that records fell_back=True for a task-specialist hit (or False for a fallback),
  - a log call that, when it raises, breaks the routing path it instruments.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.models import model_registry as mr
from cohezion.models.routing_log import (
    DEFAULT_LOG,
    read_routing_decisions,
    record_routing_decision,
)


def test_record_roundtrips_with_injected_path(tmp_path: Path) -> None:
    sink = tmp_path / "routing_log.jsonl"
    rec = record_routing_decision(
        task_class="ROUTING",
        chosen_model="llama3.2-1b-FLM",
        lane="Lane.NPU",
        fell_back=False,
        path=sink,
    )
    assert rec is not None
    back = read_routing_decisions(path=sink)
    assert len(back) == 1
    assert back[0]["task_class"] == "ROUTING"
    assert back[0]["chosen_model"] == "llama3.2-1b-FLM"
    assert back[0]["fell_back"] is False
    assert back[0]["lane"] == "Lane.NPU"


def test_pytest_run_writes_nothing_to_real_corpus() -> None:
    # No path → under pytest the writer must short-circuit (return None) and never touch
    # the real corpus. This is THE falsifiable check: a logger that writes anyway fails here.
    existed = DEFAULT_LOG.exists()
    before = DEFAULT_LOG.stat().st_mtime_ns if existed else None
    out = record_routing_decision(task_class="ROUTING", chosen_model="m", lane="", fell_back=False)
    assert out is None
    if existed:
        assert DEFAULT_LOG.stat().st_mtime_ns == before  # untouched
    else:
        assert not DEFAULT_LOG.exists()  # not created


def test_wiring_logs_specialist_hit_as_not_fell_back(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(mr, "record_routing_decision", lambda **kw: calls.append(kw) or kw)
    reg = mr.ModelRegistry()
    monkeypatch.setattr(reg, "_best_specialist", lambda task, prefer_fast: "specialist-model")

    out = reg.get_best_for_task("classify this sentiment")
    assert out == "specialist-model"
    assert calls and calls[-1]["chosen_model"] == "specialist-model"
    assert calls[-1]["fell_back"] is False  # specialist hit is NOT a fallback


def test_wiring_logs_router_fallback_as_fell_back(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(mr, "record_routing_decision", lambda **kw: calls.append(kw) or kw)
    reg = mr.ModelRegistry()
    monkeypatch.setattr(reg, "_best_specialist", lambda task, prefer_fast: None)

    class _Decision:
        model = "router-model"

    class _Router:
        def select_model(self, **kw):
            return _Decision(), {}

    monkeypatch.setattr(reg, "_ensure_router", lambda: _Router())

    out = reg.get_best_for_task("xyzzy plugh foobar")
    assert out == "router-model"
    assert calls[-1]["chosen_model"] == "router-model"
    assert calls[-1]["fell_back"] is True  # router path IS a fallback


def test_logging_failure_does_not_break_routing(monkeypatch) -> None:
    def boom(**_kw):
        raise RuntimeError("disk full")

    monkeypatch.setattr(mr, "record_routing_decision", boom)
    reg = mr.ModelRegistry()
    monkeypatch.setattr(reg, "_best_specialist", lambda task, prefer_fast: "still-routed")
    # The log raising must NOT propagate — routing returns its answer regardless.
    assert reg.get_best_for_task("classify this") == "still-routed"
