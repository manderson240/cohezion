"""Skill refiner for learning from execution results and improving PRIME skills.

The SkillRefiner learns from successful executions and appends refinements
to PRIME skill definition files. It analyzes execution metrics (tokens,
latency, quality scores) and updates skill instructions with learned patterns.

Features:
- Extract learning signals from execution results
- Analyze token efficiency and quality metrics
- Append learned refinements to PRIME .md files
- Bump version numbers for refined skills
- Non-blocking persistence (failures don't crash execution)
"""

import logging
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# MGPO: VaultNeuronWriter must be importable at module level so tests can mock
# `cohezion.compound.skill_refiner.VaultNeuronWriter` directly.
try:
    from cohezion.learning.vault_neuron_reader import VaultNeuronWriter
except ImportError:
    VaultNeuronWriter = None  # type: ignore[assignment,misc]


logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics extracted from execution result."""

    success: bool
    duration_seconds: float
    tokens_used: int
    token_efficiency: float
    quality_score: float
    anomaly_score: float
    cached_hits: int
    tokens_per_task: int = 0
    tier_used: str = "unknown"
    tool_call_count: int = 0
    escalation_count: int = 0
    prediction_error: float | None = None


@dataclass
class LearningSignal:
    """Learning insight extracted from execution."""

    skill_name: str
    operation_type: str
    key_insight: str
    metric_change: str
    recommendation: str
    confidence: float


@dataclass
class SkillRefinementInput:
    """Input for skill refinement from external systems (TDD, Adversarial)."""

    skill_name: str
    performance_metric: float
    feedback: str
    context: dict[str, Any]


class EnvironmentResponsePredictor:
    """Lightweight world model: predicts next quality given (skill, op_type) history.

    Maintains a rolling window of quality scores per (skill_name, operation_type) key
    and generates ENVIRONMENT_SURPRISE signals when actual quality deviates from the
    rolling mean by more than the surprise_threshold. Inspired by the Qwen-AgentWorld
    pattern of tracking environment response distributions to detect non-stationarity.
    """

    def __init__(self, window_size: int = 10, surprise_threshold: float = 0.2) -> None:
        self._history: dict[tuple[str, str], deque[float]] = {}
        self._window_size = window_size
        self._surprise_threshold = surprise_threshold
        # FAPO R3: optional run_fn(candidate_prompt, fixture_input) -> output for the behavioral
        # regression gate. None = gate fail-open (drift gate still applies). Set by the factory.
        self._regression_run_fn = None

    def predict(self, skill_name: str, operation_type: str) -> float | None:
        """Return rolling-mean quality prediction, or None if no history yet."""
        key = (skill_name, operation_type)
        window = self._history.get(key)
        if not window:
            return None
        return sum(window) / len(window)

    def prediction_error(self, skill_name: str, operation_type: str, actual: float) -> float | None:
        """Return (actual − predicted), or None if no history."""
        predicted = self.predict(skill_name, operation_type)
        return (actual - predicted) if predicted is not None else None

    def record(self, skill_name: str, operation_type: str, quality: float) -> None:
        """Append quality to the rolling window for this (skill, op_type) pair."""
        key = (skill_name, operation_type)
        if key not in self._history:
            self._history[key] = deque(maxlen=self._window_size)
        self._history[key].append(quality)

    def is_surprising(self, skill_name: str, operation_type: str, actual: float) -> bool:
        """Return True when |actual − predicted| > surprise_threshold."""
        err = self.prediction_error(skill_name, operation_type, actual)
        return err is not None and abs(err) > self._surprise_threshold


class SkillRefiner:
    """Refines PRIME skill definitions based on execution results."""

    SKILLS_DIR = Path(__file__).parent.parent / "skills"

    def __init__(self, mcp_client: Any = None):
        """Initialize skill refiner.

        Args:
            mcp_client: Optional MCPClient for vault operations
        """
        self.mcp_client = mcp_client
        self._env_predictor = EnvironmentResponsePredictor()
        # #118: per-skill rolling window of prediction errors (process rewards)
        self._process_rewards: dict[str, deque[float]] = {}
        # #93: predictive tier estimator (closes tier_used producer→consumer gap)
        from cohezion.compound.difficulty_estimator import DifficultyEstimator

        self._difficulty_estimator = DifficultyEstimator()

        # #136: Self-directed learning goal state (GIC agentive — arXiv 2606.23991).
        # Internally held across the session; updated by set_goal() or _auto_update_goal().
        # Factors into _generate_recommendation(): goal-aligned perspective gets priority.
        self._session_goal: dict | None = None
        self._goal_call_tally: dict[str, int] = {}  # per-skill call counter for auto-update
        self._goal_auto_threshold: int = 5  # auto-update goal every N calls per skill

    def process_reward_mean(self, skill_name: str) -> float | None:
        """Return mean accumulated RL process reward for a skill, or None if no data.

        Positive mean → skill quality exceeds its own prediction (underestimated).
        Negative mean → skill quality falls short of prediction (overestimated).
        """
        window = self._process_rewards.get(skill_name)
        return float(sum(window) / len(window)) if window else None

    def _accumulate_process_reward(self, skill_name: str, pred_err: float | None) -> None:
        """Append prediction error to per-skill process reward accumulator (window=20)."""
        if pred_err is None:
            return
        if skill_name not in self._process_rewards:
            self._process_rewards[skill_name] = deque(maxlen=20)
        self._process_rewards[skill_name].append(pred_err)

    def mgpo_weight(self, skill_name: str, gamma: float = 5.0) -> float:
        """MGPO boundary weight: w = exp(-γ * |success_rate - 0.5|).

        Returns 1.0 (maximum priority) when no data is available — treat unexplored
        skills as operating at the boundary where learning is most efficient.

        Biased by accumulated RL process rewards: consistent positive surprises
        (skill quality > prediction) shift the effective success_rate toward 0.5,
        increasing the boundary weight and raising skill priority.
        """
        import math

        try:
            if VaultNeuronWriter is None:
                return 1.0
            vnw = VaultNeuronWriter.get_instance()
            sr = vnw.query_category_success_rate(skill_name)
            if sr is None:
                return 1.0
            # #118: bias success_rate toward 0.5 by accumulated process reward.
            # Positive mean reward (quality > prediction) → skill is underestimated →
            # nudge sr toward boundary.  Scale factor 0.1 keeps nudge conservative.
            reward_mean = self.process_reward_mean(skill_name)
            if reward_mean is not None:
                sr = max(0.0, min(1.0, sr - 0.1 * reward_mean))
            return math.exp(-gamma * abs(sr - 0.5))
        except Exception:
            return 1.0

    def prioritized_skills(self, skill_names: list[str], gamma: float = 5.0) -> list[str]:
        """Return skill_names sorted descending by mgpo_weight (boundary-first ordering)."""
        return sorted(skill_names, key=lambda s: self.mgpo_weight(s, gamma), reverse=True)

    # ------------------------------------------------------------------
    # #136: Session goal state — GIC agentive Goal internalization
    # ------------------------------------------------------------------

    def set_goal(self, objective: str, target_metric: str = "quality_score") -> None:
        """Set the active session goal, overriding any auto-derived goal."""
        self._session_goal = {
            "objective": objective,
            "target_metric": target_metric,
        }

    def get_goal(self) -> dict | None:
        """Return the current session goal, or None if not set."""
        return self._session_goal

    def _auto_update_goal(self, skill_name: str, metrics: "ExecutionMetrics") -> None:
        """Propose a session goal after N consistently problematic executions (#136).

        Analyzes execution pattern over `_goal_auto_threshold` calls per skill
        and sets a goal targeting the most problematic metric.
        Priority: quality_score < 0.5 first, then escalation_count > 0.
        """
        tally = self._goal_call_tally.get(skill_name, 0) + 1
        self._goal_call_tally[skill_name] = tally
        if tally < self._goal_auto_threshold:
            return
        # Reset so it fires again after the next N calls.
        self._goal_call_tally[skill_name] = 0
        if metrics.quality_score < 0.5:
            self._session_goal = {
                "objective": "improve quality_score",
                "target_metric": "quality_score",
            }
        elif getattr(metrics, "escalation_count", 0) > 0:
            self._session_goal = {
                "objective": "reduce tier escalation",
                "target_metric": "escalation_count",
            }

    def skill_proximity(self, skill_a: str, skill_b: str) -> float:
        """#102: lineage-based skill proximity — CSHL brain development analogy.

        Skills that handle overlapping operation types with similar quality
        profiles are 'nearby' in skill space.  Proximity is the Jaccard
        similarity over shared operation-type keys scaled by mean-quality
        agreement (1 − |Δq|/2).

        Returns a float in [0.0, 1.0]:
          1.0 → identical op-type sets with identical mean quality
          0.0 → disjoint op-type sets or one skill has no history

        Consumes ERP quality distributions (producer→consumer gap closed):
        _env_predictor._history[(skill, op)] → proximity between skills.
        """
        # Collect op-types seen for each skill
        ops_a: dict[str, list[float]] = {}
        ops_b: dict[str, list[float]] = {}
        for (sn, op), window in self._env_predictor._history.items():
            if sn == skill_a:
                ops_a[op] = list(window)
            elif sn == skill_b:
                ops_b[op] = list(window)

        if not ops_a or not ops_b:
            return 0.0

        shared = set(ops_a) & set(ops_b)
        union = set(ops_a) | set(ops_b)
        if not union:
            return 0.0

        jaccard = len(shared) / len(union)
        if not shared:
            return jaccard  # 0.0 when disjoint

        # Weight by quality agreement over shared op types
        quality_agreement = 0.0
        for op in shared:
            mean_a = sum(ops_a[op]) / len(ops_a[op])
            mean_b = sum(ops_b[op]) / len(ops_b[op])
            quality_agreement += 1.0 - abs(mean_a - mean_b) / 2.0
        quality_agreement /= len(shared)

        return jaccard * quality_agreement

    def refine(
        self,
        skill_name: str,
        operation_type: str,
        execution_result: dict[str, Any],
        patterns_extracted: list[str] | None = None,
        failure_signatures: list[Any] | None = None,
        failure_attribution: Any | None = None,
    ) -> str | None:
        """Learn from execution result and refine PRIME skill.

        Analyzes execution metrics and appends learned refinements
        to the PRIME skill definition file.

        Args:
            skill_name: Name of the skill that was executed
            operation_type: Type of operation (generate, analyze, search, etc.)
            execution_result: ExecutionResult dict with metrics and outputs
            patterns_extracted: List of vault pattern paths from execution
            failure_attribution: Optional FailureAttribution from FailureAttributor.
                When provided for a failed execution:
                  - L1 (format/reasoning): emits a failure-derived PRIME refinement
                  - L2/L3 (retrieval/cascading): writes a proof_obligation to SurrealDB

        Returns:
            Path to refined skill file if successful, None otherwise
        """
        try:
            # Extract metrics
            metrics = self._extract_metrics(execution_result)

            # FAPO: handle failure attribution before the success gate
            if not metrics.success and failure_attribution is not None:
                return self._handle_failure_attribution(
                    skill_name, operation_type, failure_attribution, execution_result
                )

            # Only refine on success (original gate — preserved)
            if not metrics.success:
                logger.debug("Skipping refinement for failed execution")
                return None

            # Generate learning signal
            signal = self._generate_learning_signal(skill_name, operation_type, metrics)

            if not signal:
                logger.debug("No significant learning signal generated")
                return None

            # Find and refine PRIME file
            prime_file = self._find_prime_file(skill_name)
            if not prime_file:
                logger.debug(f"No PRIME file found for skill: {skill_name}")
                return None

            # Golden-fixture gate (V-model verification — fail-open)
            from cohezion.compound.prompt_version_registry import PromptVersionRegistry

            if not PromptVersionRegistry().check_drift(skill_name, signal.key_insight):
                logger.info("Skill refinement blocked by golden-fixture gate: %s", skill_name)
                return None

            # FAPO R3: behavioral regression gate — run the CANDIDATE skill against golden fixtures
            # and block promotion if a critical case regresses (defends the self-improvement loop
            # from QUIET prompt regression — check_drift only inspects edit-text embeddings, not
            # behavior). Fail-open when no run_fn is configured.
            if self._regression_run_fn is not None:
                candidate = prime_file.read_text() + f"\n\n{signal.key_insight}"
                if not PromptVersionRegistry().regression_check(
                    skill_name, candidate, self._regression_run_fn
                ):
                    logger.info("Skill refinement blocked by behavioral regression gate: %s", skill_name)
                    return None

            # Append refinement
            refined_path = self._append_refinement(prime_file, signal)

            if refined_path:
                logger.info(f"Refined skill {skill_name}: {signal.key_insight}")

                # Persist refinement to vault + SurrealDB (non-blocking)
                self._persist_refinement_to_vault(skill_name, operation_type, signal, metrics)

                return str(refined_path)

            return None

        except Exception as e:
            # Non-blocking: log and continue
            logger.debug(f"Skill refinement failed (non-blocking): {e}")
            return None

    def _persist_refinement_to_vault(
        self,
        skill_name: str,
        operation_type: str,
        signal: Any,
        metrics: Any,
    ) -> None:
        """Persist skill refinement to vault + SurrealDB via knowledge_bridge."""
        try:
            import time

            from cohezion.governance.knowledge_bridge import Learning, persist_learning

            content = (
                f"Skill '{skill_name}' refined after {operation_type} execution. "
                f"Insight: {signal.key_insight}. "
                f"Coherence: {getattr(metrics, 'coherence', 'N/A')}, "
                f"Quality: {getattr(metrics, 'quality_score', 'N/A')}."
            )

            learning = Learning(
                number=0,
                title=f"Skill refinement: {skill_name}",
                content=content,
                date=time.strftime("%Y-%m-%d"),
                tags=["skill-refinement", skill_name, operation_type],
                propagate_to=f"PRIME skill: {skill_name}",
                context_tier="gold",
            )

            persist_learning(learning)
            logger.info("Knowledge bridge: persisted skill refinement for %s", skill_name)

        except Exception:
            logger.debug("Skill refinement vault persistence failed (non-blocking)", exc_info=True)

    # ── FAPO failure-attribution helpers ─────────────────────────────────────

    def _handle_failure_attribution(
        self,
        skill_name: str,
        operation_type: str,
        failure_attribution: Any,
        execution_result: dict[str, Any],
    ) -> str | None:
        """Route failure attribution to L1 refinement or L2/L3 proof obligation."""
        level = getattr(failure_attribution, "escalation_level", None)
        category = getattr(failure_attribution, "category", "unknown")
        evidence = getattr(failure_attribution, "evidence", "")

        if level == "L1":
            # Act: emit failure-derived prompt refinement to PRIME skill
            return self._apply_l1_failure_refinement(skill_name, operation_type, category, evidence)
        elif level in ("L2", "L3"):
            # Record: write proof_obligation to SurrealDB; no auto-edit
            self._write_proof_obligation(skill_name, category, level, evidence)
            logger.info(
                "FAPO %s (%s) obligation recorded for skill %s — no auto-edit",
                level,
                category,
                skill_name,
            )
            return None
        return None

    def _apply_l1_failure_refinement(
        self,
        skill_name: str,
        operation_type: str,
        category: str,
        evidence: str,
    ) -> str | None:
        """Append an L1 failure-derived note to the PRIME skill file."""
        prime_file = self._find_prime_file(skill_name)
        if not prime_file:
            logger.debug("No PRIME file for L1 failure refinement: %s", skill_name)
            return None

        signal = self._generate_failure_signal(skill_name, operation_type, category, evidence)
        refined_path = self._append_refinement(prime_file, signal)
        if refined_path:
            logger.info("FAPO L1: refined PRIME skill %s for %s failure", skill_name, category)
        return str(refined_path) if refined_path else None

    def _generate_failure_signal(
        self,
        skill_name: str,
        operation_type: str,
        category: str,
        evidence: str,
    ) -> LearningSignal:
        """Create a LearningSignal that encodes a FAPO failure insight."""
        recommendation_map = {
            "format": (
                f"Add structured-output format examples to {skill_name} PRIME skill guidance"
            ),
            "reasoning": (f"Add step-by-step reasoning scaffolding to {skill_name} PRIME skill"),
        }
        return LearningSignal(
            skill_name=skill_name,
            operation_type=operation_type,
            key_insight=f"FAILURE ({category}): {evidence[:200]}",
            metric_change=f"failure_category={category}; escalation=L1",
            recommendation=recommendation_map.get(
                category,
                f"Review {category} failure in {skill_name} PRIME skill",
            ),
            confidence=0.6,
        )

    def _write_proof_obligation(
        self,
        skill_name: str,
        category: str,
        level: str,
        evidence: str,
    ) -> None:
        """Write an unsatisfied FAPO proof_obligation to SurrealDB (non-blocking)."""
        try:
            import json as _json
            import urllib.request
            from base64 import b64encode

            obligation_text = f"FAPO {level} ({category}) failure obligation: {evidence[:300]}"
            surql = (
                f"CREATE proof_obligation SET "
                f"skill_name = {_json.dumps(skill_name)}, "
                f"obligation = {_json.dumps(obligation_text)}, "
                f"satisfied_by = 'pending', "
                f"verified = false;"
            )
            req = urllib.request.Request(
                "http://localhost:8001/sql",
                data=surql.encode(),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": "cohezion",
                    "surreal-db": "cohezion",
                    "Content-Type": "text/plain",
                    "Authorization": "Basic " + b64encode(b"root:root").decode(),
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
            logger.debug("FAPO proof_obligation written for skill=%s level=%s", skill_name, level)
        except Exception:
            logger.debug("proof_obligation write failed (non-blocking)", exc_info=False)

    # ── Original helpers ──────────────────────────────────────────────────────

    def _extract_metrics(self, execution_result: dict[str, Any]) -> ExecutionMetrics:
        """Extract metrics from execution result.

        Args:
            execution_result: ExecutionResult dict

        Returns:
            ExecutionMetrics dataclass
        """
        metrics_dict = execution_result.get("metrics", {})
        token_metrics = execution_result.get("token_metrics", {})

        success = execution_result.get("success", False)
        duration = execution_result.get("duration_seconds", 0.0)
        tokens_used = token_metrics.get("tokens_used", 0)
        anomaly_score = metrics_dict.get("anomaly_score", 0.5)
        cached_hits = token_metrics.get("cache_hits", 0)

        # CB16 ext (TOKEN_BLOAT): per-task token total for rolling-window bloat detection.
        execution_trace = execution_result.get("execution_trace", {})
        tokens_per_task = (
            tokens_used
            or token_metrics.get("total_tokens")
            or token_metrics.get("token_count")
            or execution_trace.get("tokens_used")
            or execution_trace.get("total_tokens")
            or execution_trace.get("token_count")
            or 0
        )

        # Calculate quality score (lower is better quality)
        quality_score = 1.0 - anomaly_score

        # Calculate token efficiency (tokens per second)
        token_efficiency = tokens_used / duration if duration > 0 else 0.0

        return ExecutionMetrics(
            success=success,
            duration_seconds=duration,
            tokens_used=tokens_used,
            token_efficiency=token_efficiency,
            quality_score=quality_score,
            anomaly_score=anomaly_score,
            cached_hits=cached_hits,
            tokens_per_task=tokens_per_task,
        )

    def _generate_learning_signal(
        self,
        skill_name: str,
        operation_type: str,
        metrics: ExecutionMetrics,
    ) -> LearningSignal | None:
        """Generate learning signal from metrics.

        Args:
            skill_name: Name of skill
            operation_type: Type of operation
            metrics: ExecutionMetrics

        Returns:
            LearningSignal if significant learning found, None otherwise
        """
        insights = []

        # #117/#118: EnvironmentResponsePredictor + RL process reward wiring.
        # Compute prediction error BEFORE recording so predict() sees prior history.
        pred_err = self._env_predictor.prediction_error(
            skill_name, operation_type, metrics.quality_score
        )
        self._env_predictor.record(skill_name, operation_type, metrics.quality_score)
        # Store back into metrics (closes producer→consumer gap on the field).
        metrics.prediction_error = pred_err
        # Accumulate into per-skill RL process reward window.
        self._accumulate_process_reward(skill_name, pred_err)
        # #93: feed tier_used + escalation_count into predictive estimator
        self._difficulty_estimator.record(
            skill_name,
            operation_type,
            metrics.tier_used,
            metrics.escalation_count,
            metrics.quality_score,
        )

        # CB16 ext: TOKEN_BLOAT detection over a rolling window of per-task token
        # totals. Emits an insight when the current task exceeds 3x the rolling
        # median (Raschka benchmark: 578k tokens/task vs 50k baseline = 11x gap).
        if not hasattr(self, "_token_window"):
            self._token_window = deque(maxlen=10)

        current = metrics.tokens_per_task
        if current > 0:
            self._token_window.append(current)

        if len(self._token_window) >= 3 and current > 0:
            sorted_vals = sorted(self._token_window)
            median = sorted_vals[len(sorted_vals) // 2]
            if current > 3 * median:
                insights.append(
                    f"TOKEN_BLOAT: {current} tokens vs median {median} (>3x threshold). "
                    "Consider task decomposition or prompt compression."
                )

        # #117: ENVIRONMENT_SURPRISE — quality deviated from rolling-mean prediction
        if pred_err is not None and abs(pred_err) > self._env_predictor._surprise_threshold:
            direction = "above" if pred_err > 0 else "below"
            insights.append(
                f"ENVIRONMENT_SURPRISE: quality {metrics.quality_score:.2f} is "
                f"{abs(pred_err):.2f} {direction} rolling prediction. "
                "Environment response has shifted — review recent context changes."
            )

        # Check quality score
        if metrics.quality_score > 0.8:
            insights.append("high quality execution (low anomaly score)")

        # Check cache efficiency
        if metrics.cached_hits > 0:
            insights.append(f"cache hits improved throughput ({metrics.cached_hits})")

        # Check token efficiency
        if metrics.token_efficiency < 500:  # tokens/sec threshold
            insights.append("efficient token usage")

        if not insights:
            return None

        # Combine insights
        key_insight = "; ".join(insights)
        metric_change = (
            f"Quality: {metrics.quality_score:.2%}, "
            f"Tokens: {metrics.tokens_used}, "
            f"Duration: {metrics.duration_seconds:.2f}s"
        )
        # CB14: citation gate — block signals whose metric_change text doesn't cite
        # real observed values (guards against LM hallucination in the metric summary).
        if not self._lm_signal_cites_metrics(metric_change, metrics):
            logger.debug("CB14: metric_change cites no real metric values — signal blocked")
            return None
        recommendation = self._generate_recommendation(metrics, operation_type, skill_name)
        # #118: RL process reward modulates confidence.
        # Positive mean reward (skill outperforms its own prediction) → boost.
        # Negative mean reward (skill underperforms) → dampen.
        # Scale 0.2 keeps the adjustment bounded within ±0.19 given rewards ∈ [-1, 1].
        base_confidence = min(0.95, metrics.quality_score)
        reward_mean = self.process_reward_mean(skill_name)
        confidence = (
            max(0.1, min(0.95, base_confidence + 0.2 * reward_mean))
            if reward_mean is not None
            else base_confidence
        )

        return LearningSignal(
            skill_name=skill_name,
            operation_type=operation_type,
            key_insight=key_insight,
            metric_change=metric_change,
            recommendation=recommendation,
            confidence=confidence,
        )

    # #122: Autodata multi-perspective candidate pool (arXiv:2606.25996).
    # Each entry: (perspective_name, insight_template, condition_fn).
    # _autodata_recommendation generates all applicable candidates and selects
    # the one with the highest saliency score (most deviation from baseline).
    _AUTODATA_PERSPECTIVES: list[tuple[str, str, Any]] = [
        (
            "quality",
            "Optimize PRIME skill guidance for output quality in {op} operations (quality={q:.0%}).",
            lambda m: m.quality_score > 0.8,
        ),
        (
            "efficiency",
            "Add token-efficient patterns to PRIME skill for {op} (efficiency={eff:.0f} tok/s).",
            lambda m: m.token_efficiency < 500,
        ),
        (
            "caching",
            "Emphasize cache-friendly interaction patterns in PRIME skill for {op} ({hits} hits).",
            lambda m: m.cached_hits > 0,
        ),
        (
            "tier",
            "Specify tier preference in PRIME skill to reduce escalations for {op} "
            "(tier={tier}, escalations={esc}).",
            lambda m: m.escalation_count > 0 or m.tier_used not in ("unknown", ""),
        ),
        (
            "fallback",
            "Acceptable performance for {op} operations — maintain current PRIME guidance.",
            lambda m: True,
        ),
    ]

    def _autodata_candidates(self, metrics: ExecutionMetrics, operation_type: str) -> list[str]:
        """#122: Generate diverse candidate update recommendations (Autodata pattern).

        Produces one candidate per applicable perspective, substituting live
        metric values.  This replaces single-hypothesis greedy selection with
        multi-perspective candidate exploration.
        """
        candidates: list[str] = []
        fmt = {
            "op": operation_type,
            "q": metrics.quality_score,
            "eff": metrics.token_efficiency,
            "hits": metrics.cached_hits,
            "tier": metrics.tier_used,
            "esc": metrics.escalation_count,
        }
        for _name, template, condition in self._AUTODATA_PERSPECTIVES:
            if condition(metrics):
                candidates.append(template.format(**fmt))
        return candidates

    def _autodata_select(self, candidates: list[str], metrics: ExecutionMetrics) -> str:
        """#122: Self-consistency selection — pick the candidate with highest saliency.

        Saliency = word-overlap with ALL other candidates (most-consistent wins).
        Tie-break: quality > efficiency > caching > tier > fallback (order in pool).
        Falls back to candidates[0] (quality perspective) when only one candidate.
        """
        if not candidates:
            return ""
        if len(candidates) == 1:
            return candidates[0]

        def _keywords(s: str) -> set[str]:
            return {w.lower() for w in s.split() if len(w) > 3}

        scores = []
        for i, cand in enumerate(candidates):
            kw = _keywords(cand)
            overlap = sum(
                len(kw & _keywords(other)) for j, other in enumerate(candidates) if j != i
            )
            scores.append(
                (overlap, -i, cand)
            )  # secondary sort by position (earlier = higher priority)
        return max(scores)[2]

    def _lm_signal_cites_metrics(self, text: str, metrics: ExecutionMetrics) -> bool:
        """CB14: Fabrication probe — True iff text cites ≥1 actual metric value within ±50%.

        Checks numeric values extracted from ``text`` against the four primary
        ExecutionMetrics fields that any credible signal should reference.
        Fail-open: empty text or the NOMINAL sentinel returns True so the heuristic
        path runs without restriction when no LM signal is present.

        Source: NatureBench validity auditing + arXiv 2606.27226 BINEVAL probe design.
        """
        if not text or text.strip() == "NOMINAL":
            return True  # fail-open: no LM text → heuristic path unblocked
        numbers = [float(m) for m in re.findall(r"\b\d+(?:\.\d+)?\b", text)]
        if not numbers:
            return False  # text has no numbers → cannot cite any metric
        actuals = [
            float(metrics.tokens_used),
            metrics.quality_score,
            metrics.duration_seconds,
            float(metrics.cached_hits),
        ]
        for actual in actuals:
            if actual <= 0:
                continue
            lo, hi = actual * 0.5, actual * 1.5
            if any(lo <= n <= hi for n in numbers):
                return True
        return False

    def _generate_recommendation(
        self, metrics: ExecutionMetrics, operation_type: str, skill_name: str = ""
    ) -> str:
        """Generate recommendation via Autodata multi-perspective self-consistency (#122).

        Generates diverse candidate recommendations from metric perspectives
        and selects the most self-consistent one (highest word-overlap with peers).

        #136 goal injection: when a session goal is active, a goal-aligned candidate
        is prepended.  Self-consistency selection still governs, but the goal candidate
        has structural advantage because it shares vocabulary with multiple metric
        perspectives that orbit the same target_metric.

        W5: when ``skill_name`` is given and another known skill is close
        (``skill_proximity`` > 0.5), append a cross-skill transfer hint so the loop reuses a
        neighbor's learnings.
        """
        rec = ""
        # #136: goal-aligned recommendation when a session goal is active (GIC Goal dimension);
        # self-consistency selection only governs the undirected case.
        if self._session_goal is not None:
            target = self._session_goal.get("target_metric", "")
            if target == "quality_score":
                rec = (
                    f"Optimize PRIME skill guidance for output quality in {operation_type} "
                    f"operations (goal: improve quality_score, "
                    f"current={metrics.quality_score:.0%})."
                )
            elif target == "escalation_count":
                tier = getattr(metrics, "tier_used", "unknown")
                rec = (
                    f"Specify tier preference in PRIME skill to reduce escalations for "
                    f"{operation_type} (goal: reduce tier escalation, tier={tier})."
                )
        if not rec:
            candidates = self._autodata_candidates(metrics, operation_type)
            rec = self._autodata_select(candidates, metrics)
        # W5: cross-skill transfer hint from the nearest known skill (proximity > 0.5).
        if skill_name:
            best_other, best_score = "", 0.0
            predictor = getattr(self, "_env_predictor", None)
            known = set()
            if predictor is not None and hasattr(predictor, "_history"):
                for k in predictor._history:  # keys are (skill, op) tuples or "skill::op" strings
                    known.add(k[0] if isinstance(k, tuple) else str(k).split("::")[0])
            for other in known:
                if other == skill_name:
                    continue
                score = self.skill_proximity(skill_name, other)
                if score > best_score:
                    best_other, best_score = other, score
            if best_score > 0.5:
                rec = f"{rec} (transfer from '{best_other}', proximity={best_score:.2f})"
        return rec

    def _find_prime_file(self, skill_name: str) -> Path | None:
        """Find PRIME skill file for given skill name.

        Args:
            skill_name: Name of skill (e.g., 'SYSTEM_GUARDRAILS')

        Returns:
            Path to PRIME file or None if not found
        """
        # Try exact match
        prime_name = f"{skill_name.upper()}_PRIME.md"
        prime_path = self.SKILLS_DIR / prime_name

        if prime_path.exists():
            return prime_path

        # Try fuzzy match
        for file in self.SKILLS_DIR.glob("*_PRIME.md"):
            if skill_name.lower() in file.stem.lower():
                return file

        return None

    def _append_refinement(self, prime_file: Path, signal: LearningSignal) -> Path | None:
        """Append learned refinement to PRIME file.

        Args:
            prime_file: Path to PRIME .md file
            signal: LearningSignal to append

        Returns:
            Path to refined file if successful, None otherwise
        """
        try:
            # Read current file
            content = prime_file.read_text(encoding="utf-8")

            # Extract current version
            version_match = re.search(r"## Version: (\d+\.\d+\.\d+)", content)
            current_version = version_match.group(1) if version_match else "1.0.0"

            # Bump patch version
            new_version = self._bump_version(current_version)

            # Create refinement section
            refinement = self._create_refinement_section(signal)

            # Find insertion point (before Version line)
            version_line = f"## Version: {current_version}"
            if version_line not in content:
                # Fallback: append before Keywords
                insertion_point = content.rfind("## Keywords:")
            else:
                insertion_point = content.find(version_line)

            if insertion_point == -1:
                logger.debug("Could not find insertion point in PRIME file")
                return None

            # Insert refinement and update version
            new_content = (
                content[:insertion_point]
                + refinement
                + "\n"
                + f"## Version: {new_version}\n"
                + content[insertion_point + len(version_line) + 1 :]
            )

            # Write back
            prime_file.write_text(new_content, encoding="utf-8")
            logger.info(f"Refined PRIME file: {prime_file.name} → v{new_version}")

            return prime_file

        except Exception as e:
            logger.debug(f"Failed to append refinement: {e}")
            return None

    def _create_refinement_section(self, signal: LearningSignal) -> str:
        """Create refinement section to append to PRIME file.

        Args:
            signal: LearningSignal

        Returns:
            Markdown section string
        """
        timestamp = datetime.now().isoformat()

        section = f"""
## Learned Refinement ({timestamp})

**From**: {signal.operation_type.capitalize()} operation

**Insight**: {signal.key_insight}

**Metrics**: {signal.metric_change}

**Confidence**: {signal.confidence:.1%}

**Recommendation**: {signal.recommendation}

"""
        return section

    def _bump_version(self, version: str) -> str:
        """Bump patch version.

        Args:
            version: Current version string (e.g., "1.0.0")

        Returns:
            Bumped version string
        """
        try:
            parts = version.split(".")
            patch = int(parts[2]) if len(parts) > 2 else 0
            parts[2] = str(patch + 1)
            return ".".join(parts[:3])
        except (ValueError, IndexError):
            return version

    def refine_from_training_runs(self) -> str | None:
        """Query SurrealDB for training runs and refine RL skills based on results.

        Compares the best training run against the RL_ENVIRONMENT_DESIGN_PRIME
        skill's documented expectations. If the best run uses a config not yet
        documented in the skill, appends a refinement note.

        Returns:
            Path to refined skill file, or None if no refinement needed.
        """
        try:
            import json
            import urllib.request
            from base64 import b64encode

            req = urllib.request.Request(
                "http://localhost:8001/sql",
                data=b"SELECT algorithm, reward_mode, reward, convergence_rate, diagnostic FROM training_run ORDER BY reward DESC LIMIT 1;",
                headers={
                    "Accept": "application/json",
                    "surreal-ns": "cohezion",
                    "surreal-db": "cohezion",
                    "Authorization": "Basic " + b64encode(b"root:root").decode(),
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())

            if not data or data[0].get("status") != "OK" or not data[0]["result"]:
                logger.debug("No training runs in SurrealDB")
                return None

            best = data[0]["result"][0]
            algo = best.get("algorithm", "?")
            mode = best.get("reward_mode", "?")
            reward = best.get("reward", 0)

            # Check if RL skill already documents this config
            rl_skill = self.SKILLS_DIR / "RL_ENVIRONMENT_DESIGN_PRIME.md"
            if not rl_skill.exists():
                return None

            content = rl_skill.read_text()
            config_key = f"{algo}+{mode}"

            if config_key.lower() in content.lower():
                logger.debug("RL skill already documents %s (reward=%.2f)", config_key, reward)
                return None

            # Append refinement
            import time

            refinement = (
                f"\n- v{time.strftime('%Y%m%d')}: Training data shows {algo}+{mode} "
                f"achieves reward={reward:.2f}. {best.get('diagnostic', '')[:100]}\n"
            )

            with open(rl_skill, "a") as f:
                f.write(refinement)

            logger.info("Refined RL skill from training data: %s reward=%.2f", config_key, reward)
            return str(rl_skill)

        except Exception as e:
            logger.debug("Training run refinement failed (non-blocking): %s", e)
            return None


class SkillRefinerFactory:
    """Factory for creating skill refiner instances."""

    _instance: SkillRefiner | None = None

    @staticmethod
    def create(mcp_client: Any = None) -> SkillRefiner:
        """Create a new SkillRefiner.

        Args:
            mcp_client: Optional MCPClient for vault operations

        Returns:
            SkillRefiner instance
        """
        return SkillRefiner(mcp_client)

    @staticmethod
    def get_singleton(mcp_client: Any = None) -> SkillRefiner:
        """Get or create singleton SkillRefiner.

        Args:
            mcp_client: Optional MCPClient for vault operations

        Returns:
            Singleton SkillRefiner instance
        """
        if SkillRefinerFactory._instance is None:
            SkillRefinerFactory._instance = SkillRefiner(mcp_client)
        return SkillRefinerFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        SkillRefinerFactory._instance = None
