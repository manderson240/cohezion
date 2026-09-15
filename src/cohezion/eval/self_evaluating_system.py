"""Self-Evaluating AI System — Automated testing and evaluation pipelines.

Implements the three-layer evaluation framework:
  1. Layer 1: Fast, deterministic rule-based checks (syntax, schema, length, URLs, refusals).
  2. Layer 2: LLM-as-judge evaluation with anchor rubrics and multi-judge consensus
     via local Lemonade OmniRouter (:13305, $0 cloud cost) or configured endpoints.
  3. Layer 3: Human evaluation loop, inter-annotator agreement (Cohen's Kappa),
     and judge drift calibration.
  4. Golden dataset regression testing and paired t-test statistical significance
     verification before deployment.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Result of a single deterministic evaluation check."""

    check_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: str


@dataclass
class JudgeResult:
    """Result of an LLM-as-judge evaluation."""

    criterion: str
    score: int  # 1 to 5
    max_score: int
    reasoning: str


@dataclass
class GoldenExample:
    """A test case in a golden evaluation dataset."""

    id: str
    question: str
    reference_answer: str
    category: str
    difficulty: str  # "easy", "medium", "hard"
    criteria: list[str] = field(default_factory=lambda: ["relevance", "accuracy", "completeness"])


@dataclass
class EvalRun:
    """Telemetry and metrics for a completed evaluation run."""

    run_id: str
    timestamp: str
    model: str
    prompt_version: str
    total_examples: int
    avg_scores: dict[str, float]
    pass_rate: float
    failures: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Layer 1: Deterministic Checks
# ---------------------------------------------------------------------------


class DeterministicEvaluator:
    """Layer 1: Fast, zero-cost rule-based checks for model outputs."""

    def check_json_validity(self, output: str) -> EvalResult:
        """Verify the output is parseable JSON when expected."""
        try:
            json.loads(output)
            return EvalResult("json_validity", True, 1.0, "Valid JSON")
        except json.JSONDecodeError as exc:
            return EvalResult("json_validity", False, 0.0, f"Invalid JSON: {exc}")

    def check_length_bounds(
        self, output: str, min_chars: int = 10, max_chars: int = 50000
    ) -> EvalResult:
        """Verify output length falls within operational bounds."""
        length = len(output)
        if length < min_chars:
            return EvalResult(
                "length_bounds",
                False,
                0.0,
                f"Too short: {length} chars (minimum: {min_chars})",
            )
        if length > max_chars:
            return EvalResult(
                "length_bounds",
                False,
                0.0,
                f"Too long: {length} chars (maximum: {max_chars})",
            )
        return EvalResult("length_bounds", True, 1.0, f"Length OK: {length} chars")

    def check_no_hallucinated_links(self, output: str) -> EvalResult:
        """Detect potentially fabricated URLs in output."""
        url_pattern = r"https?://[^\s\)\]\}\"\'<>]+"
        urls = re.findall(url_pattern, output)
        if urls:
            return EvalResult(
                "no_hallucinated_links",
                False,
                0.0,
                f"Found {len(urls)} URLs that may be unverified: {urls[:3]}",
            )
        return EvalResult("no_hallucinated_links", True, 1.0, "No URLs detected")

    def check_required_sections(self, output: str, required: list[str]) -> EvalResult:
        """Verify required section headers or keywords appear in output."""
        missing = [s for s in required if s.lower() not in output.lower()]
        if missing:
            score = 1.0 - (len(missing) / len(required))
            return EvalResult(
                "required_sections",
                False,
                round(score, 3),
                f"Missing sections: {missing}",
            )
        return EvalResult("required_sections", True, 1.0, "All required sections present")

    def check_no_refusal(self, output: str) -> EvalResult:
        """Detect if the model refused to answer when it should have executed."""
        refusal_phrases = [
            "i cannot",
            "i can't",
            "i'm unable to",
            "as an ai",
            "i don't have access",
            "i am not able to",
        ]
        output_lower = output.lower()
        for phrase in refusal_phrases:
            if phrase in output_lower:
                return EvalResult(
                    "no_refusal",
                    False,
                    0.0,
                    f"Possible refusal detected: '{phrase}'",
                )
        return EvalResult("no_refusal", True, 1.0, "No refusal detected")

    def check_code_syntax(self, output: str, language: str = "python") -> EvalResult:
        """Verify python code blocks inside output parse without SyntaxError."""
        if language.lower() != "python":
            return EvalResult("code_syntax", True, 1.0, "Language syntax check skipped")

        # Extract code blocks
        code_blocks = re.findall(r"```(?:python)?\s*\n(.*?)\n```", output, re.DOTALL)
        if not code_blocks:
            # If no fenced code block, try parsing the whole output if it looks like code
            if any(kw in output for kw in ["def ", "class ", "import "]):
                code_blocks = [output]
            else:
                return EvalResult("code_syntax", True, 1.0, "No code blocks detected")

        for idx, block in enumerate(code_blocks):
            try:
                ast.parse(block)
            except SyntaxError as err:
                return EvalResult(
                    "code_syntax",
                    False,
                    0.0,
                    f"SyntaxError in code block {idx + 1} line {err.lineno}: {err.msg}",
                )

        return EvalResult(
            "code_syntax",
            True,
            1.0,
            f"All {len(code_blocks)} code blocks parsed cleanly",
        )

    def run_all(self, output: str, config: dict[str, Any] | None = None) -> list[EvalResult]:
        """Run all configured deterministic checks."""
        cfg = config or {}
        results = [
            self.check_length_bounds(
                output,
                cfg.get("min_chars", 10),
                cfg.get("max_chars", 50000),
            ),
            self.check_no_refusal(output),
        ]
        if cfg.get("disallow_urls", True):
            results.append(self.check_no_hallucinated_links(output))
        if cfg.get("expect_json"):
            results.append(self.check_json_validity(output))
        if cfg.get("required_sections"):
            results.append(self.check_required_sections(output, cfg["required_sections"]))
        if cfg.get("check_syntax", True):
            results.append(self.check_code_syntax(output))

        return results


