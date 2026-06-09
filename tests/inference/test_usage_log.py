"""Tests for the durable usage sink (the monitoring keystone).

``TokenUsageRecord`` already computes local-vs-cloud tokens and cost, but it is a
process-lifetime in-memory singleton — nothing persists it, so usage evaporates on
process exit and there is no cross-session/cross-harness record to monitor.

``usage_log`` mirrors ``routing_log``: fail-soft, pytest-skipped without an explicit
``path`` (the suite must never pollute the real corpus), append-JSONL to
``~/.cohezion-research/logs/usage_log.jsonl``. ``summarize_usage`` is the read side that
the monitor surfaces.

The discriminating tests below kill the two most plausible wrong implementations:
counting *records* instead of *tokens* for ``local_fraction``, and summing *all* costs
instead of *cloud-only*.
"""

from __future__ import annotations

import json

import pytest

from cohezion.inference.usage_log import (
    format_report,
    read_usage,
    record_usage,
    summarize_usage,
)


def _rec(tmp_path, **over):
    base = {
        "model": "llama3.2-1b-FLM",
        "lane": "npu",
        "input_tokens": 10,
        "output_tokens": 20,
        "cost_usd": 0.0,
        "local": True,
        "path": tmp_path / "usage_log.jsonl",
    }
    base.update(over)
    return record_usage(**base)


def test_record_usage_writes_one_jsonl_line(tmp_path):
    written = _rec(
        tmp_path,
        model="claude-sonnet-4-6",
        lane="cloud",
        input_tokens=200,
        output_tokens=50,
        cost_usd=0.00135,
        local=False,
    )
    sink = tmp_path / "usage_log.jsonl"
    assert sink.exists()
    lines = sink.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["model"] == "claude-sonnet-4-6"
    assert rec["cost_usd"] == 0.00135
    assert rec["local"] is False
    assert written == rec  # returns the dict it wrote


def test_record_usage_skipped_under_pytest_without_path():
    """Mirrors routing_log: a path-less call under pytest must no-op (returns None),
    so the suite never writes the real ~/.cohezion-research corpus."""
    assert (
        record_usage(
            model="x", lane="npu", input_tokens=1, output_tokens=1, cost_usd=0.0, local=True
        )
        is None
    )


def test_read_usage_roundtrips(tmp_path):
    _rec(tmp_path)
    _rec(tmp_path, local=False, model="claude-haiku-4-5", lane="cloud", cost_usd=0.001)
    recs = read_usage(path=tmp_path / "usage_log.jsonl")
    assert len(recs) == 2


def test_read_usage_filters_by_source(tmp_path):
    _rec(tmp_path, source="live")
    _rec(tmp_path, source="replay")
    live = read_usage(source="live", path=tmp_path / "usage_log.jsonl")
    assert len(live) == 1 and live[0]["source"] == "live"


def test_summarize_local_fraction_is_token_weighted_not_record_count(tmp_path):
    """DISCRIMINATING: 500 local tokens + 250 cloud tokens → local_fraction 500/750 ≈ 0.667.
    An impl that counts RECORDS (1 local, 1 cloud) would wrongly report 0.5."""
    _rec(tmp_path, input_tokens=300, output_tokens=200, local=True, cost_usd=0.0)
    _rec(
        tmp_path,
        input_tokens=200,
        output_tokens=50,
        local=False,
        model="claude-sonnet-4-6",
        lane="cloud",
        cost_usd=0.00135,
    )
    s = summarize_usage(read_usage(path=tmp_path / "usage_log.jsonl"))
    assert s.local_tokens == 500
    assert s.cloud_input_tokens == 200 and s.cloud_output_tokens == 50
    assert s.total_tokens == 750
    assert s.local_fraction == pytest.approx(500 / 750, abs=1e-3)  # NOT 0.5


def test_summarize_cloud_cost_sums_only_cloud(tmp_path):
    """DISCRIMINATING: local rows carry cost 0.0; only cloud cost counts. An impl that
    summed a non-zero local cost or double-counted would fail this exact value."""
    _rec(tmp_path, local=True, cost_usd=0.0)
    _rec(
        tmp_path,
        local=False,
        model="claude-sonnet-4-6",
        lane="cloud",
        input_tokens=200,
        output_tokens=50,
        cost_usd=0.00135,
    )
    s = summarize_usage(read_usage(path=tmp_path / "usage_log.jsonl"))
    assert s.cloud_cost_usd == pytest.approx(0.00135, abs=1e-9)


def test_summarize_by_model_tracks_calls_and_tokens(tmp_path):
    _rec(
        tmp_path,
        model="claude-haiku-4-5",
        lane="cloud",
        local=False,
        input_tokens=100,
        output_tokens=20,
        cost_usd=0.0001,
    )
    _rec(
        tmp_path,
        model="claude-haiku-4-5",
        lane="cloud",
        local=False,
        input_tokens=50,
        output_tokens=10,
        cost_usd=0.00005,
    )
    s = summarize_usage(read_usage(path=tmp_path / "usage_log.jsonl"))
    haiku = s.by_model["claude-haiku-4-5"]
    assert haiku["calls"] == 2
    assert haiku["tokens"] == 180  # 120 + 60
    assert haiku["cost_usd"] == pytest.approx(0.00015, abs=1e-9)


def test_summarize_empty_no_div_by_zero():
    s = summarize_usage([])
    assert s.local_tokens == 0 and s.total_tokens == 0
    assert s.local_fraction == 0.0
    assert s.cloud_cost_usd == 0.0


