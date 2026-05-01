"""ARC Prize 2026 track pipelines.

Modules:
    arc_agi_2     — ARC-AGI-2 static track ($700K)
    arc_agi_3     — ARC-AGI-3 interactive track ($850K)
    paper_track   — Paper track ($450K)
    orchestrator  — Multi-track coordinator
"""

from cohezion.arc.tracks.arc_agi_2 import ARCAGI2Pipeline
from cohezion.arc.tracks.arc_agi_3 import ARCAGI3Pipeline
from cohezion.arc.tracks.orchestrator import MultiTrackOrchestrator
from cohezion.arc.tracks.paper_track import PaperTrackPipeline


__all__ = [
    "ARCAGI2Pipeline",
    "ARCAGI3Pipeline",
    "MultiTrackOrchestrator",
    "PaperTrackPipeline",
]
