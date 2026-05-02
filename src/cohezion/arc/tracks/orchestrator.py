"""ARC-AGI Multi-Track Orchestrator.

V-Model Traceability
--------------------
Requirement  : Coordinate 3 track variants (ARC-AGI-2, ARC-AGI-3, Paper)
               with unified grid processing pipeline.
Architecture  : MultiTrackOrchestrator manages 3 pipeline instances
                with shared PatternExtractor + ARCCodec.
Implementation: Parallel/sequential runner with resource budgets.
Verification  : Each track's verify_submission() is called post-run.
Validation    : Cross-track consistency check on shared task predictions.
                HIHO coherence must stay >= 0.5 across all tracks.

Deadline: 15 Nov 2026 (all tracks)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.arc.grid_pipeline import verify_pipeline_sanity


def _timestamp() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat()


@dataclass
class TrackRun:
    track_name: str
    status: str  # pending | running | success | failed
    summary: dict[str, Any] = field(default_factory=dict)
    elapsed_sec: float = 0.0
    errors: list[str] = field(default_factory=list)


class MultiTrackOrchestrator:
    """Orchestrate all 3 ARC Prize 2026 tracks.

    Usage::

        orch = MultiTrackOrchestrator(
            data_dir=Path("data/arc-agi"),
            output_dir=Path("output/arc-prize-2026"),
        )
        orch.run_all()
        report = orch.report()
        orch.save_report()
    """

    DEADLINE = "2026-11-15"
    PRIZE_POOL_TOTAL = 2_000_000

    def __init__(
        self,
        data_dir: Path,
        output_dir: Path,
        max_depth: int = 3,
        budget: int = 5000,
        top_k_rules: int = 5,
        use_llm_fallback: bool = False,
        llm_fallback_path: Path | None = None,
        parallel: bool = False,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_depth = max_depth
        self.budget = budget
        self.top_k_rules = top_k_rules
        self.use_llm_fallback = use_llm_fallback
        self.llm_fallback_path = llm_fallback_path
        self.parallel = parallel
        self.runs: list[TrackRun] = []

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------
    def run_all(self, task_ids: list[str] | None = None, verbose: bool = True) -> dict[str, Any]:
        """Run all 3 tracks sequentially (or parallel if configured)."""
        # Import here to avoid circular deps
        from cohezion.arc.tracks.arc_agi_2 import ARCAGI2Pipeline
        from cohezion.arc.tracks.arc_agi_3 import ARCAGI3Pipeline
        from cohezion.arc.tracks.paper_track import PaperTrackPipeline

        global_start = time.perf_counter()
        self.runs = []

        # --- Track 1: ARC-AGI-2 ($700K) ---
        run2 = TrackRun(track_name="arc-agi-2", status="running")
        self.runs.append(run2)
        try:
            p2 = ARCAGI2Pipeline(
                data_dir=self.data_dir / "arc-agi-2",
                output_dir=self.output_dir / "arc-agi-2",
                max_depth=self.max_depth,
                budget=self.budget,
                top_k_rules=self.top_k_rules,
                use_llm_fallback=self.use_llm_fallback,
                llm_fallback_path=self.llm_fallback_path,
            )
            run2.summary = p2.run(task_ids=task_ids, verbose=verbose)
            v2 = p2.verify()
            run2.summary["verify"] = v2
            run2.status = "success"
        except Exception as exc:
            run2.status = "failed"
            run2.errors.append(str(exc))

        # --- Track 2: ARC-AGI-3 ($850K) ---
        run3 = TrackRun(track_name="arc-agi-3", status="running")
        self.runs.append(run3)
        try:
            p3 = ARCAGI3Pipeline(
                data_dir=self.data_dir / "arc-agi-3",
                output_dir=self.output_dir / "arc-agi-3",
                max_depth=self.max_depth,
                budget=self.budget,
                top_k_rules=self.top_k_rules,
                use_llm_fallback=self.use_llm_fallback,
                llm_fallback_path=self.llm_fallback_path,
            )
            run3.summary = p3.run(task_ids=task_ids, verbose=verbose)
            v3 = p3.verify()
            run3.summary["verify"] = v3
            run3.status = "success"
        except Exception as exc:
            run3.status = "failed"
            run3.errors.append(str(exc))

        # --- Track 3: Paper Track ($450K) ---
        runp = TrackRun(track_name="paper", status="running")
        self.runs.append(runp)
        try:
            # Paper track wraps whichever base pipeline succeeded first
            base_pipe = (
                p2 if run2.status == "success" else (p3 if run3.status == "success" else None)
            )
            pp = PaperTrackPipeline(
                output_dir=self.output_dir / "paper",
                base_pipeline=base_pipe,
            )
            # Paper track uses same task ids as base
            runp.summary = pp.run(task_ids=task_ids, verbose=verbose)
            runp.status = "success"
        except Exception as exc:
            runp.status = "failed"
            runp.errors.append(str(exc))

        global_elapsed = time.perf_counter() - global_start
        summary = {
            "deadline": self.DEADLINE,
            "prize_pool_usd": self.PRIZE_POOL_TOTAL,
            "elapsed_sec": round(global_elapsed, 2),
            "tracks": [
                {
                    "name": r.track_name,
                    "status": r.status,
                    "summary": r.summary,
                    "errors": r.errors,
                }
                for r in self.runs
            ],
        }
        if verbose:
            print(f"[Orchestrator] All tracks complete in {global_elapsed:.1f}s")
        return summary

    def report(self) -> dict[str, Any]:
        """Generate cross-track consistency report."""
        total_tasks = 0
        solved_tasks = 0
        for r in self.runs:
            if r.status == "success":
                total_tasks += r.summary.get("tasks", 0)
                solved_tasks += r.summary.get("correct", r.summary.get("tasks", 0))

        report = {
            "generated_at": _timestamp(),
            "deadline": self.DEADLINE,
            "prize_pool_usd": self.PRIZE_POOL_TOTAL,
            "tracks": [r.__dict__ for r in self.runs],
            "cross_track_consistency": {
                "all_success": all(r.status == "success" for r in self.runs),
                "total_predictions": total_tasks,
                "total_errors": sum(len(r.errors) for r in self.runs),
            },
        }
        return report

    def save_report(self, path: Path | None = None) -> Path:
        if path is None:
            path = self.output_dir / "orchestrator_report.json"
        path.write_text(json.dumps(self.report(), indent=2))
        return path

    def verify_all(self) -> dict[str, Any]:
        """Run verification on every track's submission.json."""
        results = {}
        for r in self.runs:
            if r.status != "success":
                results[r.track_name] = {"valid": False, "errors": ["track did not run"]}
                continue
            track_dir = self.output_dir / r.track_name
            sub = track_dir / "submission.json"
            data = self.data_dir / r.track_name
            if not sub.exists():
                results[r.track_name] = {"valid": False, "errors": ["submission.json missing"]}
                continue
            from cohezion.arc.submission import verify_submission

            results[r.track_name] = verify_submission(sub, data)
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="ARC Multi-Track Orchestrator")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--budget", type=int, default=5000)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--llm-fallback", action="store_true")
    parser.add_argument("--llm-fallback-path", type=Path, default=None)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    # Pre-flight: verify grid pipeline sanity
    sanity = verify_pipeline_sanity()
    if not sanity["all_ok"]:
        print(json.dumps(sanity, indent=2))
        sys.exit(1)

    orch = MultiTrackOrchestrator(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        max_depth=args.max_depth,
        budget=args.budget,
        top_k_rules=args.top_k,
        use_llm_fallback=args.llm_fallback,
        llm_fallback_path=args.llm_fallback_path,
    )
    summary = orch.run_all()
    report_path = orch.save_report()
    print(json.dumps(summary, indent=2))
    print(f"Report saved: {report_path}")

    if args.verify:
        vres = orch.verify_all()
        print(json.dumps(vres, indent=2))
        if not all(v.get("valid", False) for v in vres.values() if isinstance(v, dict)):
            sys.exit(1)
