"""Multimodal Task taxonomy — image/audio/video in+out Tasks (item 83 + user video directive, 2026-06-06).

cohezion ingests images (VISION/EXTRACTION/OCR_DOC) but had no Task for image/audio/VIDEO output, nor
for video INPUT. This adds `IMAGE_GEN`, `AUDIO_TTS`, `VIDEO_GEN` (outputs) + `VIDEO_UNDERSTAND` (video
input) to the registry `Task` enum — the same additive, no-model-yet pattern as the task-specialist
members. Non-fabrication: a Task with zero registered ModelEntries is honest "capability declared, not
yet served" — `for_task` returns [] for it until a real specialist is added (gated by items 86/87/93).

Each test fails a plausible wrong impl:
  - a member is missing → test_video_tasks_exist / test_all_multimodal_members_exist,
  - a fabricated model leaks in → test_new_tasks_have_no_registered_model,
  - an additive member broke an existing Task → test_existing_tasks_unaffected.
"""

from __future__ import annotations

from cohezion.inference.registry import Task, get_registry


def test_video_tasks_exist() -> None:
    # The user directive: "we need to add video tasks" — both directions.
    assert Task.VIDEO_GEN.value == "video_gen"
    assert Task.VIDEO_UNDERSTAND.value == "video_understand"


def test_all_multimodal_members_exist() -> None:
    for name in ("IMAGE_GEN", "AUDIO_TTS", "VIDEO_GEN", "VIDEO_UNDERSTAND"):
        assert hasattr(Task, name), f"Task.{name} missing"


def test_new_tasks_have_no_registered_model() -> None:
    # Non-fabrication: capability declared, not yet served → for_task returns [] (no invented model).
    # AUDIO_TTS is excluded: item 85 wired CosmoNarrator-PocketTTS as its registered-unverified seed.
    reg = get_registry()
    for t in (Task.IMAGE_GEN, Task.VIDEO_GEN, Task.VIDEO_UNDERSTAND):
        assert reg.for_task(t) == [], f"{t.name} must have no registered model yet"


def test_existing_tasks_unaffected() -> None:
    # Additive change must not disturb the pre-existing members (VISION input still present & served).
    assert Task.VISION.value == "vision"
    assert get_registry().for_task(Task.VISION), "VISION should still resolve a local specialist"
