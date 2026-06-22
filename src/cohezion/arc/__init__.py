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


with contextlib.suppress(Exception):
    from cohezion.arc.codec import ARCCodec as ARCCodec
    from cohezion.arc.codec import decode_prediction as decode_prediction
    from cohezion.arc.codec import encode_task as encode_task

with contextlib.suppress(Exception):
    from cohezion.arc.grid_pipeline import batch_decode as batch_decode
    from cohezion.arc.grid_pipeline import batch_encode as batch_encode
    from cohezion.arc.grid_pipeline import decode_grid as decode_grid
    from cohezion.arc.grid_pipeline import encode_grid as encode_grid
    from cohezion.arc.grid_pipeline import grid_hash as grid_hash
    from cohezion.arc.grid_pipeline import grid_summary as grid_summary
    from cohezion.arc.grid_pipeline import validate_grid as validate_grid
    from cohezion.arc.grid_pipeline import verify_pipeline_sanity as verify_pipeline_sanity

with contextlib.suppress(Exception):
    from cohezion.arc.pattern_extractor import CompoundRule as CompoundRule
    from cohezion.arc.pattern_extractor import PatternExtractor as PatternExtractor

with contextlib.suppress(Exception):
    from cohezion.arc.submission import SubmissionBuilder as SubmissionBuilder
    from cohezion.arc.submission import verify_submission as verify_submission

with contextlib.suppress(Exception):
    from cohezion.arc.tracks import ARCAGI2Pipeline as ARCAGI2Pipeline
    from cohezion.arc.tracks import ARCAGI3Pipeline as ARCAGI3Pipeline
    from cohezion.arc.tracks import MultiTrackOrchestrator as MultiTrackOrchestrator
    from cohezion.arc.tracks import PaperTrackPipeline as PaperTrackPipeline

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
