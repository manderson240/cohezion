"""The orchestrator is the universal dispatch chokepoint for usage monitoring.

``TieredOrchestrator.run`` returns one ``OrchestrationResult`` per logical dispatch (the
loop escalates tiers internally and accumulates total cost). ``_log_dispatch`` persists
exactly one durable usage record there — so every tier (local Runnable + cloud ``route()``)
AND every ``run_batch`` item (which calls ``self.run`` per item) is captured once, with the
dispatch's TOTAL cost. These tests pin that contract.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

from cohezion.inference.orchestrator import (
    OrchestrationResult,
    QualityGate,
    TieredOrchestrator,
)


def _orch() -> TieredOrchestrator:
    # A single string (cloud) tier is enough to construct a valid orchestrator; these tests
    # call _log_dispatch directly rather than driving the full escalation loop.
    return TieredOrchestrator(tiers=[("claude-haiku-4-5", QualityGate.TRUST)])


def _result(*, text: str, model: str, cost: float) -> OrchestrationResult:
    return OrchestrationResult(
        text=text,
        primary_model=model,
        final_model=model,
        escalation_count=0,
        tier_path=[],
        cost_usd=cost,
        latency_ms=1.0,
        ttft_ms=None,
        error=None,
    )


def test_log_dispatch_returns_same_result_identity():
    """_log_dispatch must be transparent — it returns the exact result it was given, so
    wrapping `return OrchestrationResult(...)` never changes run()'s contract."""
    orch = _orch()
    res = _result(text="hi", model="llama3.2-1b-FLM", cost=0.0)
    with patch("cohezion.inference.usage_log.record_dispatch") as rd:
        out = orch._log_dispatch("prompt", res)
    assert out is res
    assert rd.call_count == 1


def test_log_dispatch_persists_local_dispatch_as_free():
    orch = _orch()
    res = _result(text="answer", model="llama3.2-1b-FLM", cost=0.0)
    with patch("cohezion.inference.usage_log.record_dispatch") as rd:
        orch._log_dispatch("the prompt", res)
    kw = rd.call_args.kwargs
    assert kw["model"] == "llama3.2-1b-FLM"
    assert kw["cost_usd"] == 0.0
    assert kw["text"] == "answer"
    assert kw["source"] == "orchestrator"


def test_log_dispatch_persists_cloud_dispatch_with_total_cost():
    """DISCRIMINATING: the record must carry the dispatch's accumulated (total) cost from
    OrchestrationResult.cost_usd — NOT a hardcoded 0. An impl that dropped cost fails."""
    orch = _orch()
    res = _result(text="deep answer", model="claude-sonnet-4-6", cost=0.0091)
    with patch("cohezion.inference.usage_log.record_dispatch") as rd:
        orch._log_dispatch("hard prompt", res)
    assert rd.call_args.kwargs["cost_usd"] == 0.0091
    assert rd.call_args.kwargs["model"] == "claude-sonnet-4-6"


def test_log_dispatch_is_fail_soft():
    """A sink failure must never break the dispatch path — _log_dispatch swallows and
    still returns the result."""
    orch = _orch()
    res = _result(text="x", model="llama3.2-1b-FLM", cost=0.0)
    with patch(
        "cohezion.inference.usage_log.record_dispatch", side_effect=RuntimeError("disk full")
    ):
        out = orch._log_dispatch("p", res)
    assert out is res  # did not raise


def test_run_batch_routes_through_run_so_logging_is_covered():
    """Structural (V-Model): run_batch must call self.run per item, so the single
    _log_dispatch in run() covers the batch path too (no separate batch instrumentation)."""
    src = inspect.getsource(TieredOrchestrator.run_batch)
    assert "self.run(" in src, "run_batch must dispatch via self.run so usage logging covers it"


def test_run_logs_dispatch_at_both_return_sites():
    """Structural: both of run()'s return points (gate-pass + exhausted) must funnel through
    _log_dispatch, so no dispatch outcome escapes the monitor."""
    src = inspect.getsource(TieredOrchestrator.run)
    # Every `return` that yields an OrchestrationResult goes through _log_dispatch.
    assert src.count("self._log_dispatch(") == 2
    assert "return OrchestrationResult(" not in src  # no un-logged direct return
