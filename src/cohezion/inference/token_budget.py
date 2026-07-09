"""Session-level token budget tracking for Cohezion inference.

Consumed by cohezion.compound.local_inference to aggregate local vs. cloud
token spend across a single process lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass


# Reference pricing for cloud savings estimate: claude-sonnet-4-6
_CLOUD_INPUT_PER_TOKEN: float = 3.0 / 1_000_000  # $3/M input tokens
_CLOUD_OUTPUT_PER_TOKEN: float = 15.0 / 1_000_000  # $15/M output tokens


@dataclass
class TokenUsageRecord:
    """Aggregate token usage for a compound loop session.

    local_tokens       — tokens handled free on local silicon (NPU/iGPU/CPU)
    cloud_cost_usd     — cumulative cost of metered cloud calls
    cloud_savings_usd  — estimated savings: what local tokens would have cost on cloud
    """

    local_tokens: int = 0
    cloud_cost_usd: float = 0.0
    cloud_savings_usd: float = 0.0

    def add_local(self, total_tokens: int, *, model: str = "") -> None:
        """Record locally-handled tokens and accumulate savings estimate."""
        self.local_tokens += total_tokens
        # Estimate savings using average of input + output cloud pricing.
        avg_price = (_CLOUD_INPUT_PER_TOKEN + _CLOUD_OUTPUT_PER_TOKEN) / 2
        self.cloud_savings_usd += total_tokens * avg_price

    def add_cloud(self, input_tokens: int, output_tokens: int, *, model: str = "") -> float:
        """Record a metered cloud call and return the USD cost."""
        cost = input_tokens * _CLOUD_INPUT_PER_TOKEN + output_tokens * _CLOUD_OUTPUT_PER_TOKEN
        self.cloud_cost_usd += cost
        return cost