# ---------------------------------------------------------------------------
# Layer 2: LLM-as-Judge with Rubrics & Consensus
# ---------------------------------------------------------------------------

RUBRICS: dict[str, dict[str, Any]] = {
    "relevance": {
        "description": "Does the response directly and specifically address the user's prompt?",
        "levels": {
            1: "Completely off-topic or addresses a different question entirely.",
            2: "Tangentially related but misses the core query.",
            3: "Addresses the question but includes significant extraneous or irrelevant material.",
            4: "Directly addresses the question with only minor tangents.",
            5: "Precisely, concisely, and completely addresses the prompt.",
        },
    },
    "accuracy": {
        "description": "Is the factual, technical, and mathematical content of the response correct?",
        "levels": {
            1: "Contains critical factual or algorithmic errors that mislead the user.",
            2: "Multiple technical errors on core points.",
            3: "Mostly accurate but contains at least one notable flaw or unverified claim.",
            4: "Accurate with only trivial imprecisions.",
            5: "Completely accurate, mathematically verified, and free of defects.",
        },
    },
    "completeness": {
        "description": "Does the response cover all required constraints, edge cases, and components?",
        "levels": {
            1: "Addresses less than 20% of the prompt requirements.",
            2: "Covers some aspects but misses major functional components.",
            3: "Covers standard flow but lacks depth on edge cases or error handling.",
            4: "Comprehensive coverage with minor non-blocking gaps.",
            5: "Exhaustive coverage including edge cases, constraints, and validation.",
        },
    },
    "code_correctness": {
        "description": "Is the generated code syntactically sound, type-safe, and bug-free?",
        "levels": {
            1: "Fails to parse or execute; critical syntax or runtime failures.",
            2: "Executes partially but contains logic bugs or missing imports.",
            3: "Functional for happy path, but brittle under edge cases or missing type hints.",
            4: "Well-structured, robust, and type-hinted with minor stylistic points.",
            5: "Optimal, clean, strictly typed, passes linters and edge-case unit tests.",
        },
    },
}


