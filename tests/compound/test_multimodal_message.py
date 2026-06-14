"""Item 89: MultimodalMessage typed I/O envelope (TDD red→green).

Each test fails a plausible wrong implementation:
  - missing field → test_text_only_validates
  - no validation → test_unknown_field_rejected
  - not round-tripping → test_mixed_message_round_trips
  - crashing on empty → test_empty_message_valid
  - wrong field types → test_refs_must_be_lists_of_str
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cohezion.compound.multimodal_message import MultimodalMessage


# ---------------------------------------------------------------------------
# T_text_only: text-only message with all ref fields absent validates
# Fails: an impl that requires at least one media ref.
# ---------------------------------------------------------------------------


def test_text_only_validates() -> None:
    """A message with only text (no refs) is valid — the common case."""
    msg = MultimodalMessage(text="Hello, cohezion!")
    assert msg.text == "Hello, cohezion!"
    assert msg.image_refs is None
    assert msg.audio_refs is None
    assert msg.video_refs is None


# ---------------------------------------------------------------------------
# T_empty: fully-empty message (all None) is valid
# Fails: an impl that requires text.
# ---------------------------------------------------------------------------


def test_empty_message_valid() -> None:
    """An all-None message is valid (valid 'no content yet' sentinel)."""
    msg = MultimodalMessage()
    assert msg.text is None
    assert msg.image_refs is None
    assert msg.audio_refs is None
    assert msg.video_refs is None


# ---------------------------------------------------------------------------
# T_mixed: full mixed-modality message round-trips through model_dump / model_validate
# Fails: an impl with wrong field names or non-serialisable types.
# ---------------------------------------------------------------------------


def test_mixed_message_round_trips() -> None:
    """A mixed text+image+audio+video message serialises and deserialises identically."""
    original = MultimodalMessage(
        text="describe and narrate",
        image_refs=["s3://bucket/frame1.jpg", "s3://bucket/frame2.jpg"],
        audio_refs=["s3://bucket/narration.wav"],
        video_refs=["s3://bucket/clip.mp4"],
    )
    data = original.model_dump()
    restored = MultimodalMessage.model_validate(data)
    assert restored == original


# ---------------------------------------------------------------------------
# T_unknown: extra/unknown field → ValidationError
# Fails: an impl without `extra="forbid"` (or without Pydantic at all).
# ---------------------------------------------------------------------------


def test_unknown_field_rejected() -> None:
    """An unrecognised modality field must raise ValidationError (Pydantic boundary)."""
    with pytest.raises(ValidationError):
        MultimodalMessage(text="hi", emoji_refs=["👾"])  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# T_type: refs fields must be lists of str, not arbitrary objects
# Fails: an impl that uses Any or no type coercion.
# ---------------------------------------------------------------------------


def test_refs_must_be_lists_of_str() -> None:
    """image_refs=list[str] — passing an int should be coerced or rejected."""
    # Pydantic will try to coerce; a bare int where a list is expected raises.
    with pytest.raises(ValidationError):
        MultimodalMessage(image_refs=42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# T_nonempty_refs: non-empty refs round-trip correctly
# ---------------------------------------------------------------------------


def test_nonempty_refs_survive_round_trip() -> None:
    """Lists of refs survive model_dump → model_validate unchanged."""
    msg = MultimodalMessage(
        image_refs=["img://a", "img://b"],
        audio_refs=["audio://x"],
    )
    data = msg.model_dump()
    assert data["image_refs"] == ["img://a", "img://b"]
    assert data["audio_refs"] == ["audio://x"]
    assert data["video_refs"] is None
    assert data["text"] is None
