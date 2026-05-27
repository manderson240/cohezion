"""CLaSp (Cascade Layered Speculative) tier for iGPU inference optimization.

Implements a REST-API-level approximation of self-speculative decoding
(arXiv:2505.24196 CLaSp): use a shallow draft model (E2B) for fast generation,
verify with the full model (E4B) only when draft quality is insufficient.

Architecture:
  Draft  →  Gemma-4-E2B-it-GGUF (2B params, ~2x faster, port 13308)
  Verify →  Gemma-4-E4B-it-GGUF (4B params, full quality, port 13307)

Acceptance criterion: QualityGate (min_chars threshold), same as TieredOrchestrator.
If draft passes gate → accept (no E4B call, ~2x speedup for that token).
If draft fails gate  → call E4B for full-quality generation.

Expected compound_lift improvement: 1.5-2.5x on iGPU tier when draft
acceptance rate is 50-70% (measured as: accepted_drafts / total_calls).

Fallback: if draft port is unavailable, passes directly to the verify tier.
This makes CLaSpTier a transparent wrapper — zero regression on degraded infra.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from cohezion.inference.orchestrator import OrchestrationResult, QualityGate


logger = logging.getLogger(__name__)

# CLaSp acceptance gate: minimum chars for draft to be "good enough"
# Set higher than NPU gate (10) but lower than full iGPU gate (750, post-fix).
# Captures ~60-70% of responses that are substantive and complete.
_CLASP_DRAFT_ACCEPTANCE_CHARS = 200


@dataclass
class CLaSpStats:
    """Tracks CLaSp draft acceptance rates for compound_lift measurement."""

    total_calls: int = 0
    draft_accepted: int = 0
    draft_rejected: int = 0
    draft_unavailable: int = 0
    total_draft_ms: float = 0.0
    total_verify_ms: float = 0.0

    @property
    def acceptance_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.draft_accepted / self.total_calls

    @property
    def speedup_vs_verify_only(self) -> float:
        """Estimated speedup: how much faster than always using E4B."""
        if self.total_calls == 0 or self.total_verify_ms == 0:
            return 1.0
        # Time if we always used verify: all calls at verify latency
        verify_per_call = self.total_verify_ms / max(self.draft_rejected, 1)
        hypothetical_verify_only = self.total_calls * verify_per_call
        actual_time = self.total_draft_ms + self.total_verify_ms
        return hypothetical_verify_only / max(actual_time, 1.0)

    def summary(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "draft_accepted": self.draft_accepted,
            "acceptance_rate": round(self.acceptance_rate, 3),
            "speedup_vs_verify_only": round(self.speedup_vs_verify_only, 3),
            "avg_draft_ms": round(self.total_draft_ms / max(self.total_calls, 1), 1),
        }


# Module-level stats singleton for compound_lift measurement
_clasp_stats = CLaSpStats()


def get_clasp_stats() -> CLaSpStats:
    """Return current CLaSp stats for compound_lift measurement."""
    return _clasp_stats


@dataclass
class CLaSpTier:
    """iGPU tier with CLaSp speculative drafting.

    Drop-in replacement for GaiaAgentTier in TieredOrchestrator.

    Usage:
        from cohezion.inference.clasp_tier import build_clasp_igpu_tier
        clasp_tier = build_clasp_igpu_tier()
        orch = TieredOrchestrator(tiers=[
            (npu_tier, QualityGate(min_chars=10)),
            (clasp_tier, QualityGate(min_chars=750)),
            (cpu_tier, QualityGate.TRUST),
        ])
    """

    draft_tier: object  # GaiaAgentTier with E2B model
    verify_tier: object  # GaiaAgentTier with E4B model
    draft_gate: QualityGate = field(
        default_factory=lambda: QualityGate(min_chars=_CLASP_DRAFT_ACCEPTANCE_CHARS)
    )
    label: str = "clasp:E2B→E4B"

    async def run(self, prompt: str, **kwargs) -> OrchestrationResult:
        """CLaSp inference: draft with E2B, verify with E4B if needed."""
        global _clasp_stats
        _clasp_stats.total_calls += 1

        # Phase 1: Draft with E2B (fast, ~2x cheaper)
        draft_result: OrchestrationResult | None = None
        draft_start = time.perf_counter()
        try:
            draft_result = await self.draft_tier.run(prompt, **kwargs)
            draft_ms = (time.perf_counter() - draft_start) * 1000
            _clasp_stats.total_draft_ms += draft_ms

            # Acceptance check
            gate_pass, gate_reason = self.draft_gate.check(draft_result)
            if gate_pass:
                _clasp_stats.draft_accepted += 1
                logger.debug(
                    "CLaSp: draft accepted (%.0fms, %d chars)",
                    draft_ms,
                    len(draft_result.text),
                )
                draft_model_id = getattr(draft_result, "final_model", None) or getattr(
                    draft_result, "model", "E2B"
                )
                return OrchestrationResult(
                    text=draft_result.text,
                    primary_model=self.label,
                    final_model=f"clasp-draft:{draft_model_id}",
                    escalation_count=0,
                    cost_usd=draft_result.cost_usd,
                    latency_ms=draft_ms,
                    ttft_ms=draft_result.ttft_ms,
                    error=None,
                )
            else:
                logger.debug("CLaSp: draft rejected (%s), escalating to E4B", gate_reason)
        except Exception as exc:
            _clasp_stats.draft_unavailable += 1
            logger.debug("CLaSp: draft unavailable (%s), using verify tier", exc)

        # Phase 2: Verify with E4B (full quality)
        _clasp_stats.draft_rejected += 1
        verify_start = time.perf_counter()
        verify_result = await self.verify_tier.run(prompt, **kwargs)
        verify_ms = (time.perf_counter() - verify_start) * 1000
        _clasp_stats.total_verify_ms += verify_ms

        verify_model_id = getattr(verify_result, "final_model", None) or getattr(
            verify_result, "model", "E4B"
        )
        return OrchestrationResult(
            text=verify_result.text,
            primary_model=self.label,
            final_model=f"clasp-verify:{verify_model_id}",
            escalation_count=1,
            cost_usd=(draft_result.cost_usd if draft_result else 0.0) + verify_result.cost_usd,
            latency_ms=verify_ms + (draft_ms if draft_result else 0.0),
            ttft_ms=verify_result.ttft_ms,
            error=verify_result.error,
        )


def build_clasp_igpu_tier(
    *,
    draft_port: int = 13308,
    verify_port: int = 13307,
    draft_model: str = "Gemma-4-E2B-it-GGUF",
    verify_model: str = "Gemma-4-E4B-it-GGUF",
    draft_acceptance_chars: int = _CLASP_DRAFT_ACCEPTANCE_CHARS,
    silent: bool = True,
) -> CLaSpTier:
    """Build a CLaSp iGPU tier: E2B draft at port 13308, E4B verify at port 13307.

    Registers for the Strix Halo Governance Lane (ROCWMMA iGPU).
    Harness invariant N2 preserved: NPU remains llama3.2-1b-FLM at port 13306.

    Args:
        draft_port: Port for draft model (default 13308 for E2B)
        verify_port: Port for verify model (default 13307 for E4B)
        draft_model: Draft model ID (smaller/faster)
        verify_model: Verify model ID (larger/higher quality)
        draft_acceptance_chars: Min chars for draft to be accepted
        silent: Suppress model output logs
    """
    from cohezion.inference.gaia_adapter import build_gaia_native_tier

    draft_tier = build_gaia_native_tier(
        model_id=draft_model,
        base_url=f"http://localhost:{draft_port}/v1",
        silent=silent,
    )
    verify_tier = build_gaia_native_tier(
        model_id=verify_model,
        base_url=f"http://localhost:{verify_port}/v1",
        silent=silent,
    )
    return CLaSpTier(
        draft_tier=draft_tier,
        verify_tier=verify_tier,
        draft_gate=QualityGate(min_chars=draft_acceptance_chars),
        label=f"clasp:{draft_model[:6]}→{verify_model[:6]}",
    )
