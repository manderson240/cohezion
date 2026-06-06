"""Discriminating test for the wiring-sweep edge: pipeline → incremental_trainer (2026-06-06).

`incremental_trainer` was a genuine production orphan in pipeline/ — its IncrementalResult /
IncrementalVAETrainer / IncrementalRLTrainer (online/incremental VAE+RL training) had ZERO
importers anywhere (src, tests, registry, entry-points). Wired non-destructively via a guarded
`cohezion.pipeline` __init__ re-export.

Falsifiable: this test fails if the static edge is removed — every name must resolve FROM the
package AND be the source module's own object (identity), and appear in __all__. A wrong impl
that forgot the re-export, or aliased a different object, fails.
"""

from __future__ import annotations

import cohezion.pipeline as pipeline
import cohezion.pipeline.incremental_trainer as src


def test_incremental_trainer_reexported_from_pipeline() -> None:
    for name in ("IncrementalResult", "IncrementalVAETrainer", "IncrementalRLTrainer"):
        assert hasattr(pipeline, name), f"pipeline.{name} unreachable — wiring edge missing"
        assert getattr(pipeline, name) is getattr(src, name), f"{name} is not the source object"
        assert name in pipeline.__all__, f"{name} missing from pipeline.__all__"
