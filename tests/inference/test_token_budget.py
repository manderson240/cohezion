"""Tests for cohezion.inference.token_budget.TokenUsageRecord."""

from __future__ import annotations

from cohezion.inference.token_budget import TokenUsageRecord


class TestTokenUsageRecord:
    def test_initial_state_is_zero(self):
        r = TokenUsageRecord()
        assert r.local_tokens == 0
        assert r.cloud_cost_usd == 0.0
        assert r.cloud_savings_usd == 0.0

    def test_add_local_accumulates_tokens(self):
        r = TokenUsageRecord()
        r.add_local(100)
        r.add_local(50)
        assert r.local_tokens == 150

    def test_add_local_records_savings_estimate(self):
        r = TokenUsageRecord()
        r.add_local(1_000_000)  # 1M tokens at cloud pricing
        # savings should be positive and > 0
        assert r.cloud_savings_usd > 0

    def test_add_cloud_returns_cost(self):
        r = TokenUsageRecord()
        cost = r.add_cloud(1_000_000, 1_000_000)
        # $3/M input + $15/M output = $18 for 1M each
        assert abs(cost - 18.0) < 0.01

    def test_add_cloud_accumulates_cost(self):
        r = TokenUsageRecord()
        r.add_cloud(1_000_000, 0)
        r.add_cloud(0, 1_000_000)
        # $3/M input + $15/M output = $18 total
        assert abs(r.cloud_cost_usd - 18.0) < 0.01

    def test_add_local_does_not_affect_cloud_cost(self):
        r = TokenUsageRecord()
        r.add_local(10_000)
        assert r.cloud_cost_usd == 0.0

    def test_add_cloud_does_not_affect_local_tokens(self):
        r = TokenUsageRecord()
        r.add_cloud(1000, 1000)
        assert r.local_tokens == 0