class LocalLLMJudge:
    """Layer 2: Uses local silicon model (or configured endpoint) to grade responses."""

    def __init__(
        self,
        endpoint_url: str = "http://localhost:13305/v1/chat/completions",
        model: str = "user.cohezion-router",
        timeout: float = 60.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.model = model
        self.timeout = timeout

    def evaluate(
        self,
        question: str,
        response: str,
        criterion: str,
        rubrics: dict[str, dict[str, Any]] | None = None,
    ) -> JudgeResult:
        """Evaluate a single response against a single criterion rubric."""
        active_rubrics = rubrics or RUBRICS
        if criterion not in active_rubrics:
            raise ValueError(
                f"Unknown criterion '{criterion}'. Available: {list(active_rubrics.keys())}"
            )

        rubric = active_rubrics[criterion]
        levels_text = "\n".join(
            f"Score {score}: {desc}" for score, desc in sorted(rubric["levels"].items())
        )

        prompt = f"""You are an expert impartial evaluation judge. Your task is to score an AI system's response.

CRITERION: {rubric["description"]}

SCORING RUBRIC:
{levels_text}

USER PROMPT:
{question}

AI RESPONSE:
{response}

Score the response strictly based on the rubric above.
Respond ONLY with a JSON object in this exact format:
{{"score": <integer 1-5>, "reasoning": "<2-3 sentence factual justification>"}}"""

        import httpx

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(
                    self.endpoint_url,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.0,
                        "response_format": {"type": "json_object"},
                    },
                )
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                # Parse JSON response
                parsed = json.loads(content)
                score = int(parsed.get("score", 3))
                score = max(1, min(5, score))
                reasoning = parsed.get("reasoning", "No reasoning provided.")
                return JudgeResult(
                    criterion=criterion,
                    score=score,
                    max_score=5,
                    reasoning=reasoning,
                )
        except Exception as exc:
            logger.warning("LocalLLMJudge call failed (%s): %s", criterion, exc)
            return JudgeResult(
                criterion=criterion,
                score=3,
                max_score=5,
                reasoning=f"Judge evaluation failed ({exc}); defaulted to neutral score 3.",
            )

    def evaluate_all(
        self,
        question: str,
        response: str,
        criteria: list[str] | None = None,
    ) -> list[JudgeResult]:
        """Evaluate a response across multiple criteria."""
        active_criteria = criteria or ["relevance", "accuracy", "completeness"]
        return [self.evaluate(question, response, c) for c in active_criteria]

    def evaluate_with_consensus(
        self,
        question: str,
        response: str,
        criterion: str,
        num_judges: int = 3,
    ) -> JudgeResult:
        """Run multi-judge evaluation and return median score for variance stability."""
        results = [self.evaluate(question, response, criterion) for _ in range(num_judges)]
        scores = [r.score for r in results]
        median_score = int(np.median(scores))
        closest_result = min(results, key=lambda r: abs(r.score - median_score))
        return JudgeResult(
            criterion=criterion,
            score=median_score,
            max_score=5,
            reasoning=f"Consensus median {median_score} from scores {scores}: {closest_result.reasoning}",
        )


# ---------------------------------------------------------------------------
# Layer 3: Human Calibration & Inter-Annotator Agreement
# ---------------------------------------------------------------------------


def measure_cohens_kappa(
    scores_1: list[int],
    scores_2: list[int],
) -> dict[str, Any]:
    """Calculate inter-annotator agreement using Cohen's Kappa.

    Adjusts for chance agreement. Values > 0.6 indicate substantial agreement;
    values < 0.4 indicate ambiguous rubrics requiring refinement.
    """
    if len(scores_1) != len(scores_2) or len(scores_1) < 2:
        raise ValueError("Both score sets must be non-empty and equal length >= 2.")

    from sklearn.metrics import cohen_kappa_score

    kappa = float(cohen_kappa_score(scores_1, scores_2))

    if kappa > 0.8:
        interpretation = "almost perfect"
    elif kappa > 0.6:
        interpretation = "substantial"
    elif kappa > 0.4:
        interpretation = "moderate"
    elif kappa > 0.2:
        interpretation = "fair"
    else:
        interpretation = "poor"

    exact_agreement = sum(a == b for a, b in zip(scores_1, scores_2)) / len(scores_1)

    return {
        "cohens_kappa": round(kappa, 4),
        "interpretation": interpretation,
        "exact_agreement": round(float(exact_agreement), 4),
        "sample_size": len(scores_1),
    }


