"""ARC-AGI submission pipeline for Cohezion.

Modules:
    codec — Grid encoder/decoder for ARC format
    pattern_extractor — Compound engineering pattern rule extractor
    submission — Kaggle-ready submission package generator
    grid_pipeline — ARC grid processing pipeline with HIHO verification
    tracks — Multi-track orchestrator and individual track pipelines
"""

from __future__ import annotations

import contextlib

from cohezion.arc.codec import ARCCodec, decode_prediction, encode_task
from cohezion.arc.grid_pipeline import (
    batch_decode,
    batch_encode,
    decode_grid,
    encode_grid,
    grid_hash,
    grid_summary,
    validate_grid,
    verify_pipeline_sanity,
)
from cohezion.arc.pattern_extractor import CompoundRule, PatternExtractor
from cohezion.arc.submission import SubmissionBuilder, verify_submission
from cohezion.arc.tracks import (
    ARCAGI2Pipeline,
    ARCAGI3Pipeline,
    MultiTrackOrchestrator,
    PaperTrackPipeline,
)

# Wiring-sweep 2026-06-22: data_loader, evaluate_local, solver were orphans.
with contextlib.suppress(Exception):
    from cohezion.arc.data_loader import load_all as load_all
    from cohezion.arc.data_loader import load_task as load_task

with contextlib.suppress(Exception):
    from cohezion.arc.evaluate_local import score_submission as score_submission

with contextlib.suppress(Exception):
    from cohezion.arc.solver import SolverState as SolverState

# Wiring-sweep 2026-06-22: transforms was a genuine import-graph orphan (29 grid xform ops).
with contextlib.suppress(Exception):
    from cohezion.arc.transforms import ALL_TRANSFORMS as ALL_TRANSFORMS
    from cohezion.arc.transforms import TransformFn as TransformFn
    from cohezion.arc.transforms import apply_chain as apply_chain
    from cohezion.arc.transforms import get_timing_report as get_timing_report
    from cohezion.arc.transforms import make_color_remap as make_color_remap
    from cohezion.arc.transforms import make_color_swap as make_color_swap


__all__ = [
    "ARCAGI2Pipeline",
    "ARCAGI3Pipeline",
    "ARCCodec",
    "CompoundRule",
    "MultiTrackOrchestrator",
    "PaperTrackPipeline",
    "PatternExtractor",
    "SubmissionBuilder",
    "batch_decode",
    "batch_encode",
    "decode_grid",
    "decode_prediction",
    "encode_grid",
    "encode_task",
    "grid_hash",
    "grid_summary",
    "validate_grid",
    "verify_pipeline_sanity",
    "verify_submission",
]
