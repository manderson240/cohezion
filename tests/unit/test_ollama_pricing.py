"""Unit tests for Ollama Cloud pricing, Pro plan limits, off-peak discount, and concurrency governor."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from cohezion.inference.ollama_pricing import (
    OLLAMA_CLOUD_PRICING,
    OLLAMA_PRO_MAX_CONCURRENCY,
    OLLAMA_PRO_MONTHLY_CREDIT_USD,
    OllamaConcurrencyGovernor,
    calculate_cost_usd,
    get_model_pricing,
    get_ollama_governor,
    is_off_peak,
)


def test_pro_plan_specifications():
    """Verify official Pro plan constants."""
    assert OLLAMA_PRO_MONTHLY_CREDIT_USD == 60.0
    assert OLLAMA_PRO_MAX_CONCURRENCY == 3


def test_all_20_cloud_models_present_in_pricing():
    """Ensure all 20 cloud models are accurately registered in pricing."""
    expected_models = [
        "nemotron-3-super:cloud",
        "gpt-oss:20b-cloud",
        "clef:cloud",
        "gemma4:31b-cloud",
        "glm-5.3-flash:cloud",
        "minimax-m3.1-flash:cloud",
        "gpt-oss:120b-cloud",
        "deepseek-v4-flash:cloud",
        "muse-spark-open:cloud",
        "deepseek-v4.1-flash:cloud",
        "minimax-m2.7:cloud",
        "nemotron-3-ultra:cloud",
        "mistral-large-4:cloud",
        "glm-5.2:cloud",
        "kimi-k2.6:cloud",
        "minimax-m3:cloud",
        "kimi-k2.7-code:cloud",
        "deepseek-v4-pro:cloud",
        "glm-5.3:cloud",
        "kimi-k3:cloud",
    ]
    for model_id in expected_models:
        assert model_id in OLLAMA_CLOUD_PRICING
        pricing = OLLAMA_CLOUD_PRICING[model_id]
        assert pricing.input_per_m > 0
        assert pricing.output_per_m > 0
        assert pricing.context_window >= 131072


def test_off_peak_time_detection():
    """Verify off-peak window:
    - Outside 12:00-18:00 UTC on weekdays (Monday-Friday)
    - All day Saturday and Sunday
    """
    # Wednesday 14:00 UTC (Peak)
    dt_peak = datetime(2026, 10, 21, 14, 0, tzinfo=UTC)
    assert not is_off_peak(dt_peak)

    # Wednesday 10:00 UTC (Off-peak, before 12:00 UTC)
    dt_off_peak_morning = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)
    assert is_off_peak(dt_off_peak_morning)

    # Wednesday 20:00 UTC (Off-peak, after 18:00 UTC)
    dt_off_peak_evening = datetime(2026, 10, 21, 20, 0, tzinfo=UTC)
    assert is_off_peak(dt_off_peak_evening)

    # Saturday 14:00 UTC (Weekend, always off-peak)
    dt_saturday = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)
    assert is_off_peak(dt_saturday)

    # Sunday 03:00 UTC (Weekend, always off-peak)
    dt_sunday = datetime(2026, 10, 25, 3, 0, tzinfo=UTC)
    assert is_off_peak(dt_sunday)


def test_calculate_cost_with_and_without_off_peak_discount():
    """Verify 50% discount applies during off-peak for eligible models."""
    model = "deepseek-v4-pro:cloud"
    in_tokens = 1_000_000
    out_tokens = 1_000_000

    dt_peak = datetime(2026, 10, 21, 14, 0, tzinfo=UTC)
    dt_off_peak = datetime(2026, 10, 21, 20, 0, tzinfo=UTC)

    # Standard peak cost: $1.32 + $3.96 = $5.28
    cost_peak = calculate_cost_usd(model, in_tokens, out_tokens, utc_dt=dt_peak)
    assert pytest.approx(cost_peak, 0.001) == 5.28

    # Off-peak discount cost: 50% of $5.28 = $2.64
    cost_off_peak = calculate_cost_usd(model, in_tokens, out_tokens, utc_dt=dt_off_peak)
    assert pytest.approx(cost_off_peak, 0.001) == 2.64


def test_nemotron_super_ultra_low_cost():
    """Verify nemotron-3-super is ultra-low cost ($0.015 / 1M input)."""
    cost = calculate_cost_usd("nemotron-3-super:cloud", 100_000, 10_000)
    # 100k * (0.015 / 1M) = $0.0015; 10k * (0.60 / 1M) = $0.006; total = $0.0075
    assert pytest.approx(cost, 0.0001) == 0.0075


@pytest.mark.asyncio
async def test_concurrency_governor_enforces_limit():
    """Verify OllamaConcurrencyGovernor strictly limits concurrent slots to max_concurrent."""
    governor = OllamaConcurrencyGovernor(max_concurrent=3)
    active_tracker: list[int] = []

    async def worker(worker_id: int):
        await governor.acquire()
        active_tracker.append(governor.active_requests)
        # Verify active requests never exceed 3
        assert governor.active_requests <= 3
        await asyncio.sleep(0.01)
        governor.release()

    # Launch 10 parallel workers
    await asyncio.gather(*(worker(i) for i in range(10)))

    # All workers served
    assert governor.total_served == 10
    assert governor.active_requests == 0
    assert max(active_tracker) <= 3
