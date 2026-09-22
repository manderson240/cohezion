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
