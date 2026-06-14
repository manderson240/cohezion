"""Item 89 — MultimodalMessage: typed I/O envelope for mixed-modality dispatcher input/output.

A validated, immutable data shape that carries mixed-modality parts (text, images, audio clips,
video clips) through the cohezion compound dispatcher. It is the boundary type: callers who pass
an unknown modality are rejected immediately via Pydantic rather than silently discarded.

Design:
  - All fields optional (None = absent / not-yet-provided).
  - ``extra="forbid"`` rejects unknown fields at validation time (the I/O boundary guard).
  - ``frozen=True`` makes instances hashable and immutable after construction.
  - refs fields carry opaque URI strings (s3://, local://, data-uri, …) — the dispatcher
    resolves them; MultimodalMessage itself does not open files.

This is a pure data envelope — no dispatch, no I/O, no SurrealDB. The wiring of
MultimodalMessage into the live dispatcher is the separate gated behaviour-change (item 90+).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MultimodalMessage(BaseModel):
    """Typed container for a mixed-modality dispatcher message.

    All fields default to ``None`` (absent). An all-None message is a valid "no content yet"
    sentinel (e.g. a routing stub). Extra/unknown fields raise ``ValidationError`` immediately.

    Attributes
    ----------
    text:
        Free-form text payload (prompt, transcript, caption, …).
    image_refs:
        Ordered list of image URI strings (s3://, file://, data:image/…).
    audio_refs:
        Ordered list of audio URI strings (s3://, file://, data:audio/…).
    video_refs:
        Ordered list of video URI strings (s3://, file://, data:video/…).
    """

    model_config = ConfigDict(
        frozen=True,  # immutable — safe to pass by reference through the pipeline
        extra="forbid",  # unknown modality fields rejected at the boundary (I/O guard)
    )

    text: str | None = None
    image_refs: list[str] | None = None
    audio_refs: list[str] | None = None
    video_refs: list[str] | None = None
