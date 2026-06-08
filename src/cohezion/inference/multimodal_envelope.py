"""Multimodal I/O envelope for the fleet dispatcher (item 89, thread M).

``MultimodalMessage`` is the typed boundary model that carries mixed-modality
parts through ``fleet._dispatch_one``.  It is PURELY a data-shape declaration:
no dispatch behaviour is changed in this item.

Design:
- All four part fields are optional (default ``None``) — a text-only message
  is perfectly valid, as is an empty message waiting to be populated.
- ``model_config = ConfigDict(extra="forbid")`` enforces that callers pass ONLY
  the declared four modalities.  An unknown part type (e.g. ``depth_refs``) is
  rejected at construction time by Pydantic, keeping the boundary clean.
- ``list[str]`` for ref fields: each ref is a URI-style identifier
  (``"img://…"``, ``"audio://…"``, ``"vid://…"``) pointing to the actual blob
  managed by the storage tier.  Validation enforces the element type.

Usage::

    msg = MultimodalMessage(text="hello world")
    mixed = MultimodalMessage(
        text="analyse the attached clip",
        image_refs=["img://frame01.jpg"],
        audio_refs=["audio://narration.wav"],
        video_refs=["vid://clip.mp4"],
    )

Item 89 deliverable.  The dispatch wiring (fleet branch for multimodal)
is the separate gated step — this module declares the data shape only.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MultimodalMessage(BaseModel):
    """Mixed-modality message envelope for the cohezion fleet dispatcher (item 89).

    All fields are optional; an empty ``MultimodalMessage()`` is valid and
    represents a not-yet-populated payload.  Unknown fields are forbidden —
    Pydantic raises ``ValidationError`` on any unrecognised keyword.

    Attributes
    ----------
    text:
        UTF-8 text content (generation prompt or user turn).
    image_refs:
        Ordered list of image blob URIs (e.g. ``"img://…"``).
    audio_refs:
        Ordered list of audio blob URIs (e.g. ``"audio://…"``).
    video_refs:
        Ordered list of video blob URIs (e.g. ``"vid://…"``).
    """

    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    image_refs: list[str] | None = None
    audio_refs: list[str] | None = None
    video_refs: list[str] | None = None


__all__ = ["MultimodalMessage"]


# ---------------------------------------------------------------------------
# ## FUTURE HOOKS
# ---------------------------------------------------------------------------
# 89b: Wire MultimodalMessage as the input type for fleet._dispatch_one — replace
#      the current bare-string prompt with MultimodalMessage so the dispatcher
#      can branch on image_refs / audio_refs / video_refs presence.
# 89c: Add a `from_text(cls, text)` classmethod for ergonomic construction from
#      a plain string (the 95% case) without the dict wrapper.
# 89d: Integrate with the AG-UI typed SSE event layer — wrap MultimodalMessage
#      as a StreamInput event so streaming callers see modality-aware payloads.
