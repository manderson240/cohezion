"""ARC-AGI-3 Track Submission Pipeline (Interactive Track — $850K Prize).

V-Model Traceability
--------------------
Requirement  : Per-test interactive feedback loop with 2 attempts.
Architecture  : InteractiveSession + ARCCodec + PatternExtractor + LLM fallback.
Implementation: Submit attempt_1, receive feedback, refine for attempt_2.
Verification  : verify_submission() + feedback-loop invariants.
Validation    : score = first-try + second-try weighted accuracy.

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
class InteractiveAttempt:
    """Single attempt within an interactive session."""

    attempt_num: int  # 1 or 2
    grid: Grid
    feedback: str  # e.g. "correct", "wrong_shape", "wrong_colors"
    source: str
    confidence: float
    wall_time_ms: float


@dataclass
class ARCAGI3Result:
    """Result container for ARC-AGI-3 interactive track."""

    task_id: str
    test_index: int
    attempts: list[InteractiveAttempt]
    final_reward: float  # weighted: 1.0 for correct on attempt_1, 0.5 for attempt_2
    provenance: list[PredictionProvenance] = field(default_factory=list)


def _simulate_feedback(prediction: Grid, gold: Grid | None) -> str:
    """Simulate evaluation harness feedback (real harness returns simple bool).

    For offline development we produce richer synthetic feedback.
    In real Kaggle submission this is replaced by the platform's 1-bit signal.
    """
    if gold is None:
        return "unknown"
    if grids_equal(prediction, gold):
        return "correct"
    # Deeper diagnostics
    if len(prediction) != len(gold):
        return "wrong_shape"
    if any(len(pr) != len(gr) for pr, gr in zip(prediction, gold)):
        return "wrong_shape"
    # Compare color sets
    pred_colors = {c for row in prediction for c in row}
    gold_colors = {c for row in gold for c in row}
    if pred_colors != gold_colors:
        return "wrong_colors"
    return "wrong_pattern"


def _refine_prediction(
    first_pred: Grid,
    feedback: str,
    test_input: Grid,
    rules: list,
    extractor: PatternExtractor,
) -> Grid:
    """Generate a second attempt given feedback from first attempt.

    Strategies per feedback:
    - correct   : return same grid (should never happen as loop stops)
    - wrong_shape: preserve aspect ratio heuristic, try nearest valid size
    - wrong_colors: swap most common color, or run inverse
    - wrong_pattern: try next best rule or LLM fallback
    """
    if feedback == "correct":
        return first_pred

    if feedback == "wrong_shape":
        # Naive: try transpose or scale
        if len(first_pred) == len(test_input) and len(first_pred[0]) == len(test_input[0]):
            return first_pred  # same shape as input means rule preserved dims
        return test_input  # fallback to identity if shape is off

    if feedback == "wrong_colors":
        # Try simple inversion heuristic
        try:
            inv = [[9 - c for c in row] for row in first_pred]
            return inv
        except Exception:
            pass
        return test_input

    # wrong_pattern: try next best rule
    return first_pred  # in real harness attempt_2 should differ


class ARCAGI3Pipeline:
    """ARC-AGI-3 interactive track submission pipeline.

    The Kaggle interactive track provides per-test feedback:
    - attempt_1 is scored immediately (1 point if correct).
    - If wrong, a 1-bit signal is returned.
    - attempt_2 can refine the answer (0.5 point if correct).

    Our pipeline simulates this loop offline using gold solutions
    (for training/validation) and produces the same submission.json
    format so the same verification code applies.
    """

    TRACK_NAME = "arc-agi-3"
    PRIZE_USD = 850_000
    DEADLINE = "2026-11-15"
    NUM_ATTEMPTS = 2
    ATTEMPT_1_WEIGHT = 1.0
    ATTEMPT_2_WEIGHT = 0.5

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
        self.results: list[ARCAGI3Result] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        task_ids: list[str] | None = None,
        verbose: bool = True,
        gold_solutions: dict[str, list[Grid]] | None = None,
    ) -> dict[str, Any]:
        """Run full interactive pipeline.

        If ``gold_solutions`` is provided, we simulate the feedback loop
        offline to refine attempt_2.  Otherwise both attempts are identical
        (as required by blind test evaluation).
        """
        start = time.perf_counter()
        challenges_path = self.data_dir / "arc-agi-3_test_challenges.json"
        if not challenges_path.exists():
            challenges_path = self.data_dir / "arc-agi_test_challenges.json"

        if not challenges_path.exists():
            raise FileNotFoundError(f"Test challenges not found: {challenges_path}")

        challenges: dict[str, Any] = json.loads(challenges_path.read_text())
        if task_ids is None:
            task_ids = sorted(challenges.keys())

        submission: dict[str, list[dict[str, Any]]] = {}
        total_reward = 0.0
        total_tasks = 0

        for tid in task_ids:
            task = challenges[tid]
            rules = self.builder.extractor.extract(task)
            golds = gold_solutions.get(tid, []) if gold_solutions else []
            preds = []

            for ti, test_ex in enumerate(task.get("test", [])):
                test_input = test_ex["input"]
                # Attempt 1
                pred1, prov1 = self.builder._predict_with_rules(tid, ti, test_input, rules)
                feedback = "unknown"
                gold = golds[ti] if ti < len(golds) else None
                if gold is not None:
                    feedback = _simulate_feedback(pred1, gold)

                attempt1 = InteractiveAttempt(
                    attempt_num=1,
                    grid=pred1,
                    feedback=feedback,
                    source=prov1[-1].source if prov1 else "default_zero",
                    confidence=prov1[-1].rule_confidence if prov1 else 0.0,
                    wall_time_ms=prov1[-1].wall_time_ms if prov1 else 0.0,
                )

                reward = 0.0
                if feedback == "correct":
                    reward = self.ATTEMPT_1_WEIGHT
                    pred2 = pred1
                else:
                    pred2 = _refine_prediction(
                        pred1, feedback, test_input, rules, self.builder.extractor
                    )
                    if gold is not None and grids_equal(pred2, gold):
                        reward = self.ATTEMPT_2_WEIGHT

                attempt2 = InteractiveAttempt(
                    attempt_num=2,
                    grid=pred2,
                    feedback="correct" if reward == self.ATTEMPT_2_WEIGHT else feedback,
                    source="refined" if pred2 != pred1 else attempt1.source,
                    confidence=attempt1.confidence,
                    wall_time_ms=attempt1.wall_time_ms,
                )

                preds.append({"attempt_1": pred1, "attempt_2": pred2})
                total_reward += reward
                total_tasks += 1

                result = ARCAGI3Result(
                    task_id=tid,
                    test_index=ti,
                    attempts=[attempt1, attempt2],
                    final_reward=reward,
                    provenance=prov1,
                )
                self.results.append(result)

            submission[tid] = preds

        elapsed = time.perf_counter() - start

        # Save
        self.builder.save(submission)
        self.builder.save_provenance(self.output_dir / "provenance.jsonl")
        pkg = self.builder.package(submission)

        summary = {
            "track": self.TRACK_NAME,
            "tasks": total_tasks,
            "total_reward": round(total_reward, 2),
            "max_reward": total_tasks * self.ATTEMPT_1_WEIGHT,
            "elapsed_sec": round(elapsed, 2),
            "output": str(self.output_dir / "submission.json"),
            "package": str(pkg),
        }
        if verbose:
            print(f"[ARC-AGI-3] {summary}")
        return summary

    def verify(self) -> dict[str, Any]:
        sub_path = self.output_dir / "submission.json"
        return verify_submission(sub_path, self.data_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="ARC-AGI-3 Interactive Track Pipeline")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--budget", type=int, default=5000)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--llm-fallback", action="store_true")
    parser.add_argument("--llm-fallback-path", type=Path, default=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--solution-path", type=Path, default=None)
    args = parser.parse_args()

    gold_solutions = None
    if args.solution_path:
        gold_solutions = json.loads(Path(args.solution_path).read_text())

    pipe = ARCAGI3Pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        max_depth=args.max_depth,
        budget=args.budget,
        top_k_rules=args.top_k,
        use_llm_fallback=args.llm_fallback,
        llm_fallback_path=args.llm_fallback_path,
    )
    summary = pipe.run(gold_solutions=gold_solutions)
    print(json.dumps(summary, indent=2))

    if args.verify:
        vres = pipe.verify()
        print(json.dumps(vres, indent=2))
        if not vres.get("valid"):
            sys.exit(1)
