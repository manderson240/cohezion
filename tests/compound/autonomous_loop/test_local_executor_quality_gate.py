"""Falsification-first tests for the QA-judge knot in the autonomous loop.

THE LEAK (protocol audit #2): `local_executor.execute_task` set
`success = bool(output.strip())` — a non-empty but WRONG answer passed, so the
loop could never register a genuine quality failure and cloud escalation was
driven by emptiness, not quality.

THE KNOT: a SECOND local lemonade lane (`_judge_quality`) judges the Dev output
against the task's acceptance criteria. Only a genuine quality FAIL counts.

These tests mock the judge lane (deterministic) by routing `_chat_complete` on
the prompt: the Dev prompt contains "compound engineering assistant", the judge
prompt contains "QA verifier". The falsification test (test_*_wrong_answer_*)
FAILS against the old `bool(strip())` impl and PASSES against the knot.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from cohezion.compound.autonomous_loop import local_executor as le


@dataclass
class _Task:
    id: str
    description: str
    category: str
    verification: str


def _make_chat(dev_output: str, judge_verdict: str, *, judge_raises: bool = False):
    """side_effect for _chat_complete: routes Dev vs judge lane by prompt content."""
    calls: dict[str, int] = {"dev": 0, "judge": 0}

    def fake(base_url, model, prompt, max_tokens=512, timeout=60.0):
        if "QA verifier" in prompt:
            calls["judge"] += 1
            if judge_raises:
                raise RuntimeError("judge lane hiccup")
            content = judge_verdict
        else:
            calls["dev"] += 1
            content = dev_output
        return {"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 10}}

    fake.calls = calls  # type: ignore[attr-defined]
    return fake


@pytest.fixture
def _npu_node(monkeypatch):
    # Force a deterministic node so the Dev model is stable; judge uses its own model.
    monkeypatch.setattr(le, "_classify_node", lambda _d: "npu")


def test_nonempty_wrong_answer_yields_failure(monkeypatch, _npu_node):
    """FALSIFICATION: a non-empty but acceptance-VIOLATING output → success=False.

    Old impl (`success = bool(output.strip())`) returns True here → this test RED.
    """
    chat = _make_chat("The capital of France is Berlin.", "FAIL")
    monkeypatch.setattr(le, "_chat_complete", chat)
    ex = le.LocalImprovementExecutor()
    task = _Task("t1", "What is the capital of France?", "general", "Answer must be Paris")
    result = ex.execute_task(task, "/tmp/wt")
    # The Dev output is non-empty (the old gate would PASS it) — prove that:
    assert result["output"].strip(), "Dev output must be non-empty (old gate would pass)"
    assert result["success"] is False  # the knot: quality FAIL
    assert chat.calls["judge"] == 1  # judge lane actually consulted


def test_correct_answer_yields_success(monkeypatch, _npu_node):
    chat = _make_chat("The capital of France is Paris.", "PASS")
    monkeypatch.setattr(le, "_chat_complete", chat)
    ex = le.LocalImprovementExecutor()
    task = _Task("t1", "What is the capital of France?", "general", "Answer must be Paris")
    result = ex.execute_task(task, "/tmp/wt")
    assert result["success"] is True


def test_empty_output_fails_fast_without_judge(monkeypatch, _npu_node):
    """Cheap pre-filter: empty output → fail without ever calling the judge lane."""
    chat = _make_chat("   ", "PASS")  # judge would say PASS, but must not be called
    monkeypatch.setattr(le, "_chat_complete", chat)
    ex = le.LocalImprovementExecutor()
    task = _Task("t1", "Do something", "general", "non-empty")
    result = ex.execute_task(task, "/tmp/wt")
    assert result["success"] is False
    assert chat.calls["judge"] == 0  # pre-filter short-circuits the judge


def test_judge_error_fails_open_to_prefilter(monkeypatch, _npu_node):
    """Fail-OPEN: judge-lane error must NOT abort a task → degrade to pre-filter PASS."""
    chat = _make_chat("Some non-empty answer.", "FAIL", judge_raises=True)
    monkeypatch.setattr(le, "_chat_complete", chat)
    ex = le.LocalImprovementExecutor()
    task = _Task("t1", "Do something", "general", "criteria")
    result = ex.execute_task(task, "/tmp/wt")
    assert result["success"] is True  # non-empty + judge errored → fail-open PASS


def test_genuine_quality_fails_route_to_cloud_exactly_once(monkeypatch):
    """N genuine QA-fails (quality, not emptiness) drive cloud escalation once."""
    from cohezion.compound.autonomous_loop.coordinator import LoopConfig, LoopCoordinator, LoopTask

    # Real LocalImprovementExecutor, but no warmup subprocess / RAM gate.
    monkeypatch.setattr(le, "warmup_tiers", lambda *a, **k: {})
    monkeypatch.setattr(le, "check_ram", lambda *a, **k: (True, 100.0))
    monkeypatch.setattr(le, "_classify_node", lambda _d: "npu")
    # Dev output non-empty but WRONG; judge says FAIL → quality-driven escalation.
    monkeypatch.setattr(le, "_chat_complete", _make_chat("Non-empty wrong answer.", "FAIL"))

    cloud = Mock()
    cloud._started = True
    cloud.execute_task.return_value = {"success": True, "tokens_used": 5, "node": "cloud"}

    cfg = LoopConfig(
        use_local_inference=True,
        cloud_escalation_threshold=3,
        sprint_duration_seconds=1e9,
        max_tokens=10**9,
    )
    coord = LoopCoordinator(cfg)
    # Same task id picked 4× → 3 local quality-fails, 4th escalates to cloud.
    coord._backlog = [
        LoopTask("t1", "wrong-on-purpose", "general", 1, "must be correct", 10) for _ in range(4)
    ]
    coord.run(executor=cloud)

    assert cloud.execute_task.call_count == 1
