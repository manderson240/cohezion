"""Item 93: Register Higgs-Audio as a research-only AUDIO_TTS tier.

ModelEntry `research_only=True` + `for_product_task()` guard — the entry appears
in `for_task(AUDIO_TTS)` but is filtered from `for_product_task(AUDIO_TTS)`.

Discriminating tests:
  1. PRIMARY DISC.: `for_product_task(AUDIO_TTS)` does NOT return Higgs-Audio even
     when `for_task(AUDIO_TTS)` does (kills impl that does no research_only filtering).
  2. `for_task(AUDIO_TTS)` DOES return Higgs-Audio (entry is registered).
  3. Higgs-Audio entry has `research_only=True` (guard attribute is set correctly).
  4. Non-research-only AUDIO_TTS entries ARE returned by `for_product_task(AUDIO_TTS)`
     (kills an impl that filters ALL entries, not just research_only ones).
  5. Higgs-Audio entry has `verified_working=False` (serving proof not yet run).
"""

from __future__ import annotations

import copy

from cohezion.inference.registry import FleetRegistry, Task, get_registry

HIGGS_MODEL_ID = "Higgs-Audio-v3-TTS-4B"


def _isolated_registry() -> FleetRegistry:
    """Deep copy of the module singleton so mutations don't pollute other tests."""
    return FleetRegistry(models=copy.deepcopy(get_registry().models))


class TestHiggsAudioProductGuard:
    """PRIMARY DISC.: for_product_task must filter research_only entries."""

    def test_product_task_excludes_higgs_audio(self) -> None:
        """PRIMARY DISC.: for_product_task(AUDIO_TTS) must NOT include Higgs-Audio.

        Kills an impl that simply aliases for_product_task to for_task
        (no filtering), or one that misses the research_only attribute entirely.
        """
        reg = _isolated_registry()
        product_ids = {e.model_id for e in reg.for_product_task(Task.AUDIO_TTS)}
        assert HIGGS_MODEL_ID not in product_ids, (
            f"for_product_task(AUDIO_TTS) must not return Higgs-Audio "
            f"(research-only), but got: {product_ids}"
        )

    def test_for_task_includes_higgs_audio(self) -> None:
        """for_task(AUDIO_TTS) MUST include Higgs-Audio — it is registered.

        Kills an impl that never adds the entry (registration guard).
        """
        reg = _isolated_registry()
        all_ids = {e.model_id for e in reg.for_task(Task.AUDIO_TTS)}
        assert HIGGS_MODEL_ID in all_ids, (
            f"for_task(AUDIO_TTS) must include Higgs-Audio, got: {all_ids}"
        )

    def test_higgs_entry_research_only_flag(self) -> None:
        """The Higgs-Audio ModelEntry must have research_only=True.

        Kills an impl that adds the entry but forgets to set research_only,
        or sets it to False (would pass through the product guard).
        """
        reg = _isolated_registry()
        entry = reg.models.get(HIGGS_MODEL_ID)
        assert entry is not None, f"{HIGGS_MODEL_ID} must exist in registry.models"
        assert entry.research_only is True, (
            f"{HIGGS_MODEL_ID}: research_only must be True, got {entry.research_only}"
        )

    def test_non_research_entries_pass_product_guard(self) -> None:
        """for_product_task(AUDIO_TTS) must still return non-research-only entries.

        Kills an impl that filters ALL AUDIO_TTS entries, not just research_only.
        CosmoNarrator and kokoro-v1 must survive the filter.
        """
        reg = _isolated_registry()
        product_entries = reg.for_product_task(Task.AUDIO_TTS)
        non_higgs = [e for e in product_entries if e.model_id != HIGGS_MODEL_ID]
        assert non_higgs, (
            "for_product_task(AUDIO_TTS) must return non-research entries "
            "(CosmoNarrator-PocketTTS, kokoro-v1); got empty list"
        )

    def test_higgs_entry_unverified_working(self) -> None:
        """Higgs-Audio must have verified_working=False (serving proof not yet run).

        Kills an impl that sets verified_working=True without a real transformers
        serving smoke (behaviour-change gated behind K1/rule-5 + lanes-up window).
        """
        reg = _isolated_registry()
        entry = reg.models.get(HIGGS_MODEL_ID)
        assert entry is not None, f"{HIGGS_MODEL_ID} must exist in registry.models"
        assert entry.verified_working is False, (
            f"{HIGGS_MODEL_ID}: verified_working must be False until TTS smoke passes"
        )
