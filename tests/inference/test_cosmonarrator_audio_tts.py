"""Item 85: Wire CosmoNarrator as the AUDIO_TTS seed (TDD red→green).

`for_task(Task.AUDIO_TTS)` must return the CosmoNarrator/PocketTTS ModelEntry with
`verified_working=False` — the same "registered-unverified" pattern as items
4/19/21/23/28.  The serving SMOKE (narrator emits a non-empty audio artifact)
is the verification gate; registration alone changes no behavior.

Each test fails a plausible wrong impl:
  - entry absent → test_audio_tts_registered
  - entry has wrong verified_working flag (True) → test_cosmonarrator_unverified
  - entry is on wrong lane or task → test_cosmonarrator_task_affinity / test_cosmonarrator_lane
  - registration broke existing routing → test_registration_additive_general / _vision
"""

from __future__ import annotations

import copy

from cohezion.inference.registry import FleetRegistry, Lane, Task, get_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _isolated_registry() -> FleetRegistry:
    """Deep copy of the module singleton so mutations don't pollute other tests."""
    return FleetRegistry(models=copy.deepcopy(get_registry().models))


# ---------------------------------------------------------------------------
# Core correctness tests
# ---------------------------------------------------------------------------


class TestCosmoNarratorRegistered:
    """for_task(AUDIO_TTS) returns the CosmoNarrator/PocketTTS entry."""

    def test_audio_tts_registered(self) -> None:
        """AUDIO_TTS must now have ≥1 registered ModelEntry."""
        reg = _isolated_registry()
        entries = reg.for_task(Task.AUDIO_TTS)
        assert entries, "for_task(AUDIO_TTS) must return ≥1 entry after item 85"

    def test_cosmonarrator_model_id(self) -> None:
        """The registered model_id must reference PocketTTS or CosmoNarrator."""
        reg = _isolated_registry()
        entries = reg.for_task(Task.AUDIO_TTS)
        assert entries, "need ≥1 entry"
        model_ids = [e.model_id.lower() for e in entries]
        assert any("pockettts" in mid or "cosmo" in mid or "tts" in mid for mid in model_ids), (
            f"model_id must reference PocketTTS/CosmoNarrator, got {[e.model_id for e in entries]}"
        )

    def test_cosmonarrator_task_affinity(self) -> None:
        """The entry's task_affinity must include AUDIO_TTS."""
        reg = _isolated_registry()
        for entry in reg.for_task(Task.AUDIO_TTS):
            assert Task.AUDIO_TTS in entry.task_affinity, (
                f"{entry.model_id}: AUDIO_TTS missing from task_affinity {entry.task_affinity}"
            )

    def test_cosmonarrator_lane_is_local(self) -> None:
        """CosmoNarrator runs CPU-only (PocketTTS, ~6x real-time) — must be a local lane."""
        reg = _isolated_registry()
        entries = reg.for_task(Task.AUDIO_TTS)
        assert entries
        local_lanes = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}
        for entry in entries:
            assert entry.lane in local_lanes, (
                f"{entry.model_id} must be on a local lane, got {entry.lane}"
            )


class TestCosmoNarratorUnverified:
    """MAIN DISCRIMINATOR: registered entry must have verified_working=False.

    A wrong impl that sets verified_working=True (claiming a TTS proof that
    hasn't happened yet) fails this test.
    """

    def test_cosmonarrator_unverified(self) -> None:
        """All AUDIO_TTS entries must have verified_working=False (smoke not yet run)."""
        reg = _isolated_registry()
        entries = reg.for_task(Task.AUDIO_TTS)
        assert entries, "need ≥1 entry to check"
        for entry in entries:
            assert not entry.verified_working, (
                f"{entry.model_id}: verified_working must be False until TTS smoke passes"
            )

    def test_unverified_entry_has_zero_cost(self) -> None:
        """Local TTS entry must have zero cost (CPU-local, no cloud charge)."""
        reg = _isolated_registry()
        for entry in reg.for_task(Task.AUDIO_TTS):
            assert entry.cost_per_1k_input_usd == 0.0
            assert entry.cost_per_1k_output_usd == 0.0


class TestRegistrationAdditive:
    """Registering the CosmoNarrator entry must not disturb other Tasks."""

    def test_general_task_unchanged(self) -> None:
        """for_task(GENERAL) must still return ≥1 entry after item 85."""
        reg = _isolated_registry()
        assert reg.for_task(Task.GENERAL), "GENERAL must still resolve"

    def test_vision_task_unchanged(self) -> None:
        """for_task(VISION) must still return ≥1 entry after item 85."""
        reg = _isolated_registry()
        assert reg.for_task(Task.VISION), "VISION must still resolve a local specialist"

    def test_image_gen_still_empty(self) -> None:
        """IMAGE_GEN has no registered model yet — item 86 is still gated."""
        reg = _isolated_registry()
        assert reg.for_task(Task.IMAGE_GEN) == [], "IMAGE_GEN must still have no entry"

    def test_video_gen_still_empty(self) -> None:
        """VIDEO_GEN has no registered model yet — item 87 is still research-gated."""
        reg = _isolated_registry()
        assert reg.for_task(Task.VIDEO_GEN) == [], "VIDEO_GEN must still have no entry"


class TestRegistryIntegrity:
    """Structural checks on the registry after item 85."""

    def test_cosmonarrator_entry_in_models_dict(self) -> None:
        """The CosmoNarrator model_id must appear in registry.models."""
        reg = _isolated_registry()
        tts_ids = {e.model_id for e in reg.for_task(Task.AUDIO_TTS)}
        for mid in tts_ids:
            assert mid in reg.models, f"{mid} must appear in registry.models"

    def test_no_fabricated_verified_tts(self) -> None:
        """No AUDIO_TTS entry may be marked verified_working=True at registration.

        Verification requires a real TTS smoke test producing a non-empty audio artifact.
        A registry-only edit that sets verified_working=True is a fabrication — fails
        this discriminating test.
        """
        reg = _isolated_registry()
        verified_tts = [e for e in reg.for_task(Task.AUDIO_TTS) if e.verified_working]
        assert not verified_tts, (
            f"AUDIO_TTS entries with fabricated verified_working=True: "
            f"{[e.model_id for e in verified_tts]}"
        )
