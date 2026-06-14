"""Item 145: FLUX provider↔consumer metadata-contract guard — TDD red→green (2026-06-08).

Structural-before-behavioral check (L366): for the vibe specifier consumer that reads
``block.metadata["workflow_id"]`` and ``block.metadata["template_name"]``, determine
which registered FluxProvider subclasses CAN ever satisfy it by inspecting whether
their ``get_context`` source constructs ``FluxBlock(metadata=…)``.

  - CacheFlux → False: ``FluxBlock(content=…, source=…, relevance_score=…)`` —
    no ``metadata=`` kwarg; metadata is always empty default → cannot satisfy specifier
  - HistoryFlux → True: ``FluxBlock(…, metadata=entry.get("metadata", {}), …)`` —
    passes through the recorded metadata → CAN carry workflow_id/template_name

Catches the exact 2026-06-07 bug at harness time instead of by manual tracing.
NON-FABRICATED: derived from reading each provider's actual ``get_context`` source.

Discriminating tests — each kills a plausible wrong implementation:

  1. CacheFlux → False  (PRIMARY DISC.: kills "assume all providers set metadata")
  2. HistoryFlux → True (kills "return False for all providers")
  3. Guard reads source, not runtime behavior  (kills "instantiate and call get_context")
  4. Returns dict keyed by provider name      (kills "return a bool not a dict")
  5. Injected providers → deterministic       (kills "scans live production list")
"""

from __future__ import annotations

from cohezion.flux.providers.cache_flux import CacheFlux
from cohezion.flux.providers.history_flux import HistoryFlux
from cohezion.flux.structural_guard import flux_provider_metadata_guard


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cache_flux_cannot_satisfy_specifier() -> None:
    """CacheFlux does NOT set metadata= in FluxBlock → guard returns False.

    PRIMARY DISCRIMINATOR: kills an impl that assumes all registered providers
    set metadata (e.g. returns True for everything).
    """
    result = flux_provider_metadata_guard({"cache_flux": CacheFlux})
    assert result["cache_flux"] is False, (
        f"CacheFlux (no metadata=) must be False; got {result['cache_flux']}"
    )


def test_history_flux_can_satisfy_specifier() -> None:
    """HistoryFlux DOES set metadata= in FluxBlock → guard returns True.

    Kills an impl that returns False for all providers (over-conservative).
    """
    result = flux_provider_metadata_guard({"history_flux": HistoryFlux})
    assert result["history_flux"] is True, (
        f"HistoryFlux (sets metadata=) must be True; got {result['history_flux']}"
    )


def test_guard_reads_source_not_runtime() -> None:
    """Guard uses source inspection, not live instantiation.

    Verifies the guard does not try to instantiate CacheFlux (which requires
    a semantic_cache argument) or call async get_context at import time.
    Passes if no exception is raised — no asyncio.run, no instantiation needed.
    """
    # CacheFlux requires a semantic_cache to function at runtime.
    # The guard must work without instantiating it.
    result = flux_provider_metadata_guard({"cache_flux": CacheFlux, "history_flux": HistoryFlux})
    assert "cache_flux" in result
    assert "history_flux" in result


def test_result_is_dict_keyed_by_provider_name() -> None:
    """Result is a dict mapping provider name → bool, not a bare bool.

    Kills an impl that returns a single boolean instead of per-provider dict.
    """
    result = flux_provider_metadata_guard({"cache_flux": CacheFlux})
    assert isinstance(result, dict), f"result must be dict; got {type(result)}"
    assert "cache_flux" in result, f"key 'cache_flux' missing; got {result}"
    assert isinstance(result["cache_flux"], bool), (
        f"value must be bool; got {type(result['cache_flux'])}"
    )


def test_injected_providers_deterministic() -> None:
    """With only the two known providers, result is fully deterministic.

    Kills an impl that scans a live production registry and picks up random providers.
    """
    result = flux_provider_metadata_guard({"cache_flux": CacheFlux, "history_flux": HistoryFlux})
    assert set(result.keys()) == {"cache_flux", "history_flux"}, (
        f"must return only injected providers; got {set(result.keys())}"
    )
    assert result == {"cache_flux": False, "history_flux": True}, f"wrong values; got {result}"
