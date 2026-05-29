"""Token usage tracking with asymmetric cost model.

Not all tokens are equal:
  Local silicon (NPU/iGPU/CPU): $0.00 per token — track for quality budget
  Cloud (Claude/Gemini):        real $ per token — track for cost budget

A 10k-token compound loop entirely on NPU/iGPU = $0.00.
Same loop on Sonnet = $0.18. Over 1000 cycles/month = $180 saved.

Cloud token pricing (as of 2026):
  Haiku 4.5:  $0.80/M input, $4.00/M output
  Sonnet 4.6: $3.00/M input, $15.00/M output
  Opus 4.7:   $15.00/M input, $75.00/M output
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime


logger = logging.getLogger(__name__)

# Cloud pricing per 1M tokens (input, output) — updated 2026
_CLOUD_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
    "gemini-flash": (0.075, 0.30),
    "gemini-pro": (1.25, 5.00),
    "default_cloud": (3.00, 15.00),  # conservative default
}

# Local silicon — $0 API cost
_LOCAL_MODELS = frozenset(
    {
        "llama3.2-1b-FLM",
        "Gemma-4-E4B-it-GGUF",
        "Gemma-4-E2B-it-GGUF",
        "Gemma-4-26B-A4B-it-GGUF",
        "Gemma-4-31B-it-GGUF",
        "DeepSeek-Qwen3-8B-GGUF",
        "Qwen3-0.6B-GGUF",
        "Qwen3-8B-GGUF",
    }
)


@dataclass
class TokenUsageRecord:
    """Track asymmetric token costs across local and cloud tiers.

    Usage
    -----
    record = TokenUsageRecord()
    record.add_local(1500, model="llama3.2-1b-FLM")  # NPU — free
    record.add_cloud(200, 50, model="claude-sonnet-4-6")  # cloud — costs real $
    print(record.cloud_savings_usd)  # estimated savings vs cloud-only baseline
    """

    local_tokens: int = 0
    cloud_tokens_input: int = 0
    cloud_tokens_output: int = 0
    cache_hits: int = 0
    cache_tokens_saved: int = 0
    session_start: datetime = field(default_factory=lambda: datetime.now(UTC))
    _cost_by_model: dict[str, float] = field(default_factory=dict, repr=False)

    def add_local(self, tokens: int, model: str = "") -> None:
        """Record local silicon token usage (no cost)."""
        self.local_tokens += tokens
        logger.debug("Local tokens: +%d (model=%s, total=%d)", tokens, model, self.local_tokens)

    def add_cloud(
        self, input_tokens: int, output_tokens: int, model: str = "default_cloud"
    ) -> float:
        """Record cloud token usage and return cost in USD."""
        pricing = _CLOUD_PRICING.get(model, _CLOUD_PRICING["default_cloud"])
        cost = input_tokens / 1_000_000 * pricing[0] + output_tokens / 1_000_000 * pricing[1]
        self.cloud_tokens_input += input_tokens
        self.cloud_tokens_output += output_tokens
        self._cost_by_model[model] = self._cost_by_model.get(model, 0.0) + cost
        logger.debug(
            "Cloud tokens: +%d/%d (model=%s, cost=$%.6f)", input_tokens, output_tokens, model, cost
        )
        return cost

    def add_cache_hit(self, tokens_saved: int) -> None:
        """Record a semantic cache hit that avoided a cloud call."""
        self.cache_hits += 1
        self.cache_tokens_saved += tokens_saved

    @property
    def cloud_cost_usd(self) -> float:
        """Total cloud spend in USD this session."""
        return sum(self._cost_by_model.values())

    @property
    def cloud_savings_usd(self) -> float:
        """Estimated savings from local routing vs. cloud-only baseline (Sonnet rate).

        Assumes every local token would have cost Sonnet rates if routed to cloud.
        """
        sonnet_input_rate = 3.00 / 1_000_000
        return self.local_tokens * sonnet_input_rate

    @property
    def total_tokens(self) -> int:
        return self.local_tokens + self.cloud_tokens_input + self.cloud_tokens_output

    @property
    def local_fraction(self) -> float:
        """Fraction of total tokens handled by free local silicon."""
        total = self.total_tokens
        if total == 0:
            return 0.0
        return self.local_tokens / total

    def is_local_model(self, model_id: str) -> bool:
        """Return True if model_id is known to be a local (free) model."""
        return model_id in _LOCAL_MODELS or any(
            local in model_id for local in ("FLM", "GGUF", "llama", "gemma")
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "local_tokens": self.local_tokens,
            "cloud_tokens_input": self.cloud_tokens_input,
            "cloud_tokens_output": self.cloud_tokens_output,
            "cloud_cost_usd": round(self.cloud_cost_usd, 6),
            "cloud_savings_usd": round(self.cloud_savings_usd, 4),
            "cache_hits": self.cache_hits,
            "cache_tokens_saved": self.cache_tokens_saved,
            "local_fraction": round(self.local_fraction, 3),
            "cost_by_model": dict(self._cost_by_model),
        }

    def telegram_report(self) -> str:
        """Format token usage for Telegram notification."""
        return (
            f"<b>Token Report</b>\n"
            f"Local (free): {self.local_tokens:,} tokens\n"
            f"Cloud: {self.cloud_tokens_input + self.cloud_tokens_output:,} tokens "
            f"(${self.cloud_cost_usd:.4f})\n"
            f"Cache hits: {self.cache_hits} "
            f"(saved ~{self.cache_tokens_saved:,} tokens)\n"
            f"Savings vs cloud-only: <b>${self.cloud_savings_usd:.2f}</b> "
            f"({self.local_fraction:.0%} local)"
        )
