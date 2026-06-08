"""Discriminating tests for flux_specifier_satisfiability (backlog item 145, 2026-06-08).

Structural-before-behavioral (L366) regression guard for the CacheFlux/specifier mismatch: the
vibe specifier reads block.metadata["workflow_id"]/["template_name"], so a provider whose
get_context never populates metadata= can NEVER satisfy it. The guard inspects each provider's
get_context SOURCE for a populated metadata=. CacheFlux -> False (the bug), others -> True.

Each test fails a plausible wrong impl:
  - an impl that checks only "consumer queries provider" (not key-production) marks a no-metadata
    provider True → test_no_meta_provider_cannot_satisfy,
  - an impl that misreads the live providers → test_live_cache_flux_false_history_flux_true.
"""

from __future__ import annotations

from cohezion.flux.provider import FluxProvider
from cohezion.flux.specifier_guard import flux_specifier_satisfiability
from cohezion.flux.types import FluxBlock


class _SetsMeta(FluxProvider):
    async def get_context(self, query, *, top_k=10):
        return [
            FluxBlock(content="x", source="s", relevance_score=1.0, metadata={"workflow_id": "w"})
        ]


class _NoMeta(FluxProvider):
    async def get_context(self, query, *, top_k=10):
        return [FluxBlock(content="x", source="s", relevance_score=1.0)]


def test_satisfiability_by_metadata_production() -> None:
    out = flux_specifier_satisfiability([_SetsMeta, _NoMeta])
    assert out == {"_SetsMeta": True, "_NoMeta": False}


def test_no_meta_provider_cannot_satisfy() -> None:
    # DISCRIMINATING: a provider that never sets metadata= cannot satisfy the specifier.
    assert flux_specifier_satisfiability([_NoMeta]) == {"_NoMeta": False}


def test_live_cache_flux_false_history_flux_true() -> None:
    # The exact 2026-06-07 bug: CacheFlux blocks carry empty metadata → can't satisfy the specifier.
    out = flux_specifier_satisfiability()
    assert out.get("CacheFlux") is False
    assert out.get("HistoryFlux") is True
