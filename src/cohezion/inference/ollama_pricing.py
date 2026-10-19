"""Ollama Cloud Pricing & Pro Plan Specifications.

Authoritative reference:
- https://ollama.com/pricing
- https://docs.ollama.com/faq

Ollama Pro Plan Key Details:
- Cost: $20 / month
- Included Usage Credits: $60.00 / month (resets monthly; no rollover; pay-as-you-go beyond)
- Concurrency Limit: 3 concurrent requests (Free: 1, Pro: 3, Max: 10)
- Off-Peak Window: Outside 12:00-18:00 UTC on weekdays (Monday-Friday), and all day Saturday & Sunday (UTC).
- Off-Peak Discount: 50% discount on input and output tokens for eligible models (e.g. DeepSeek v4 series).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


# Plan limits
OLLAMA_PRO_MONTHLY_CREDIT_USD: float = 60.0
OLLAMA_PRO_SUBSCRIPTION_USD: float = 20.0
OLLAMA_PRO_MAX_CONCURRENCY: int = 3
OLLAMA_FREE_MAX_CONCURRENCY: int = 1
OLLAMA_MAX_PLAN_CONCURRENCY: int = 10


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Pricing rates per 1,000,000 (1M) tokens in USD."""

    model_id: str
    input_per_m: float
    output_per_m: float
    cached_input_per_m: float | None = None
    has_off_peak_discount: bool = False
    context_window: int = 131072

    @property
    def input_per_token(self) -> float:
        return self.input_per_m / 1_000_000.0

    @property
    def output_per_token(self) -> float:
        return self.output_per_m / 1_000_000.0

    @property
    def cached_input_per_token(self) -> float:
        rate = self.cached_input_per_m if self.cached_input_per_m is not None else self.input_per_m
        return rate / 1_000_000.0


# Official Ollama Cloud Pricing Matrix (USD per 1M tokens)
OLLAMA_CLOUD_PRICING: dict[str, ModelPricing] = {
    # Ultra-low cost background swarms & sentinels
    "nemotron-3-super:cloud": ModelPricing(
        model_id="nemotron-3-super:cloud",
        input_per_m=0.015,
        output_per_m=0.60,
        cached_input_per_m=0.0075,
        context_window=262144,
    ),
    "gpt-oss:20b-cloud": ModelPricing(
        model_id="gpt-oss:20b-cloud",
        input_per_m=0.07,
        output_per_m=0.30,
        cached_input_per_m=0.035,
        context_window=131072,
    ),
    "clef:cloud": ModelPricing(
        model_id="clef:cloud",
        input_per_m=0.10,
        output_per_m=0.40,
        cached_input_per_m=0.05,
        context_window=131072,
    ),
    "gemma4:31b-cloud": ModelPricing(
        model_id="gemma4:31b-cloud",
        input_per_m=0.14,
        output_per_m=0.40,
        cached_input_per_m=0.07,
        context_window=262144,
    ),
    "glm-5.3-flash:cloud": ModelPricing(
        model_id="glm-5.3-flash:cloud",
        input_per_m=0.15,
        output_per_m=0.50,
        cached_input_per_m=0.075,
        context_window=1048576,
    ),
    "minimax-m3.1-flash:cloud": ModelPricing(
        model_id="minimax-m3.1-flash:cloud",
        input_per_m=0.15,
        output_per_m=0.60,
        cached_input_per_m=0.075,
        context_window=1048576,
    ),
    "gpt-oss:120b-cloud": ModelPricing(
        model_id="gpt-oss:120b-cloud",
        input_per_m=0.15,
        output_per_m=0.60,
        cached_input_per_m=0.075,
        context_window=131072,
    ),
    "deepseek-v4-flash:cloud": ModelPricing(
        model_id="deepseek-v4-flash:cloud",
        input_per_m=0.15,
        output_per_m=0.60,
        cached_input_per_m=0.075,
        context_window=131072,
    ),
    "muse-spark-open:cloud": ModelPricing(
        model_id="muse-spark-open:cloud",
        input_per_m=0.20,
        output_per_m=0.80,
        cached_input_per_m=0.10,
        context_window=131072,
    ),
    # Mid-Tier High-Efficiency Reasoning & Coding
    "deepseek-v4.1-flash:cloud": ModelPricing(
        model_id="deepseek-v4.1-flash:cloud",
        input_per_m=0.30,
        output_per_m=1.20,
        cached_input_per_m=0.075,
        has_off_peak_discount=True,  # 50% discount off-peak: $0.15 / $0.60
        context_window=1048576,
    ),
    "minimax-m2.7:cloud": ModelPricing(
        model_id="minimax-m2.7:cloud",
        input_per_m=0.30,
        output_per_m=1.20,
        cached_input_per_m=0.15,
        context_window=262144,
    ),
    "nemotron-3-ultra:cloud": ModelPricing(
        model_id="nemotron-3-ultra:cloud",
        input_per_m=0.40,
        output_per_m=1.60,
        cached_input_per_m=0.20,
        context_window=262144,
    ),
    "mistral-large-4:cloud": ModelPricing(
        model_id="mistral-large-4:cloud",
        input_per_m=0.68,
        output_per_m=2.09,
        cached_input_per_m=0.34,
        context_window=1048576,
    ),
    "glm-5.2:cloud": ModelPricing(
        model_id="glm-5.2:cloud",
        input_per_m=0.70,
        output_per_m=2.40,
        cached_input_per_m=0.35,
        context_window=1048576,
    ),
    "kimi-k2.6:cloud": ModelPricing(
        model_id="kimi-k2.6:cloud",
        input_per_m=0.80,
        output_per_m=3.20,
        cached_input_per_m=0.40,
        context_window=262144,
    ),
    "minimax-m3:cloud": ModelPricing(
        model_id="minimax-m3:cloud",
        input_per_m=0.80,
        output_per_m=3.20,
        cached_input_per_m=0.40,
        context_window=1048576,
    ),
    "kimi-k2.7-code:cloud": ModelPricing(
        model_id="kimi-k2.7-code:cloud",
        input_per_m=0.95,
        output_per_m=4.00,
        cached_input_per_m=0.475,
        context_window=262144,
    ),
    # Flagship Frontier Reasoning & Coding
    "deepseek-v4-pro:cloud": ModelPricing(
        model_id="deepseek-v4-pro:cloud",
        input_per_m=1.32,
        output_per_m=3.96,
        cached_input_per_m=0.33,
        has_off_peak_discount=True,  # 50% discount off-peak: $0.66 / $1.98
        context_window=524288,
    ),
    "glm-5.3:cloud": ModelPricing(
        model_id="glm-5.3:cloud",
        input_per_m=1.40,
        output_per_m=4.40,
        cached_input_per_m=0.70,
        context_window=1048576,
    ),
    "kimi-k3:cloud": ModelPricing(
        model_id="kimi-k3:cloud",
        input_per_m=3.00,
        output_per_m=15.00,
        cached_input_per_m=1.50,
        context_window=1048576,
    ),
}