def check_judge_drift(
    human_ground_truth: list[float],
    judge_scores: list[float],
    drift_threshold: float = 0.5,
) -> dict[str, Any]:
    """Detect if automated judge has drifted from human calibration ground truth."""
    if len(human_ground_truth) != len(judge_scores) or not human_ground_truth:
        raise ValueError("Ground truth and judge scores must have matching positive lengths.")

    diffs = [abs(h - j) for h, j in zip(human_ground_truth, judge_scores)]
    mean_abs_error = float(np.mean(diffs))
    has_drifted = mean_abs_error > drift_threshold

    return {
        "mean_abs_error": round(mean_abs_error, 4),
        "drift_threshold": drift_threshold,
        "has_drifted": has_drifted,
        "status": "RECALIBRATE_JUDGE" if has_drifted else "CALIBRATED",
    }


# ---------------------------------------------------------------------------
# Golden Dataset & Regression Pipeline
# ---------------------------------------------------------------------------


class GoldenDataset:
    """Manages a persistent, curated evaluation dataset."""

    def __init__(self, filepath: str | Path = "golden_dataset.json") -> None:
        self.filepath = Path(filepath)
        self.examples: list[GoldenExample] = []
        if self.filepath.exists():
            self.load()

    def add(self, example: GoldenExample) -> None:
        """Add an example and persist."""
        self.examples.append(example)
        self.save()

    def save(self) -> None:
        """Persist examples to disk."""
        data = [asdict(e) for e in self.examples]
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        """Load examples from disk."""
        content = self.filepath.read_text(encoding="utf-8")
        data = json.loads(content)
        self.examples = [GoldenExample(**item) for item in data]

    def summary(self) -> dict[str, Any]:
        """Return dataset breakdown statistics."""
        categories: dict[str, int] = {}
        for e in self.examples:
            categories[e.category] = categories.get(e.category, 0) + 1
        return {
            "total_examples": len(self.examples),
            "categories": categories,
        }


