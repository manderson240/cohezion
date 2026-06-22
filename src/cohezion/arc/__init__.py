"""ARC-AGI submission pipeline for Cohezion.

Modules:
    codec — Grid encoder/decoder for ARC format
    pattern_extractor — Compound engineering pattern rule extractor
    submission — Kaggle-ready submission package generator
    grid_pipeline — ARC grid processing pipeline with HIHO verification
    tracks — Multi-track orchestrator and individual track pipelines
"""

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


import contextlib

# Wiring-sweep 2026-06-22: data_loader, evaluate_local, solver, transforms were orphans.
with contextlib.suppress(Exception):
    from cohezion.arc.data_loader import load_task as load_task
    from cohezion.arc.data_loader import load_all as load_all

with contextlib.suppress(Exception):
    from cohezion.arc.evaluate_local import score_submission as score_submission

with contextlib.suppress(Exception):
    from cohezion.arc.solver import SolverState as SolverState


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
