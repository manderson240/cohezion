"""Infra-vs-item classification must read structured fields, never model prose (C5).

2026-09-22 review: when ``metrics["error"]`` was absent, ``_failure_reason`` fell back to
``result.output`` and ``is_infra_failure`` regex-matched "timeout" in it. A proposal ABOUT
timeouts was then classed as an outage, never counted, and retried forever -- the exact
541-row defect the retry cap was added to stop.
"""

from __future__ import annotations

import urllib.error
from types import SimpleNamespace

from cohezion.actioner.engine import MAX_FAILURE_ATTEMPTS, WorkQueueAPI, run_batch


ITEM = {"id": "c5c5c5000001", "title": "agent routing cache", "domain": "cs"}


class FakeAPI(WorkQueueAPI):
    def __init__(self, items, patch_exc=None):
        super().__init__("http://fake")
        self.items, self.patch_exc = items, patch_exc

    def eligible_items(self):
        return [dict(i) for i in self.items]

    def mark_actioned(self, item_id, route):
        if self.patch_exc:
            raise self.patch_exc
        return {}

    def mark_rejected(self, item_id, note):
        return {}


class ResultExecutor:
    def __init__(self, **result):
        self.result, self.calls = result, 0

    def execute_task(self, task_description, skill_name, operation_type, execute_fn):
        self.calls += 1
        return SimpleNamespace(**self.result)


def _drain(exe, api, tmp_path, runs=MAX_FAILURE_ATTEMPTS + 2):
    return [
        run_batch(
            exe, api, lambda p: "{}", proposals_path=tmp_path / "p.jsonl", vault_dir=tmp_path / "v"
        )
        for _ in range(runs)
    ]


def test_model_prose_about_timeouts_still_consumes_the_retry_budget(tmp_path):
    prose = "Proposed change: raise the request timeout and retry on connection refused."
    exe = ResultExecutor(success=False, output=prose, metrics={})
    summaries = _drain(exe, FakeAPI([ITEM]), tmp_path)
    assert exe.calls == MAX_FAILURE_ATTEMPTS
    assert summaries[MAX_FAILURE_ATTEMPTS - 1]["failed_permanent"] == [ITEM["id"]]


def test_structured_error_type_is_infra(tmp_path):
    exe = ResultExecutor(
        success=False, output="Error: boom", metrics={"error": "boom", "error_type": "URLError"}
    )
    summaries = _drain(exe, FakeAPI([ITEM]), tmp_path)
    assert exe.calls == MAX_FAILURE_ATTEMPTS + 2  # never capped
    assert summaries[-1]["failed_permanent"] == []


def test_structured_error_message_is_infra(tmp_path):
    exe = ResultExecutor(
        success=False,
        output="",
        metrics={"error": "Error in chat completions (status 404): model_not_loaded"},
    )
    summaries = _drain(exe, FakeAPI([ITEM]), tmp_path)
    assert exe.calls == MAX_FAILURE_ATTEMPTS + 2
    assert summaries[-1]["failed_permanent"] == []


def test_api_outage_after_a_successful_cycle_is_infra(tmp_path):
    exe = ResultExecutor(success=True, output="{}", metrics={})
    api = FakeAPI([ITEM], patch_exc=urllib.error.URLError("[Errno 111] Connection refused"))
    summaries = _drain(exe, api, tmp_path)
    assert summaries[-1]["failed_permanent"] == []


def test_api_4xx_is_not_infra_even_when_its_text_says_timeout(tmp_path):
    exe = ResultExecutor(success=True, output="{}", metrics={})
    err = urllib.error.HTTPError("http://fake", 422, "Unprocessable: timeout", {}, None)
    summaries = _drain(exe, FakeAPI([ITEM], patch_exc=err), tmp_path)
    assert summaries[MAX_FAILURE_ATTEMPTS - 1]["failed_permanent"] == [ITEM["id"]]