def is_improvement_significant(
    scores_before: list[float],
    scores_after: list[float],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Test whether score change across paired test cases is statistically significant.

    Uses a paired t-test (scipy.stats.ttest_rel) comparing the same question instances.
    """
    if len(scores_before) != len(scores_after) or len(scores_before) < 2:
        raise ValueError("Paired t-test requires identical non-empty score sets (n >= 2).")

    diffs = np.array(scores_after) - np.array(scores_before)
    mean_diff = float(np.mean(diffs))

    # Check for zero variance
    if np.all(diffs == 0):
        return {
            "mean_before": round(float(np.mean(scores_before)), 3),
            "mean_after": round(float(np.mean(scores_after)), 3),
            "mean_difference": 0.0,
            "t_statistic": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "direction": "unchanged",
            "recommendation": "Scores are identical across runs.",
        }

    t_stat, p_val = stats.ttest_rel(scores_after, scores_before)
    p_value = float(p_val)
    t_statistic = float(t_stat)
    is_sig = bool(p_value < alpha and mean_diff > 0)

    direction = "improvement" if mean_diff > 0 else ("regression" if mean_diff < 0 else "neutral")

    recommendation = (
        "Statistically significant improvement (p < alpha) — safe to deploy"
        if is_sig
        else (
            "Regression detected — do not deploy"
            if mean_diff < 0 and p_value < alpha
            else "Not statistically significant — improvement may be noise"
        )
    )

    return {
        "mean_before": round(float(np.mean(scores_before)), 3),
        "mean_after": round(float(np.mean(scores_after)), 3),
        "mean_difference": round(mean_diff, 3),
        "t_statistic": round(t_statistic, 4),
        "p_value": round(p_value, 4),
        "is_significant": is_sig,
        "direction": direction,
        "recommendation": recommendation,
    }


class RegressionPipeline:
    """Runs evaluation sweeps against golden datasets and detects regressions."""

    def __init__(
        self,
        deterministic_eval: DeterministicEvaluator | None = None,
        llm_judge: LocalLLMJudge | None = None,
        score_threshold: float = 3.5,
    ) -> None:
        self.det_eval = deterministic_eval or DeterministicEvaluator()
        self.judge = llm_judge or LocalLLMJudge()
        self.threshold = score_threshold

    def run_sweep(
        self,
        dataset: GoldenDataset,
        generate_fn: Callable[[str], str],
        model_name: str,
        prompt_version: str,
    ) -> EvalRun:
        """Run full evaluation sweep across dataset."""
        all_scores: dict[str, list[float]] = {}
        failures: list[dict[str, Any]] = []

        for example in dataset.examples:
            response = generate_fn(example.question)

            # Layer 1: Deterministic checks
            det_results = self.det_eval.run_all(response)
            det_failures = [r for r in det_results if not r.passed]

            if det_failures:
                failures.append(
                    {
                        "id": example.id,
                        "question": example.question,
                        "layer": "deterministic",
                        "details": [r.details for r in det_failures],
                    }
                )
                continue

            # Layer 2: LLM judge checks
            judge_results = self.judge.evaluate_all(example.question, response, example.criteria)

            for result in judge_results:
                if result.criterion not in all_scores:
                    all_scores[result.criterion] = []
                all_scores[result.criterion].append(float(result.score))

                if result.score < self.threshold:
                    failures.append(
                        {
                            "id": example.id,
                            "question": example.question,
                            "layer": "llm_judge",
                            "criterion": result.criterion,
                            "score": result.score,
                            "reasoning": result.reasoning,
                        }
                    )

        avg_scores = {
            crit: round(sum(vals) / len(vals), 3) for crit, vals in all_scores.items() if vals
        }
        total_eval = len(dataset.examples)
        pass_count = total_eval - len(failures)
        pass_rate = round(pass_count / total_eval, 4) if total_eval > 0 else 0.0

        return EvalRun(
            run_id=f"eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(UTC).isoformat(),
            model=model_name,
            prompt_version=prompt_version,
            total_examples=total_eval,
            avg_scores=avg_scores,
            pass_rate=pass_rate,
            failures=failures,
        )

    def compare_runs(self, baseline: EvalRun, current: EvalRun) -> dict[str, Any]:
        """Compare two evaluation runs to detect performance regressions."""
        regressions: dict[str, dict[str, float]] = {}
        improvements: dict[str, dict[str, float]] = {}

        for crit, curr_score in current.avg_scores.items():
            if crit in baseline.avg_scores:
                base_score = baseline.avg_scores[crit]
                delta = curr_score - base_score
                if delta < -0.2:  # Regressed by more than 0.2 points
                    regressions[crit] = {
                        "baseline": base_score,
                        "current": curr_score,
                        "delta": round(delta, 3),
                    }
                elif delta > 0.2:  # Improved by more than 0.2 points
                    improvements[crit] = {
                        "baseline": base_score,
                        "current": curr_score,
                        "delta": round(delta, 3),
                    }

        verdict = "REGRESSION" if regressions else "PASS"

        return {
            "verdict": verdict,
            "regressions": regressions,
            "improvements": improvements,
            "pass_rate_delta": round(current.pass_rate - baseline.pass_rate, 4),
        }


# ---------------------------------------------------------------------------
# Complete Unified Orchestrator
# ---------------------------------------------------------------------------


class SelfEvaluatingOrchestrator:
    """Master orchestrator connecting all three layers with SurrealDB telemetry."""

    def __init__(
        self,
        endpoint_url: str = "http://localhost:13305/v1/chat/completions",
        judge_model: str = "user.cohezion-router",
        surreal_url: str = "http://localhost:8001",
    ) -> None:
        self.det_eval = DeterministicEvaluator()
        self.judge = LocalLLMJudge(endpoint_url=endpoint_url, model=judge_model)
        self.surreal_url = surreal_url

    def evaluate_output(
        self,
        question: str,
        response: str,
        criteria: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run full evaluation pipeline on a single response."""
        # Layer 1: Deterministic check
        det_results = self.det_eval.run_all(response, config=config)
        det_passed = all(r.passed for r in det_results)

        if not det_passed:
            failed_checks = [asdict(r) for r in det_results if not r.passed]
            return {
                "status": "FAIL",
                "layer": "deterministic",
                "score": 0.0,
                "details": failed_checks,
                "recommendation": "Resolve structural/syntax issues before semantic evaluation.",
            }

        # Layer 2: LLM Judge
        judge_results = self.judge.evaluate_all(question, response, criteria=criteria)
        avg_score = float(np.mean([r.score for r in judge_results]))

        status = "PASS" if avg_score >= 3.5 else "FAIL"

        return {
            "status": status,
            "layer": "llm_judge",
            "score": round(avg_score, 2),
            "details": [asdict(r) for r in judge_results],
            "recommendation": (
                "Response meets quality thresholds."
                if status == "PASS"
                else "Quality below 3.5 threshold; refine prompt or model reasoning."
            ),
        }
