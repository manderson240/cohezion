"""Item 123: ideogram-4-GGUF as second IMAGE_GEN candidate — TDD red→green.

Registers `ideogram-4-GGUF` (leejet/ideogram-4-GGUF, 9B text-to-image, Q4_0 5.64GB,
stable-diffusion.cpp Vulkan) as a second ``IMAGE_GEN`` ``ModelEntry`` with
``verified_working=False``, pattern-matching items 4/19/21/23/28/85/103.

Registration-only additive first step.  Serving proof (sd.cpp Vulkan on gfx1151)
is gated behind item 86.  ``for_task(IMAGE_GEN)`` now returns the entry even
before the serving proof runs.

Discriminating tests — each kills a plausible wrong implementation:

  1. for_task(IMAGE_GEN) includes Ideogram4     (PRIMARY: kills "no IMAGE_GEN entries")
  2. Ideogram4 verified_working is False        (kills "mark verified without proof")
  3. task_affinity includes Task.IMAGE_GEN      (kills "missing IMAGE_GEN affinity")
  4. size_gb is approximately 5.64              (kills "fabricated/wrong size")
  5. lane is a LOCAL silicon lane               (kills "mis-routed to cloud")
  6. runtime_backend signals sd.cpp path        (kills "wrong backend wiring")
"""

from __future__ import annotations

from cohezion.inference.registry import FleetRegistry, Lane, Task


# All cloud lanes — Ideogram4 must NOT be on any of these.
_CLOUD_LANES = {Lane.CLOUD_OLLAMA, Lane.CLOUD_CLAUDE, Lane.CLOUD_GEMINI}


def _get_ideogram4(registry: FleetRegistry):
    """Return the ideogram-4-GGUF ModelEntry, or None if absent."""
    candidates = [m for m in registry.for_task(Task.IMAGE_GEN) if "ideogram" in m.model_id.lower()]
    return candidates[0] if candidates else None


def test_for_task_image_gen_includes_ideogram4() -> None:
    """for_task(IMAGE_GEN) must return an entry whose model_id contains 'ideogram'.

    PRIMARY DISCRIMINATOR: kills an impl where IMAGE_GEN still returns [].
    """
    registry = FleetRegistry()
    candidates = registry.for_task(Task.IMAGE_GEN)
    ids = [m.model_id for m in candidates]
    assert any("ideogram" in mid.lower() for mid in ids), (
        f"for_task(IMAGE_GEN) must include ideogram-4-GGUF; got {ids}"
    )


def test_ideogram4_verified_working_is_false() -> None:
    """Ideogram4 must have verified_working=False (serving proof not yet run).

    Kills an impl that marks verified without a real serving smoke test.
    Mirrors the pattern in items 4/19/21/23/28/85/103.
    """
    entry = _get_ideogram4(FleetRegistry())
    assert entry is not None, "ideogram-4-GGUF not found in IMAGE_GEN candidates"
    assert entry.verified_working is False, (
        f"ideogram-4-GGUF must be verified_working=False until item-86 proof runs; "
        f"got {entry.verified_working}"
    )


def test_ideogram4_task_affinity_includes_image_gen() -> None:
    """task_affinity must include Task.IMAGE_GEN (the contract for for_task to work).

    Kills an impl where the affinity set is wrong and for_task would filter it out.
    """
    entry = _get_ideogram4(FleetRegistry())
    assert entry is not None, "ideogram-4-GGUF not found in IMAGE_GEN candidates"
    assert Task.IMAGE_GEN in entry.task_affinity, (
        f"IMAGE_GEN must be in ideogram-4-GGUF task_affinity; got {entry.task_affinity}"
    )


def test_ideogram4_size_gb_approximately_564() -> None:
    """size_gb must be approximately 5.64 (Q4_0 GGUF disk size, non-fabricated).

    Kills an impl that omits size_gb (None) or invents an incorrect value.
    The K1/rule-5 OOM headroom gate requires an honest size to compute headroom.
    """
    entry = _get_ideogram4(FleetRegistry())
    assert entry is not None, "ideogram-4-GGUF not found in IMAGE_GEN candidates"
    assert entry.size_gb is not None, "size_gb must be set (needed for OOM headroom gate)"
    assert abs(entry.size_gb - 5.64) < 0.5, (
        f"size_gb must be ≈5.64 GB (Q4_0 GGUF); got {entry.size_gb}"
    )


def test_ideogram4_lane_is_local_silicon() -> None:
    """Ideogram4 must be on a local silicon lane, NOT a cloud lane.

    Kills an impl that accidentally routes a local sd.cpp model to cloud.
    stable-diffusion.cpp uses Vulkan on the local iGPU — it is a local-only model.
    """
    entry = _get_ideogram4(FleetRegistry())
    assert entry is not None, "ideogram-4-GGUF not found in IMAGE_GEN candidates"
    assert entry.lane not in _CLOUD_LANES, (
        f"ideogram-4-GGUF must be on local silicon; got lane={entry.lane!r} "
        f"(all cloud lanes: {_CLOUD_LANES})"
    )


def test_ideogram4_runtime_backend_signals_sd_cpp() -> None:
    """runtime_backend must signal the stable-diffusion.cpp dispatch path.

    Kills an impl that wires the wrong backend (e.g. 'flm' or 'llamacpp_hip'),
    which would cause the dispatcher to send image-gen traffic to a text-LLM server.
    """
    entry = _get_ideogram4(FleetRegistry())
    assert entry is not None, "ideogram-4-GGUF not found in IMAGE_GEN candidates"
    assert "sd" in entry.runtime_backend.lower() or "diffusion" in entry.runtime_backend.lower(), (
        f"runtime_backend must identify sd.cpp dispatch path; got {entry.runtime_backend!r}"
    )
