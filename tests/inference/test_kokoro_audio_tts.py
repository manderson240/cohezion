"""Item 103: Register kokoro-v1 as a second AUDIO_TTS ModelEntry (TDD red→green).

`for_task(Task.AUDIO_TTS)` must return BOTH the item-85 CosmoNarrator entry AND the
new kokoro-v1 entry (`hexgrad/Kokoro-82M`, Apache-2.0, ALREADY served on :13305).
This supersedes item-85's "needs serving proof" — the artifact already exists.
Both entries are registered with `verified_working=False` (non-fabrication: the TTS smoke
producing a non-empty audio artifact is the verification gate).

Each test fails a plausible wrong impl:
  - only CosmoNarrator present → test_kokoro_registered
  - kokoro has verified_working=True (fabricated proof) → test_kokoro_unverified
  - kokoro not on a local lane → test_kokoro_lane_is_local
  - CosmoNarrator was dropped when kokoro was added → test_cosmonarrator_still_present
  - kokoro not bound to AUDIO_TTS → test_kokoro_task_affinity
  - other Tasks broken by addition → TestRegistrationAdditive
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


def _all_audio_tts_ids() -> list[str]:
    return [e.model_id for e in _isolated_registry().for_task(Task.AUDIO_TTS)]


# ---------------------------------------------------------------------------
# Core correctness — kokoro-v1 present
# ---------------------------------------------------------------------------


class TestKokoroRegistered:
    """for_task(AUDIO_TTS) now returns kokoro-v1 as a second entry."""

    def test_kokoro_registered(self) -> None:
        """AUDIO_TTS must include a kokoro-v1 entry after item 103.

        Kills an impl that only has CosmoNarrator.
        """
        ids = _all_audio_tts_ids()
        assert any("kokoro" in mid.lower() for mid in ids), (
            f"kokoro-v1 entry not found in AUDIO_TTS entries: {ids}"
        )

    def test_audio_tts_has_two_entries(self) -> None:
        """After item 103, AUDIO_TTS must have ≥2 registered entries.

        Kills an impl that added kokoro but removed CosmoNarrator (not additive).
        """
        entries = _isolated_registry().for_task(Task.AUDIO_TTS)
        assert len(entries) >= 2, (
            f"AUDIO_TTS must have ≥2 entries (CosmoNarrator + kokoro), got {len(entries)}: "
            f"{[e.model_id for e in entries]}"
        )

    def test_kokoro_task_affinity(self) -> None:
        """kokoro-v1's task_affinity must include AUDIO_TTS."""
        reg = _isolated_registry()
        kokoro = next(
            (e for e in reg.for_task(Task.AUDIO_TTS) if "kokoro" in e.model_id.lower()), None
        )
        assert kokoro is not None, "kokoro entry must exist"
        assert Task.AUDIO_TTS in kokoro.task_affinity, (
            f"AUDIO_TTS missing from kokoro task_affinity: {kokoro.task_affinity}"
        )

    def test_kokoro_lane_is_local(self) -> None:
        """kokoro-v1 must be on a local lane (not cloud).

        Kills an impl that accidentally assigns a cloud lane to the local ONNX model.
        """
        reg = _isolated_registry()
        kokoro = next(
            (e for e in reg.for_task(Task.AUDIO_TTS) if "kokoro" in e.model_id.lower()), None
        )
        assert kokoro is not None, "kokoro entry must exist"
        local_lanes = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}
        assert kokoro.lane in local_lanes, f"kokoro must be on a local lane, got {kokoro.lane}"

    def test_kokoro_zero_cost(self) -> None:
        """Local TTS entry must have zero cloud cost."""
        reg = _isolated_registry()
        kokoro = next(
            (e for e in reg.for_task(Task.AUDIO_TTS) if "kokoro" in e.model_id.lower()), None
        )
        assert kokoro is not None
        assert kokoro.cost_per_1k_input_usd == 0.0
        assert kokoro.cost_per_1k_output_usd == 0.0


# ---------------------------------------------------------------------------
# Non-fabrication: kokoro must be registered-unverified
# ---------------------------------------------------------------------------


class TestKokoroUnverified:
    """MAIN DISCRIMINATOR: kokoro registered with verified_working=False.

    A wrong impl that sets verified_working=True claims a TTS smoke proof
    that hasn't been run yet — this test catches that fabrication.
    """

    def test_kokoro_unverified(self) -> None:
        """kokoro-v1 must have verified_working=False at registration time."""
        reg = _isolated_registry()
        kokoro = next(
            (e for e in reg.for_task(Task.AUDIO_TTS) if "kokoro" in e.model_id.lower()), None
        )
        assert kokoro is not None, "kokoro entry must exist"
        assert not kokoro.verified_working, (
            "kokoro verified_working must be False until a TTS smoke passes — "
            "setting True without the smoke is a fabrication"
        )

    def test_no_audio_tts_entry_fabricated_verified(self) -> None:
        """No AUDIO_TTS entry may have verified_working=True (neither kokoro nor CosmoNarrator).

        Both entries await their TTS smoke proof.
        """
        reg = _isolated_registry()
        verified = [e for e in reg.for_task(Task.AUDIO_TTS) if e.verified_working]
        assert not verified, (
            f"AUDIO_TTS entries with fabricated verified_working=True: "
            f"{[e.model_id for e in verified]}"
        )


# ---------------------------------------------------------------------------
# Additive: CosmoNarrator (item 85) must still be present
# ---------------------------------------------------------------------------


class TestAdditive:
    """Adding kokoro must not disturb CosmoNarrator (item 85) or other Tasks."""

    def test_cosmonarrator_still_present(self) -> None:
        """CosmoNarrator must remain in AUDIO_TTS after kokoro is added.

        Kills an impl that replaces CosmoNarrator with kokoro instead of
        adding a second entry.
        """
        ids = _all_audio_tts_ids()
        assert any(
            "cosmo" in mid.lower() or "pockettts" in mid.lower() or "tts" in mid.lower()
            for mid in ids
        ), f"CosmoNarrator must still be present, got: {ids}"

    def test_general_task_unchanged(self) -> None:
        """for_task(GENERAL) must still resolve after item 103."""
        reg = _isolated_registry()
        assert reg.for_task(Task.GENERAL), "GENERAL task routing must be unaffected"

    def test_vision_task_unchanged(self) -> None:
        """for_task(VISION) must still resolve after item 103."""
        reg = _isolated_registry()
        assert reg.for_task(Task.VISION), "VISION task routing must be unaffected"

    def test_kokoro_in_registry_models_dict(self) -> None:
        """The kokoro model_id must appear in registry.models (not just for_task)."""
        reg = _isolated_registry()
        kokoro_entries = [e for e in reg.for_task(Task.AUDIO_TTS) if "kokoro" in e.model_id.lower()]
        assert kokoro_entries, "kokoro entry must exist"
        for entry in kokoro_entries:
            assert entry.model_id in reg.models, (
                f"{entry.model_id} returned by for_task but absent from registry.models"
            )
