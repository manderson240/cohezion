"""Discriminating test for the wiring-sweep edge: data_mesh → audio_telemetry (2026-06-06).

`audio_telemetry` was a genuine production orphan in data_mesh/ — its bioacoustic schema
(TaxonomyLevel / BirdSpeciesNode / AudioSegmentMetadata / SpectrogramConfig /
AudioTelemetryEvent, the BirdCLEF-2026 telemetry data product) had ZERO importers anywhere
(the lone "audio_telemetry" grep hit in learning/ouroboros.py is a method NAME, not an
import). Wired non-destructively via a guarded `cohezion.data_mesh` __init__ re-export.

Falsifiable: this test fails if the static edge is removed — every schema name must resolve
FROM the package AND be the source module's own object (identity), and appear in __all__. A
wrong impl that forgot the re-export, or aliased a different object, fails.
"""

from __future__ import annotations

import cohezion.data_mesh as data_mesh
import cohezion.data_mesh.audio_telemetry as src


def test_audio_telemetry_reexported_from_data_mesh() -> None:
    for name in (
        "TaxonomyLevel",
        "BirdSpeciesNode",
        "AudioSegmentMetadata",
        "SpectrogramConfig",
        "AudioTelemetryEvent",
    ):
        assert hasattr(data_mesh, name), f"data_mesh.{name} unreachable — wiring edge missing"
        assert getattr(data_mesh, name) is getattr(src, name), f"{name} is not the source object"
        assert name in data_mesh.__all__, f"{name} missing from data_mesh.__all__"
