"""Non-guardrail failures must not retry forever (2026-09-21).

Live evidence: 541 journey rows "Action research item 77adb..." from one item that
failed every 5-minute run with no limit. The cap counts failures per item content in the
ledger next to the proposals file; infrastructure failures never count, because an
outage says nothing about the item (observed live the same day: ``No model loaded``).
"""

from __future__ import annotations

from types import SimpleNamespace

from cohezion.actioner.engine import MAX_FAILURE_ATTEMPTS, WorkQueueAPI, run_batch


class FakeAPI(WorkQueueAPI):
    def __init__(self, items):
        super().__init__("http://fake")
        self.items = items
        self.rejected: list[str] = []

    def eligible_items(self):
        return [dict(i) for i in self.items]

    def mark_actioned(self, item_id, route):
        return {}

    def mark_rejected(self, item_id, note):
        self.rejected.append(item_id)
        return {}


class FailingExecutor:
    def __init__(self, reason):
        self.reason = reason
        self.calls = 0

    def execute_task(self, task_description, skill_name, operation_type, execute_fn):
        self.calls += 1
        return SimpleNamespace(success=False, output="", metrics={"error": self.reason})


ITEM = {"id": "77adb0000001", "title": "agent routing cache", "domain": "cs"}


def _run(executor, api, tmp_path):
    return run_batch(
        executor,
        api,
        lambda p: "{}",
        proposals_path=tmp_path / "p.jsonl",
        vault_dir=tmp_path / "v",
    )


def test_always_failing_item_is_attempted_at_most_n_times(tmp_path):
    api, exe = FakeAPI([ITEM]), FailingExecutor("model returned malformed JSON")
    summaries = [_run(exe, api, tmp_path) for _ in range(MAX_FAILURE_ATTEMPTS + 3)]
    assert exe.calls == MAX_FAILURE_ATTEMPTS
    assert summaries[MAX_FAILURE_ATTEMPTS - 1]["failed_permanent"] == [ITEM["id"]]
    assert summaries[-1]["skipped_failed_permanent"] == 1
    assert summaries[-1]["failed"] == {}
    assert api.rejected == []  # terminal locally; the card itself is not rewritten


def test_infra_failures_never_consume_the_retry_budget(tmp_path):
    exe = FailingExecutor('Error in chat completions (status 404): {"type":"model_not_loaded"}')
    api = FakeAPI([ITEM])
    for _ in range(MAX_FAILURE_ATTEMPTS + 3):
        s = _run(exe, api, tmp_path)
    assert exe.calls == MAX_FAILURE_ATTEMPTS + 3
    assert s["failed_permanent"] == []


def test_changed_item_gets_a_fresh_budget(tmp_path):
    api, exe = FakeAPI([ITEM]), FailingExecutor("model returned malformed JSON")
    for _ in range(MAX_FAILURE_ATTEMPTS + 1):
        _run(exe, api, tmp_path)
    assert exe.calls == MAX_FAILURE_ATTEMPTS
    api.items = [{**ITEM, "title": "agent routing cache (revised abstract)"}]
    _run(exe, api, tmp_path)
    assert exe.calls == MAX_FAILURE_ATTEMPTS + 1


def test_guardrail_failures_still_reject_and_are_not_counted(tmp_path):
    api = FakeAPI([ITEM])
    s = _run(
        FailingExecutor("Input blocked by guardrails: Potential injection pattern"), api, tmp_path
    )
    assert api.rejected == [ITEM["id"]]
    assert s["failed_permanent"] == []


# --- Guardrail blocks split by guard (2026-09-22) -----------------------------------
# A ResourceGuard BLOCK ("Resources constrained: CPU=...") is load, not content: it used
# to permanently reject a good card on a load spike because every "Input blocked by
# guardrails" message was treated as terminal.


class GuardBlockingExecutor:
    """Returns the executor's real guardrail-block metrics shape, naming the guard."""

    def __init__(self, guard, reason):
        self.guard, self.reason, self.calls = guard, reason, 0

    def execute_task(self, task_description, skill_name, operation_type, execute_fn):
        self.calls += 1
        msg = f"Input blocked by guardrails: {self.reason}"
        return SimpleNamespace(
            success=False,
            output=f"Error: {msg}",
            metrics={
                "error": msg,
                "blocked_by_guardrails": True,
                "blocked_by_guard": self.guard,
                "blocked_guard_reason": self.reason,
            },
        )


def test_resource_guard_block_is_retryable_and_uncounted(tmp_path):
    exe = GuardBlockingExecutor("resource", "Resources constrained: CPU=97.0%, Memory=91.0%")
    api = FakeAPI([ITEM])
    for _ in range(MAX_FAILURE_ATTEMPTS + 2):
        s = _run(exe, api, tmp_path)
    assert api.rejected == []  # a load spike must not reject a good card
    assert exe.calls == MAX_FAILURE_ATTEMPTS + 2  # never skipped: not counted
    assert s["failed_permanent"] == [] and s["skipped_failed_permanent"] == 0
    assert s["deferred_transient_guard"] == [ITEM["id"]]


def test_rate_limit_block_is_transient_too(tmp_path):
    api = FakeAPI([ITEM])
    _run(GuardBlockingExecutor("rate_limit", "Rate limit exceeded"), api, tmp_path)
    assert api.rejected == []


def test_fail_closed_guard_exception_is_transient_even_for_a_content_guard(tmp_path):
    api = FakeAPI([ITEM])
    exe = GuardBlockingExecutor("prompt_injection", "Guardrail exception: prompt_injection")
    _run(exe, api, tmp_path)
    assert api.rejected == []


def test_prompt_injection_block_still_terminal_rejects(tmp_path):
    api = FakeAPI([ITEM])
    exe = GuardBlockingExecutor("prompt_injection", "Potential injection pattern detected")
    s = _run(exe, api, tmp_path)
    assert api.rejected == [ITEM["id"]]
    assert "deferred_transient_guard" not in s
    assert s["failed_permanent"] == []


def test_executor_reports_the_blocking_guard_name():
    """Producer side: the real CompoundExecutor must put the guard name in metrics."""
    from unittest.mock import MagicMock

    from cohezion.compound.executor import CompoundExecutor
    from cohezion.security.guardrail_pipeline import (
        GuardrailAction,
        GuardrailPipeline,
        GuardrailResult,
    )

    class LoadGuard:
        async def check(self, text, context):
            return GuardrailResult(action=GuardrailAction.BLOCK, reason="Resources constrained")

    exe = CompoundExecutor(
        MagicMock(), guardrail_pipeline=GuardrailPipeline(guardrails=[("resource", LoadGuard())])
    )
    result = exe.execute_task(
        task_description="Action research item x",
        skill_name="research-actioner",
        operation_type="generate",
        execute_fn=lambda g: ("never", {}),
    )
    assert result.success is False
    assert result.metrics["blocked_by_guard"] == "resource"
