"""The actioner's model use goes through the 16 GiB admission gate (ops MAJOR #4).

Before this, only act_loop called ``hotswap.ensure_resident``; the actioner's chat call
reached the :13305 router directly, which loads a missing model on demand with no RAM
floor. A refusal is a safety-gate outcome: a transient deferral, not an item failure,
and not a reason for the systemd unit to report failure every 5 minutes.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from cohezion.actioner.engine import WorkQueueAPI, run_batch, summary_exit_code


ITEMS = [
    {"id": f"adm00000000{n}", "title": "agent routing cache", "created_at": f"2026-09-0{n}"}
    for n in (1, 2, 3)
]


class FakeAPI(WorkQueueAPI):
    def __init__(self, items):
        super().__init__("http://fake")
        self.items, self.actioned = items, []

    def eligible_items(self):
        return [dict(i) for i in self.items]

    def mark_actioned(self, item_id, route):
        self.actioned.append(item_id)
        return {}


class CountingExecutor:
    def __init__(self):
        self.calls = 0

    def execute_task(self, task_description, skill_name, operation_type, execute_fn):
        self.calls += 1
        out, _ = execute_fn("")
        return SimpleNamespace(success=True, output=out, metrics={})


class FakeAdmit:
    def __init__(self, ok):
        self.ok, self.calls = ok, []

    def __call__(self, model_id):
        self.calls.append(model_id)
        return SimpleNamespace(ok=self.ok, reason="insufficient RAM: 9.0GB free < 16GB floor")


def _run(admit, api, exe, tmp_path, runs=1):
    raw = json.dumps({"proposal": "p", "falsifiable_step": "s"})
    for _ in range(runs):
        s = run_batch(
            exe,
            api,
            lambda p: raw,
            proposals_path=tmp_path / "p.jsonl",
            vault_dir=tmp_path / "v",
            admit=admit,
            model="Gemma-4-E4B-it-GGUF",
        )
    return s


def test_refused_admission_makes_no_model_call_and_defers(tmp_path):
    admit, exe, api = FakeAdmit(ok=False), CountingExecutor(), FakeAPI(ITEMS)
    s = _run(admit, api, exe, tmp_path)
    assert exe.calls == 0 and api.actioned == []
    assert admit.calls == ["Gemma-4-E4B-it-GGUF"]  # stops at the first refusal
    assert s["deferred_admission"] == [i["id"] for i in ITEMS]
    assert s["failed"] == {}
    assert "insufficient RAM" in s["admission_refused"]


def test_refusal_never_consumes_the_retry_budget(tmp_path):
    exe, api = CountingExecutor(), FakeAPI(ITEMS[:1])
    s = _run(FakeAdmit(ok=False), api, exe, tmp_path, runs=5)
    assert s["skipped_failed_permanent"] == 0 and s["failed_permanent"] == []
    s = _run(FakeAdmit(ok=True), api, exe, tmp_path)
    assert api.actioned == [ITEMS[0]["id"]]


def test_admitted_calls_are_gated_before_every_item(tmp_path):
    admit, exe, api = FakeAdmit(ok=True), CountingExecutor(), FakeAPI(ITEMS)
    _run(admit, api, exe, tmp_path)
    assert len(admit.calls) == exe.calls == 3


def test_deferral_exits_zero_real_failures_exit_one():
    deferred = {"failed": {}, "deferred_admission": ["a"], "admission_refused": "x"}
    assert summary_exit_code(deferred) == 0
    guard = {"failed": {"b": "Resources constrained"}, "deferred_transient_guard": ["b"]}
    assert summary_exit_code(guard) == 0
    crash = {"failed": {"c": "connection refused"}}
    assert summary_exit_code(crash) == 1
    terminal = {"failed": {"d": "x", "e": "y"}, "rejected": ["d"], "failed_permanent": ["e"]}
    assert summary_exit_code(terminal) == 0


def test_driver_wires_the_admission_gate_and_exit_code(monkeypatch, capsys):
    """Consumption: the production driver passes hotswap.ensure_resident as ``admit``."""
    import importlib.util
    import sys
    from pathlib import Path

    import cohezion.compound as compound
    from cohezion.actioner import engine
    from cohezion.inference import hotswap

    seen: dict = {}

    def fake_run_batch(executor, **kw):
        seen.update(kw)
        return {"failed": {}, "deferred_admission": ["x"], "admission_refused": "floor"}

    monkeypatch.setattr(engine, "run_batch", fake_run_batch)
    monkeypatch.setattr(engine, "default_chat_fn", lambda model: (lambda p: ""))
    monkeypatch.setattr(compound, "make_executor", lambda mcp: object())
    monkeypatch.setattr(sys, "argv", ["actioner.py"])
    path = Path(__file__).resolve().parents[2] / "scripts" / "actioner.py"
    spec = importlib.util.spec_from_file_location("_actioner_driver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
    assert seen["admit"] is hotswap.ensure_resident
    assert "DEFERRED (transient)" in capsys.readouterr().out