def is_off_peak(utc_dt: datetime | None = None) -> bool:
    """Determine if a given time is in the Ollama Cloud off-peak discount window.

    Window:
    - Outside 12:00-18:00 UTC on weekdays (Monday=0 ... Friday=4)
    - All day Saturday (5) and Sunday (6) UTC
    """
    if utc_dt is None:
        utc_dt = datetime.now(UTC)
    elif utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC)
    else:
        utc_dt = utc_dt.astimezone(UTC)

    # Weekends are all off-peak
    if utc_dt.weekday() in (5, 6):
        return True

    # Weekdays: off-peak outside 12:00 - 18:00 UTC
    return not (12 <= utc_dt.hour < 18)


def get_model_pricing(model_name: str) -> ModelPricing:
    """Lookup pricing record for an Ollama Cloud model, falling back to a sensible default."""
    # Normalize model tag
    tag = model_name if ":cloud" in model_name else f"{model_name}:cloud"
    if tag in OLLAMA_CLOUD_PRICING:
        return OLLAMA_CLOUD_PRICING[tag]

    # Look for partial matches
    for key, pricing in OLLAMA_CLOUD_PRICING.items():
        if key.startswith(model_name) or model_name.startswith(key.split(":")[0]):
            return pricing

    # Conservative default ($0.50 input / $1.50 output per 1M)
    return ModelPricing(
        model_id=tag,
        input_per_m=0.50,
        output_per_m=1.50,
        cached_input_per_m=0.25,
        context_window=131072,
    )


def calculate_cost_usd(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    *,
    is_cached: bool = False,
    utc_dt: datetime | None = None,
) -> float:
    """Calculate exact USD cost for an inference call with off-peak discounting."""
    pricing = get_model_pricing(model_name)
    off_peak = is_off_peak(utc_dt)
    discount = 0.5 if (off_peak and pricing.has_off_peak_discount) else 1.0

    in_rate = pricing.cached_input_per_token if is_cached else pricing.input_per_token
    out_rate = pricing.output_per_token

    return (input_tokens * in_rate + output_tokens * out_rate) * discount


class OllamaConcurrencyGovernor:
    """Enforces Ollama Pro plan concurrency limit (3 concurrent requests) with FIFO queuing."""

    def __init__(self, max_concurrent: int = OLLAMA_PRO_MAX_CONCURRENCY) -> None:
        self.max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None
        self._active_requests: int = 0
        self._queued_requests: int = 0
        self._total_served: int = 0

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    @property
    def active_requests(self) -> int:
        return self._active_requests

    @property
    def queued_requests(self) -> int:
        return self._queued_requests

    @property
    def total_served(self) -> int:
        return self._total_served

    async def acquire(self) -> None:
        """Acquire a slot under the concurrency limit, queuing if full."""
        self._queued_requests += 1
        try:
            await self.semaphore.acquire()
        finally:
            self._queued_requests -= 1
        self._active_requests += 1

    def release(self) -> None:
        """Release an acquired concurrency slot."""
        if self._active_requests > 0:
            self._active_requests -= 1
            self._total_served += 1
        self.semaphore.release()


# Global singleton governor initialized with Pro plan limit
_GLOBAL_GOVERNOR: OllamaConcurrencyGovernor | None = None


def get_ollama_governor() -> OllamaConcurrencyGovernor:
    """Get the process-wide Ollama concurrency governor."""
    global _GLOBAL_GOVERNOR
    if _GLOBAL_GOVERNOR is None:
        _GLOBAL_GOVERNOR = OllamaConcurrencyGovernor(max_concurrent=OLLAMA_PRO_MAX_CONCURRENCY)
    return _GLOBAL_GOVERNOR
