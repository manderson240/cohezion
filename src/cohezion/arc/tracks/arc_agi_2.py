"""ARC-AGI-2 Track Submission Pipeline (Static Track — $700K Prize).

V-Model Traceability
--------------------
Requirement  : Produce Kaggle-ready submission.json for ARC-AGI-2 static eval.
Architecture  : SubmissionBuilder + PatternExtractor + DSL solver.
Implementation: Inherits from base track pipeline; uses 2 attempts per test.
Verification  : verify_submission() checks grid invariants + attempt counts.
Validation    : run against evaluation set + compute score.

Deadline: 15 Nov 2026
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.arc.codec import Grid, grids_equal
from cohezion.arc.pattern_extractor import PatternExtractor
from cohezion.arc.submission import PredictionProvenance, SubmissionBuilder, verify_submission


def _default_grid(rows: int = 1, cols: int = 1) -> Grid:
    return [[0] * cols for _ in range(rows)]


@dataclass
class ARCAGI2Result:
    """Result container for ARC-AGI-2 track."""

    task_id: str
    predictions: list[dict[str, Any]]
    source: str  # 'rule' | 'fallback_dsl' | 'fallback_llm' | 'default_zero'
    confidence: float
    wall_time_ms: float
    provenance: list[PredictionProvenance] = field(default_factory=list)


class ARCAGI2Pipeline:
    """ARC-AGI-2 static track submission pipeline.

    Parameters
    ----------
    data_dir : Path
        Directory containing ``arc-agi-2/arc-agi_test_challenges.json``.
    output_dir : Path
        Where ``submission.json``, provenance, and package are written.
    max_depth : int
        DSL search depth (default 3).
    budget : int
        DSL candidate evaluations per task (default 5000).
    top_k_rules : int
        Number of compound rules to try before fallback.
    use_llm_fallback : bool
        Enable LLM program generation for unsolved tasks.
    """

    TRACK_NAME = "arc-agi-2"
    PRIZE_USD = 700_000
    DEADLINE = "2026-11-15"
    NUM_ATTEMPTS = 2

    def __init__(
        self,
        data_dir: Path,
        output_dir: Path,
        max_depth: int = 3,
        budget: int = 5000,
        top_k_rules: int = 5,
        use_llm_fallback: bool = False,
        llm_fallback_path: Path | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.builder = SubmissionBuilder(
            data_dir=self.data_dir,
            output_path=self.output_dir / "submission.json",
            extractor=PatternExtractor(max_depth=max_depth, budget_per_strategy=budget),
            max_depth=max_depth,
            budget=budget,
            top_k_rules=top_k_rules,
            use_llm_fallback=use_llm_fallback,
            llm_fallback_path=llm_fallback_path,
        )
        self.results: list[ARCAGI2Result] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, task_ids: list[str] | None = None, verbose: bool = True) -> dict[str, Any]:
        """Run full pipeline and return submission dict."""
        start = time.perf_counter()
        submission = self.builder.build(task_ids=task_ids, verbose=verbose)
        elapsed = time.perf_counter() - start

        # Save artifacts
        self.builder.save(submission)
        self.builder.save_provenance(self.output_dir / "provenance.jsonl")
        pkg = self.builder.package(submission)

        summary = {
            "track": self.TRACK_NAME,
            "tasks": len(submission),
            "elapsed_sec": round(elapsed, 2),
            "output": str(self.output_dir / "submission.json"),
            "package": str(pkg),
        }
        if verbose:
            print(f"[ARC-AGI-2] {summary}")
        return summary

    def verify(self) -> dict[str, Any]:
        """Run verification harness on produced submission."""
        sub_path = self.output_dir / "submission.json"
        return verify_submission(sub_path, self.data_dir)

    def evaluate(self, solution_path: Path | None = None) -> dict[str, Any]:
        """Score submission against known solutions (if available)."""
        if solution_path is None:
            solution_path = self.data_dir / "arc-agi_evaluation_solutions.json"
        sub_path = self.output_dir / "submission.json"
        if not sub_path.exists() or not solution_path.exists():
            return {"error": "submission or solutions missing", "correct": 0, "total": 0}
        sub = json.loads(sub_path.read_text())
        sols = json.loads(solution_path.read_text())
        correct = 0
        total = 0
        for tid, preds in sub.items():
            if tid not in sols:
                continue
            gold = sols[tid]
            for pi, pred in enumerate(preds):
                if pi >= len(gold):
                    break
                total += 1
                # Compare attempt_1 (or attempt_2) against gold
                if "attempt_1" in pred and grids_equal(pred["attempt_1"], gold[pi]):
                    correct += 1
        return {
            "track": self.TRACK_NAME,
            "correct": correct,
            "total": total,
            "accuracy": round(correct / max(total, 1), 4),
        }

    def package(self, extra_files: list[Path] | None = None) -> Path:
        """Create submission_package.zip with manifest and provenance."""
        return self.builder.package(extra_files=extra_files)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="ARC-AGI-2 Static Track Pipeline")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--budget", type=int, default=5000)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--llm-fallback", action="store_true")
    parser.add_argument("--llm-fallback-path", type=Path, default=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--solution-path", type=Path, default=None)
    args = parser.parse_args()

    pipe = ARCAGI2Pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        max_depth=args.max_depth,
        budget=args.budget,
        top_k_rules=args.top_k,
        use_llm_fallback=args.llm_fallback,
        llm_fallback_path=args.llm_fallback_path,
    )
    summary = pipe.run()
    print(json.dumps(summary, indent=2))

    if args.verify:
        vres = pipe.verify()
        print(json.dumps(vres, indent=2))
        if not vres.get("valid"):
            sys.exit(1)

    if args.evaluate:
        eres = pipe.evaluate(solution_path=args.solution_path)
        print(json.dumps(eres, indent=2))
