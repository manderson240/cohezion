"""Item 89: Multimodal I/O envelope (TDD red→green).

`MultimodalMessage` is a Pydantic boundary model carrying mixed-modality parts
through the dispatcher: `{text, image_refs, audio_refs, video_refs}`.

Each test fails a plausible wrong impl:
  - no unknown-part rejection → test_unknown_part_type_rejected
  - required fields cause empty-message to fail → test_empty_message_valid
  - round-trip loses fields → test_mixed_message_roundtrip
  - optional list allows non-string refs → test_refs_must_be_strings
"""

from __future__ import annotations

import pytest

from cohezion.inference.multimodal_envelope import MultimodalMessage


# ---------------------------------------------------------------------------
# Validation: text-only
# ---------------------------------------------------------------------------


class TestTextOnly:
    def test_text_only_validates(self) -> None:
        msg = MultimodalMessage(text="hello world")
        assert msg.text == "hello world"
        assert msg.image_refs is None
        assert msg.audio_refs is None
        assert msg.video_refs is None

    def test_text_none_is_valid(self) -> None:
        """text=None is valid — message may carry refs only."""
        msg = MultimodalMessage(text=None)
        assert msg.text is None


# ---------------------------------------------------------------------------
# Validation: empty message (all-None parts)
# ---------------------------------------------------------------------------


class TestEmptyMessage:
    def test_empty_message_valid(self) -> None:
        """Empty MultimodalMessage (all fields at defaults) must not raise.

        DISCRIMINATOR: a wrong impl with required fields rejects this.
        """
        msg = MultimodalMessage()
        assert msg.text is None
        assert msg.image_refs is None
        assert msg.audio_refs is None
        assert msg.video_refs is None

    def test_empty_message_type(self) -> None:
        """An empty message is still a MultimodalMessage instance."""
        msg = MultimodalMessage()
        assert isinstance(msg, MultimodalMessage)


# ---------------------------------------------------------------------------
# Validation: mixed-modality round-trip
# ---------------------------------------------------------------------------


class TestMixedMessage:
    def test_mixed_text_image_audio_validates(self) -> None:
        """A mixed text+image+audio message must validate."""
        msg = MultimodalMessage(
            text="describe this",
            image_refs=["img://scene.png"],
            audio_refs=["audio://ambient.wav"],
        )
        assert msg.text == "describe this"
        assert msg.image_refs == ["img://scene.png"]
        assert msg.audio_refs == ["audio://ambient.wav"]
        assert msg.video_refs is None

    def test_mixed_message_roundtrip(self) -> None:
        """Round-trip through model_dump/model_validate preserves all fields.

        DISCRIMINATOR: a wrong impl losing optional fields on round-trip fails.
        """
        data = {
            "text": "analyse this video",
            "image_refs": ["img://frame1.jpg", "img://frame2.jpg"],
            "audio_refs": None,
            "video_refs": ["vid://clip.mp4"],
        }
        msg = MultimodalMessage(**data)
        dumped = msg.model_dump()
        assert dumped["text"] == data["text"]
        assert dumped["image_refs"] == data["image_refs"]
        assert dumped["audio_refs"] is None
        assert dumped["video_refs"] == data["video_refs"]

    def test_all_refs_present(self) -> None:
        """Message with all four modalities populates correctly."""
        msg = MultimodalMessage(
            text="full multimodal",
            image_refs=["img://a.png"],
            audio_refs=["audio://b.mp3"],
            video_refs=["vid://c.mp4"],
        )
        assert len(msg.image_refs) == 1
        assert len(msg.audio_refs) == 1
        assert len(msg.video_refs) == 1


# ---------------------------------------------------------------------------
# Validation: unknown part types rejected
# ---------------------------------------------------------------------------


class TestUnknownPartRejected:
    def test_unknown_part_type_rejected(self) -> None:
        """MAIN DISCRIMINATOR: an unknown field must raise a ValidationError.

        A plain dataclass or BaseModel without extra='forbid' would silently
        accept 'depth_refs', making the boundary porous to injection/drift.
        """
        with pytest.raises(Exception):  # pydantic ValidationError
            MultimodalMessage(text="hi", depth_refs=["depth://scan.exr"])  # type: ignore[call-arg]

    def test_unknown_field_forbidden_not_ignored(self) -> None:
        """Unknown fields are NOT silently ignored — Pydantic raises, not swallows."""
        raised = False
        try:
            MultimodalMessage(unknown_modality=["x://foo"])  # type: ignore[call-arg]
        except Exception:
            raised = True
        assert raised, "unknown fields must raise, not be silently ignored"


# ---------------------------------------------------------------------------
# Type constraints on refs
# ---------------------------------------------------------------------------


class TestRefTypes:
    def test_refs_must_be_list_of_strings(self) -> None:
        """image_refs / audio_refs / video_refs are list[str] — a nested int fails."""
        # An integer in the list should fail Pydantic coercion / strict typing
        with pytest.raises(Exception):
            MultimodalMessage(image_refs=[123])  # type: ignore[list-item]

    def test_empty_list_of_refs_is_valid(self) -> None:
        """An explicit empty list (not None) is a valid, distinct state."""
        msg = MultimodalMessage(image_refs=[])
        assert msg.image_refs == []

    def test_multiple_refs_in_one_modality(self) -> None:
        """Multiple refs in one modality validate as a list."""
        msg = MultimodalMessage(audio_refs=["a://1.wav", "a://2.wav", "a://3.wav"])
        assert len(msg.audio_refs) == 3