def test_format_report_shows_budget_remaining(tmp_path):
    """DISCRIMINATING on the budget arithmetic: $5.00 budget − $0.00135 spent = $4.99865."""
    _rec(
        tmp_path,
        local=False,
        model="claude-sonnet-4-6",
        lane="cloud",
        input_tokens=200,
        output_tokens=50,
        cost_usd=0.00135,
    )
    s = summarize_usage(read_usage(path=tmp_path / "usage_log.jsonl"))
    report = format_report(s, budget_usd=5.0)
    assert "4.99" in report  # remaining ≈ 4.99865
    assert "local" in report.lower()


# ---------------------------------------------------------------------------
# record_dispatch — the convenience used by the run()/extend_claude chokepoints
# ---------------------------------------------------------------------------


def test_record_dispatch_local_model_zero_cost_is_local(tmp_path):
    from cohezion.inference.usage_log import record_dispatch

    rec = record_dispatch(
        prompt="x" * 40,
        text="y" * 20,
        model="llama3.2-1b-FLM",
        cost_usd=0.0,
        path=tmp_path / "usage_log.jsonl",
    )
    assert rec["local"] is True and rec["lane"] == "local"
    assert rec["input_tokens"] == 10 and rec["output_tokens"] == 5  # len//4


def test_record_dispatch_cloud_model_with_cost_is_cloud(tmp_path):
    from cohezion.inference.usage_log import record_dispatch

    rec = record_dispatch(
        prompt="x" * 40,
        text="y" * 20,
        model="claude-sonnet-4-6",
        cost_usd=0.006,
        path=tmp_path / "usage_log.jsonl",
    )
    assert rec["local"] is False and rec["lane"] == "cloud"
    assert rec["cost_usd"] == 0.006


def test_record_dispatch_cached_cloud_zero_cost_still_cloud(tmp_path):
    """DISCRIMINATING: a $0 *cached* cloud hit must NOT be miscounted as free local
    silicon. Kills the naive 'cost==0 ⇒ local' classifier — the model id decides too."""
    from cohezion.inference.usage_log import record_dispatch

    rec = record_dispatch(
        prompt="x" * 40,
        text="y" * 20,
        model="claude-haiku-4-5",
        cost_usd=0.0,
        cached=True,
        path=tmp_path / "usage_log.jsonl",
    )
    assert rec["local"] is False and rec["lane"] == "cloud"


# ---------------------------------------------------------------------------
# electricity — local silicon is NOT free; it draws watts (user requirement)
# ---------------------------------------------------------------------------


def test_estimate_energy_usd_arithmetic(monkeypatch):
    """3600 W for 1000 ms = 0.001 kWh; at $1/kWh that is exactly $0.001."""
    monkeypatch.setenv("COHEZION_ELECTRICITY_USD_PER_KWH", "1.0")
    from cohezion.inference.usage_log import estimate_energy_usd

    assert estimate_energy_usd(3600.0, 1000.0) == pytest.approx(0.001, abs=1e-9)


def test_record_dispatch_local_includes_electricity(tmp_path, monkeypatch):
    """A local dispatch costs $0 in API but a NONZERO electricity charge proportional to
    lane watts × duration."""
    monkeypatch.setenv("COHEZION_ELECTRICITY_USD_PER_KWH", "0.17")
    from cohezion.inference.usage_log import record_dispatch

    rec = record_dispatch(
        prompt="x" * 40,
        text="y" * 20,
        model="Gemma-4-E4B-it-GGUF",
        cost_usd=0.0,
        latency_ms=800.0,
        lane="igpu_rocwmma",
        path=tmp_path / "usage_log.jsonl",
    )
    assert rec["cost_usd"] == 0.0  # no API cost
    assert rec["energy_usd"] > 0.0  # but real electricity


def test_record_dispatch_cloud_has_zero_local_electricity(tmp_path):
    """DISCRIMINATING: a cloud dispatch draws ~0 LOCAL watts — the user does not pay for
    Anthropic's datacenter power. energy_usd must be 0 even with a long latency."""
    from cohezion.inference.usage_log import record_dispatch

    rec = record_dispatch(
        prompt="x" * 40,
        text="y" * 200,
        model="claude-sonnet-4-6",
        cost_usd=0.009,
        latency_ms=5000.0,
        path=tmp_path / "usage_log.jsonl",
    )
    assert rec["energy_usd"] == 0.0


def test_summary_total_cost_includes_electricity(tmp_path, monkeypatch):
    """DISCRIMINATING: total_cost_usd = cloud API $ + local electricity $. An impl that
    reported only cloud cost (the old 'local is free' model) fails this."""
    monkeypatch.setenv("COHEZION_ELECTRICITY_USD_PER_KWH", "1.0")
    from cohezion.inference.usage_log import record_dispatch

    p = tmp_path / "usage_log.jsonl"
    record_dispatch(
        prompt="x" * 40,
        text="y" * 40,
        model="Gemma-4-31B-it-GGUF",
        cost_usd=0.0,
        latency_ms=3600_000.0,
        lane="cpu",
        path=p,
    )  # 55W·1h
    record_dispatch(
        prompt="x" * 40,
        text="y" * 40,
        model="claude-sonnet-4-6",
        cost_usd=0.006,
        latency_ms=900.0,
        path=p,
    )
    s = summarize_usage(read_usage(path=p))
    # CPU 55 W for 1 h = 0.055 kWh × $1 = $0.055 electricity; cloud API = $0.006.
    assert s.local_energy_usd == pytest.approx(0.055, abs=1e-6)
    assert s.cloud_cost_usd == pytest.approx(0.006, abs=1e-9)
    assert s.total_cost_usd == pytest.approx(0.055 + 0.006, abs=1e-6)
