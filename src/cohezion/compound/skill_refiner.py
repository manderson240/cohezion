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
from datetime import UTC, datetime
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
    authority_tag: str = "system"


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


class ShadowCanaryValidator:
    """Rolling-window baseline gate — blocks PRIME promotion on quality regression.

    Before SkillRefiner writes a candidate learning signal to a PRIME skill file,
    validate() checks whether the triggering execution's quality score falls more than
    ``regression_threshold`` below the per-skill rolling median baseline. Fail-open
    when the baseline window is empty (first N executions always pass).

    Interface (confirmed by Bonsai-8B design review 2026-06-30):
        record(skill_name, quality_score)       — called every successful execution
        validate(skill_name, candidate_scores)  — called before each PRIME write
    """

    # RC1: regime-conditioned threshold multipliers.
    # STUCK (FD<1.3): loosen gate to allow experimental updates that break the exploitation rut.
    # CHAOTIC (FD>1.7): tighten gate; quality is oscillating so block speculative promotions.
    _REGIME_THRESHOLD_MULTIPLIERS: dict[str, float] = {
        "stuck": 1.5,
        "chaotic": 0.5,
    }

    def __init__(self, window_size: int = 20, regression_threshold: float = 0.05) -> None:
        self._history: dict[str, deque[float]] = {}
        self._window_size = window_size
        self._regression_threshold = regression_threshold

    def record(self, skill_name: str, quality_score: float) -> None:
        """Append quality_score to the per-skill rolling baseline window."""
        if skill_name not in self._history:
            self._history[skill_name] = deque(maxlen=self._window_size)
        self._history[skill_name].append(quality_score)

    def validate(
        self,
        skill_name: str,
        candidate_scores: list[float],
        regime: str | None = None,
    ) -> tuple[bool, str]:
        """Return (ok, reason).

        Fail-open when there is no baseline history or no candidate scores.
        Blocks when median(candidate) < median(baseline) - effective_threshold.

        The effective threshold is the base regression_threshold modulated by the
        current FD regime (RC1): STUCK loosens it (×1.5), CHAOTIC tightens it (×0.5).
        """
        window = self._history.get(skill_name)
        if not window or not candidate_scores:
            return True, "no_baseline"

        multiplier = self._REGIME_THRESHOLD_MULTIPLIERS.get(regime or "", 1.0)
        effective_threshold = self._regression_threshold * multiplier

        sorted_baseline = sorted(window)
        baseline_median = sorted_baseline[len(sorted_baseline) // 2]

        sorted_candidate = sorted(candidate_scores)
        candidate_median = sorted_candidate[len(sorted_candidate) // 2]

        regression = baseline_median - candidate_median
        if regression > effective_threshold:
            return False, (
                f"quality regression {candidate_median:.2f} vs baseline {baseline_median:.2f} "
                f"(delta {regression:.3f} > threshold {effective_threshold:.3f}"
                + (f", regime={regime}" if regime else "")
                + ")"
            )
        return True, (
            f"ok (candidate {candidate_median:.2f} >= "
            f"baseline {baseline_median:.2f} - {effective_threshold:.3f}"
            + (f", regime={regime}" if regime else "")
            + ")"
        )


class SkillRefiner:
    """Refines PRIME skill definitions based on execution results."""

    SKILLS_DIR = Path(__file__).parent.parent / "skills"

    # RQGM2: rotating goal targets — cycles quality_score → escalation_count → token_efficiency
    # so the SkillRefiner never stagnates at a single-metric local optimum (Red Queen principle).
    _RQGM_GOAL_ROTATION: list[str] = ["quality_score", "escalation_count", "token_efficiency"]

    # CB15: words excluded from PRIME invariant keyword extraction (anchor words + stop words).
    # Shared-root comparison requires min 4 chars, so short words filtered out by length already.
    _SEESAW_STOP: frozenset[str] = frozenset(
        {
            "must",
            "never",
            "always",
            "required",
            "mandatory",  # anchor words themselves
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "have",
            "when",
            "will",
            "not",
            "are",
            "was",
            "been",
            "they",
            "their",
            "which",
            "should",
            "would",
            "could",
            "does",
            "into",
            "each",
            "only",
        }
    )

    def __init__(
        self,
        mcp_client: Any = None,
        moe_router: Any = None,
        degradation_detector: Any = None,
        journey_tracker: Any = None,
        health_oracle: Any = None,
        failure_memory: Any = None,
    ):
        """Initialize skill refiner.

        Args:
            mcp_client: Optional MCPClient for vault operations
            moe_router: Optional MoESkillRouter (#83). When wired, biases
                ``_autodata_select`` candidate scoring by learned per-expert weight.
            degradation_detector: Optional DegradationDetector. When wired,
                per-skill quality drift is checked on each learning signal.
            health_oracle: Optional CompoundHealthOracle. When wired, each execution's
                quality score is fed into the streaming HIHO regime tracker so the oracle
                builds up a rolling FD baseline across the session.
            failure_memory: Optional FailureConditionedMemory. Retrieval-augmented
                recommendation over past FAPO L1 failure+fix pairs (defaults to a
                fresh in-process instance — never None, so retrieval is always
                attempted and fails open to the existing generic template).
        """
        self.mcp_client = mcp_client
        # #83: MoE router over the five Autodata expert heads (None = unbiased selection).
        self._moe_router = moe_router
        # Per-skill drift: calls check_skill_drift() in _generate_learning_signal when wired.
        self._degradation_detector = degradation_detector
        # AReaL2.0: cross-session trajectory history from JourneyTracker — consumed by
        # _autodata_candidates() to generate history-informed perspective candidates.
        self._journey_tracker = journey_tracker
        # CH1-CH5: streaming HIHO regime oracle — assess() is called on each quality score so
        # the oracle accumulates an FD baseline and can answer is_healthy() across the session.
        self._health_oracle = health_oracle
        # #83: maps candidate recommendation text -> originating expert name; populated by
        # _autodata_candidates(), consumed by _autodata_select() for MoE-weighted scoring.
        self._candidate_expert_map: dict[str, str] = {}
        self._env_predictor = EnvironmentResponsePredictor()
        # #118: per-skill rolling window of prediction errors (process rewards)
        self._process_rewards: dict[str, deque[float]] = {}
        # NIG prior: (mu, kappa, alpha, beta) per skill — conjugate for Normal(mu,sigma²).
        # Prior: mu=0.0 (zero mean), kappa=1.0 (one pseudocount), alpha=1.5 (half-observation
        # prior on variance), beta=1.0 (unit prior scale).  Works from n=1 unlike z-score
        # normalization which needs ≥3 samples to stabilize.  (Gelman BDA §2.6)
        self._nig_params: dict[str, tuple[float, float, float, float]] = {}
        # #93: predictive tier estimator (closes tier_used producer→consumer gap)
        from cohezion.compound.difficulty_estimator import DifficultyEstimator

        self._difficulty_estimator = DifficultyEstimator()

        # #136: Self-directed learning goal state (GIC agentive — arXiv 2606.23991).
        # Internally held across the session; updated by set_goal() or _auto_update_goal().
        # Factors into _generate_recommendation(): goal-aligned perspective gets priority.
        self._session_goal: dict | None = None
        self._goal_call_tally: dict[str, int] = {}  # per-skill call counter for auto-update
        self._goal_auto_threshold: int = 5  # auto-update goal every N calls per skill
        # RQGM (Red Queen Gödel Machine — arXiv 2606.26294): co-evolving goal epoch prevents
        # static-evaluator stagnation.  Each time _auto_update_goal fires, the epoch advances
        # and the goal target rotates through _RQGM_GOAL_ROTATION, breaking local optima.
        self._goal_epoch: int = 0
        self._goal_consecutive_hits: int = 0
        # RV2 (RiVER frequency penalty — arXiv:2606.27369): per-candidate win counter for
        # _autodata_select(); dominant candidates are penalised via 1/(1+wins) to prevent
        # perspective lock.
        self._autodata_wins: dict[str, int] = {}
        # FAPO R3 (M1): optional run_fn(candidate_prompt, fixture_input) -> output for the behavioral
        # regression gate in refine(). None = gate fail-open (drift gate still applies). Wired by
        # SkillRefinerFactory.create so the gate is LIVE on the standard path, not dormant.
        self._regression_run_fn = None
        # Shadow canary: rolling quality baseline per skill; blocks PRIME promotion on regression.
        self._shadow_canary = ShadowCanaryValidator()
        # Adversarial review: 3-perspective frontier-first LLM fan-out before PRIME commit.
        # Priority: claude-fable-5 → claude-opus-4-8 → agy → Bonsai-8B-local.
        # None = dormant; gate lazy-builds on first refine() call; fail-open everywhere.
        self._adversarial_chat_fn: Any = None
        # Failure-conditioned retrieval (2607.13104 + MSCE 2607.16617 + self-healing-code):
        # kNN over past FAPO L1 failure+fix pairs, consumed by _generate_failure_signal().
        # Always instantiated (never None) — retrieve() on an empty/unreachable-embed store
        # is itself fail-open (returns []), so this never changes existing behaviour when
        # no analogous failure has been recorded yet.
        if failure_memory is not None:
            self._failure_memory = failure_memory
        else:
            from cohezion.compound.failure_memory import FailureConditionedMemory

            self._failure_memory = FailureConditionedMemory()

    def process_reward_mean(self, skill_name: str) -> float | None:
        """Return mean accumulated RL process reward for a skill, or None if no data.

        Positive mean → skill quality exceeds its own prediction (underestimated).
        Negative mean → skill quality falls short of prediction (overestimated).
        """
        window = self._process_rewards.get(skill_name)
        return float(sum(window) / len(window)) if window else None

    def _accumulate_process_reward(self, skill_name: str, pred_err: float | None) -> None:
        """Normalize pred_err with NIG predictive std and append to the reward window.

        Normal-Inverse-Gamma conjugate update (Gelman BDA §2.6):
          prior  (μ, κ, α, β) → posterior after observing x:
          κ' = κ+1,  μ' = (κμ+x)/κ',  α' = α+0.5,  β' = β + κ(x-μ)²/(2κ')
          predictive std = sqrt(β'(κ'+1)/(α'κ'))

        Works from n=1 without warm-up (unlike z-score which needs ≥3 for a
        stable sample std).  RV1 upgrade per Gelman BDA §3.1 research run.
        """
        if pred_err is None:
            return
        if skill_name not in self._process_rewards:
            self._process_rewards[skill_name] = deque(maxlen=20)
        # NIG sequential update
        mu, kappa, alpha, beta = self._nig_params.get(skill_name, (0.0, 1.0, 1.5, 1.0))
        kappa_new = kappa + 1.0
        mu_new = (kappa * mu + pred_err) / kappa_new
        alpha_new = alpha + 0.5
        beta_new = beta + kappa * (pred_err - mu) ** 2 / (2.0 * kappa_new)
        self._nig_params[skill_name] = (mu_new, kappa_new, alpha_new, beta_new)
        import math

        pred_std = math.sqrt(beta_new * kappa_new / (alpha_new * kappa))
        normalized = (pred_err - mu) / max(pred_std, 1e-8)
        self._process_rewards[skill_name].append(normalized)

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

        Epoch 0: uses the original metrics-driven heuristic (quality < 0.5 first,
        then escalation_count > 0) — existing behaviour is preserved.
        Epoch 1+: rotates through _RQGM_GOAL_ROTATION [quality_score,
        escalation_count, token_efficiency] ignoring current metrics, so the
        SkillRefiner never stagnates at a single-metric local optimum (RQGM2).

        Each firing increments _goal_epoch and resets _goal_consecutive_hits.
        """
        tally = self._goal_call_tally.get(skill_name, 0) + 1
        self._goal_call_tally[skill_name] = tally
        if tally < self._goal_auto_threshold:
            return
        # Reset so it fires again after the next N calls.
        self._goal_call_tally[skill_name] = 0
        # RQGM2: advance epoch counter and reset consecutive-hit tracker.
        self._goal_consecutive_hits = 0
        if self._goal_epoch == 0:
            # Epoch 0: original metrics-driven heuristic — preserve backward compatibility.
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
        else:
            # Epoch 1+: rotate through goal targets regardless of current metrics.
            target = self._RQGM_GOAL_ROTATION[self._goal_epoch % len(self._RQGM_GOAL_ROTATION)]
            self._session_goal = {
                "objective": f"rqgm-epoch-{self._goal_epoch} optimize {target}",
                "target_metric": target,
            }
        self._goal_epoch += 1

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
                self._record_blocked_promotion(skill_name, signal, "drift_gate")
                return None

            # FAPO R3: behavioral regression gate — run the CANDIDATE skill against golden fixtures
            # and block promotion if a critical case regresses (defends the self-improvement loop
            # from QUIET prompt regression — check_drift only inspects edit-text embeddings, not
            # behavior). Fail-open when no run_fn is configured.
            if self._regression_run_fn is not None:
                reg = PromptVersionRegistry()
                # WIRING H1: the gate was DORMANT because nothing ever populated golden_fixture, so
                # regression_check always hit its no-fixtures fail-open path. Lazily bootstrap
                # fixtures from the CURRENT (pre-edit) prime content so the gate has cases to BITE
                # on. Non-circular: fixtures capture the skill's CURRENT correct behavior; the
                # candidate edit is then tested AGAINST them — the skill does NOT author its own
                # pass criteria from the edit it is trying to promote. Fail-safe (no-op on error).
                self._ensure_golden_fixtures(reg, skill_name, prime_file)

                candidate = prime_file.read_text() + f"\n\n{signal.key_insight}"

                # BMAD qa_gate P0 (ADVISORY): risk-weighted 4-state verdict WRAPPING the binary
                # regression gate below. Logs a qa_gate row; the BINARY gate still OWNS the actual
                # block (additive — never alters this decision). Belt-and-suspenders try (evaluate
                # is itself fail-open) so an advisory failure can never break refine().
                from cohezion.compound import qa_gate as _qa_gate

                try:
                    _qa_gate.evaluate(skill_name, candidate, self._regression_run_fn)
                except Exception as _exc:
                    logger.debug("qa_gate advisory failed (non-blocking): %s", _exc)

                if not reg.regression_check(skill_name, candidate, self._regression_run_fn):
                    logger.info(
                        "Skill refinement blocked by behavioral regression gate: %s", skill_name
                    )
                    self._record_blocked_promotion(skill_name, signal, "regression_gate")
                    return None

            # Shadow canary: block promotion when current quality regresses vs rolling baseline.
            # Fail-open when no history yet or when quality_score is absent (e.g., mocked metrics).
            # RC1: extract FD regime from oracle to modulate the effective threshold.
            _canary_regime: str | None = None
            _canary_oracle = getattr(self, "_health_oracle", None)
            if _canary_oracle is not None:
                _canary_last = getattr(_canary_oracle, "_last_assessment", None)
                if _canary_last is not None:
                    _canary_regime = getattr(_canary_last, "regime", None)
            _candidate_score = getattr(metrics, "quality_score", None)
            if _candidate_score is not None:
                _canary_ok, _canary_reason = self._shadow_canary.validate(
                    skill_name, [_candidate_score], regime=_canary_regime
                )
                if not _canary_ok:
                    logger.info(
                        "Skill refinement blocked by shadow canary: %s — %s",
                        skill_name,
                        _canary_reason,
                    )
                    self._record_blocked_promotion(skill_name, signal, "shadow_canary")
                    return None

            # Adversarial review: 3-perspective local LLM fan-out (fail-open when offline).
            # Inserted after shadow canary so only high-quality signals reach this gate.
            if not self._adversarial_review_gate(signal, skill_name, metrics):
                self._record_blocked_promotion(skill_name, signal, "adversarial_review")
                return None

            # AOEP mutability axis: decay stale pending mutations (TTL contract)
            queue = getattr(self, "mutation_queue", None)
            if queue is not None and hasattr(queue, "expire_stale"):
                queue.expire_stale()

            # CB15: seesaw gate — block any recommendation that negates PRIME invariants
            if not self._seesaw_check(prime_file, signal.recommendation):
                self._record_blocked_promotion(skill_name, signal, "seesaw_check")
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
            # Failure-conditioned retrieval: record this (failure, fix) pair now that the
            # refinement was actually applied, so a future analogous failure (in this or
            # any other skill) can retrieve and cite it instead of the generic template.
            try:
                self._failure_memory.record(
                    failure_text=evidence,
                    fix_text=signal.recommendation,
                    skill_name=skill_name,
                    category=category,
                )
            except Exception:
                logger.debug("failure_memory.record failed (non-blocking)", exc_info=True)
        return str(refined_path) if refined_path else None

    def _generate_failure_signal(
        self,
        skill_name: str,
        operation_type: str,
        category: str,
        evidence: str,
    ) -> LearningSignal:
        """Create a LearningSignal that encodes a FAPO failure insight.

        Failure-conditioned retrieval (2607.13104 self-improving-agent survey +
        MSCE 2607.16617 + GenAI_Agents self_healing_code): before falling back
        to the generic per-category template, retrieve the most semantically
        similar PAST failure+fix from ``self._failure_memory``. When a match
        clears the similarity threshold, its fix text becomes the
        recommendation VERBATIM (not decorated) so that re-recording it after
        this refinement is applied doesn't accumulate citation wrappers across
        repeated retrievals. Provenance instead goes into ``metric_change``.
        Fail-open: an empty/unreachable memory returns [] and behaviour is
        byte-for-byte the pre-existing generic-template path.
        """
        recommendation_map = {
            "format": (
                f"Add structured-output format examples to {skill_name} PRIME skill guidance"
            ),
            "reasoning": (f"Add step-by-step reasoning scaffolding to {skill_name} PRIME skill"),
        }

        retrieved = self._failure_memory.retrieve(evidence, k=1)
        if retrieved:
            past_record, similarity = retrieved[0]
            recommendation = past_record.fix_text
            metric_change = (
                f"failure_category={category}; escalation=L1; "
                f"retrieved_fix_from='{past_record.failure_text[:60]}' "
                f"(similarity={similarity:.2f})"
            )
            confidence = 0.65  # slightly higher: grounded in a demonstrated prior fix
        else:
            recommendation = recommendation_map.get(
                category,
                f"Review {category} failure in {skill_name} PRIME skill",
            )
            metric_change = f"failure_category={category}; escalation=L1"
            confidence = 0.6

        return LearningSignal(
            skill_name=skill_name,
            operation_type=operation_type,
            key_insight=f"FAILURE ({category}): {evidence[:200]}",
            metric_change=metric_change,
            recommendation=recommendation,
            confidence=confidence,
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

        # POLARITY FIX (2026-07-12): anomaly_score is a HEALTH score (high=good) — use directly
        quality_score = anomaly_score

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
        # Shadow canary: feed into per-skill rolling baseline for validate() in refine().
        self._shadow_canary.record(skill_name, metrics.quality_score)
        # Per-skill drift: WARN at 3%, CRITICAL at 5% drop vs rolling mean.
        if self._degradation_detector is not None:
            self._degradation_detector.check_skill_drift(skill_name, metrics.quality_score)
        # CH5: Health oracle — feed quality score into streaming HIHO regime tracker so
        # oracle.is_healthy() reflects actual session quality history, not warming-up state.
        if self._health_oracle is not None:
            try:
                self._health_oracle.assess(metrics.quality_score)
            except Exception:
                pass
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
    # RA1-RA3: regime-aware expert weight multipliers (2026-07-04).
    # Applied in _autodata_select() when a CompoundHealthOracle regime is available.
    # HIHO (1.3≤FD≤1.7): no bias — dict omits HIHO entries, defaults to 1.0 via .get().
    # STUCK (FD<1.3): loop over-exploiting → boost exploration signals (quality/efficiency/trajectory),
    #   suppress operational signals (tier/caching = more of the same pattern).
    # CHAOTIC (FD>1.7): quality oscillating → boost stability signals (tier/caching anchor routing),
    #   suppress exploration signals (quality metrics are unreliable noise in this regime).
    _REGIME_EXPERT_WEIGHT: dict[tuple[str, str], float] = {
        ("stuck", "quality"): 1.6,
        ("stuck", "efficiency"): 1.4,
        ("stuck", "trajectory"): 1.5,
        ("stuck", "tier"): 0.6,
        ("stuck", "caching"): 0.7,
        ("stuck", "fallback"): 0.8,
        ("chaotic", "tier"): 1.8,
        ("chaotic", "caching"): 1.6,
        ("chaotic", "fallback"): 1.4,
        ("chaotic", "quality"): 0.6,
        ("chaotic", "efficiency"): 0.7,
        ("chaotic", "trajectory"): 0.8,
    }

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
        # #83: rebuild candidate->expert map for MoE-weighted selection.
        self._candidate_expert_map = {}
        for _name, template, condition in self._AUTODATA_PERSPECTIVES:
            if condition(metrics):
                candidate = template.format(**fmt)
                candidates.append(candidate)
                self._candidate_expert_map[candidate] = _name

        # AReaL2.0: trajectory-informed perspective — consume cross-session history from
        # JourneyTracker. Generates a history-grounded candidate when recent trajectory
        # data for this operation_type exists (≥3 matching points).
        if self._journey_tracker is not None:
            try:
                recent = [
                    p
                    for p in self._journey_tracker.export_trajectories(last_n=20)
                    if p["operation_type"] == operation_type
                ]
                if len(recent) >= 3:
                    mean_coherence = sum(p["coherence"] for p in recent) / len(recent)
                    n = len(recent)
                    if mean_coherence >= 0.65:
                        candidate = (
                            f"Trajectory shows high coherence ({mean_coherence:.0%}) on "
                            f"{operation_type} over last {n} runs — reinforce current "
                            f"PRIME guidance; this approach is working well."
                        )
                    else:
                        candidate = (
                            f"Trajectory shows degraded coherence ({mean_coherence:.0%}) on "
                            f"{operation_type} over last {n} runs — revise PRIME skill "
                            f"to address recurring quality shortfall."
                        )
                    candidates.append(candidate)
                    self._candidate_expert_map[candidate] = "trajectory"
            except Exception:
                pass  # fail-open: tracker errors never block candidate generation

        return candidates

    def _autodata_select(
        self,
        candidates: list[str],
        metrics: ExecutionMetrics,
        regime: str | None = None,
    ) -> str:
        """#122: Self-consistency selection — pick the candidate with highest saliency.

        Saliency = word-overlap with ALL other candidates (most-consistent wins).
        Tie-break: quality > efficiency > caching > tier > fallback (order in pool).
        Falls back to candidates[0] (quality perspective) when only one candidate.

        RA1-RA3 (2026-07-04): when ``regime`` is "stuck" or "chaotic", applies a
        per-expert multiplier from ``_REGIME_EXPERT_WEIGHT`` AFTER the MoE weight.
        Combined score = overlap × moe_weight × regime_weight.  HIHO or None → 1.0
        for all experts (no bias), preserving the original self-consistency ordering.
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
            expert = self._candidate_expert_map.get(cand, "fallback")
            # #83 (MR4): bias score by the originating expert's learned MoE weight when wired.
            # No router → weight 1.0, preserving the pure self-consistency ordering.
            weight = 1.0
            if self._moe_router is not None:
                weight = self._moe_router.get_weight(expert)
            # RA1-RA3: regime-aware multiplier — STUCK boosts exploration, CHAOTIC boosts stability.
            if regime in ("stuck", "chaotic"):
                weight = weight * self._REGIME_EXPERT_WEIGHT.get((regime, expert), 1.0)
            # RV2 (RiVER arXiv:2606.27369): frequency penalty prevents perspective lock.
            # Candidates that have won many times are discounted via 1/(1+wins) so
            # under-explored perspectives can overtake a habitually dominant winner.
            wins = self._autodata_wins.get(cand, 0)
            freq_penalty = 1.0 / (1.0 + wins)
            scores.append(
                (overlap * weight * freq_penalty, -i, cand)
            )  # secondary sort by position (earlier = higher priority)
        winner = max(scores)[2]
        # Post-selection: increment win counter for the chosen candidate (RV2).
        self._autodata_wins[winner] = self._autodata_wins.get(winner, 0) + 1
        return winner

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
            # RA1-RA3: pass the oracle's current FD regime so selection favors the right experts.
            # Use getattr so stubs that skip __init__ (e.g. W5 tests via __new__) don't crash.
            _regime: str | None = None
            _oracle = getattr(self, "_health_oracle", None)
            if _oracle is not None:
                _last = getattr(_oracle, "_last_assessment", None)
                if _last is not None:
                    _regime = getattr(_last, "regime", None)
            rec = self._autodata_select(candidates, metrics, regime=_regime)
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

    def _ensure_golden_fixtures(self, registry: Any, skill_name: str, prime_file: Path) -> None:
        """WIRING H1: populate golden fixtures so the behavioral regression gate is non-dormant.

        Bootstraps fixtures from the CURRENT (pre-edit) prime content ONLY when the skill has none.
        This is the missing production caller for ``bootstrap_fixtures`` — without it the
        ``golden_fixture`` table stays empty and ``regression_check`` perpetually fail-opens.

        Anti-poisoning (security review FIXTURE-POISONING): fixtures are derived from the skill's
        CURRENT correct behavior, NOT from the candidate edit being promoted — so a skill cannot
        author its own pass criteria from the change it is trying to land (non-circular). We also
        never re-author once fixtures exist (avoids unbounded accumulation / drift of criteria).

        Fail-safe: any error (lemonade down → empty generation; SurrealDB down → load/write error)
        is swallowed, leaving fixtures absent so the gate stays fail-open (no fixtures → skip),
        per the existing regression_check contract. Bootstrap must never break refine().
        """
        try:
            if registry._load_behavioral_fixtures(skill_name):
                return  # already has fixtures — never re-author its own criteria
            current = prime_file.read_text(encoding="utf-8")
            # H1 real fix: GROUND each fixture keyword against the CURRENT skill's actual output (run the
            # pre-edit prime via _regression_run_fn) so a confirmed keyword is VERIFIED behaviour
            # (critical=True → can block a real regression), not an LLM guess. partial(rf, current) binds
            # the candidate arg to the current prime → ground(inp) = rf(current, inp). No run_fn → no
            # grounding → fixtures stay critical=False (observe-only), preserving the prior contract.
            import functools

            ground = (
                functools.partial(self._regression_run_fn, current)
                if self._regression_run_fn
                else None
            )
            registry.bootstrap_fixtures(skill_name, current, ground_fn=ground)
        except Exception as exc:  # fail-safe: gate stays fail-open if population fails
            logger.debug("golden-fixture bootstrap skipped (fail-safe): %s", exc)

    # ------------------------------------------------------------------
    # Adversarial review gate (local inference, 3-perspective fan-out)
    # ------------------------------------------------------------------

    _ADVERSARIAL_PERSONAS: list[tuple[str, str]] = [
        (
            "skeptic",
            (
                "You are an adversarial reviewer. Assume this skill improvement is WRONG.\n"
                "Find a concrete reason to reject it.\n"
                "Reply ONLY: APPROVE or REJECT <reason in ≤15 words>.\n"
            ),
        ),
        (
            "invariant_guardian",
            (
                "You are an invariant guardian. Check if this recommendation negates any "
                "'must', 'never', or 'always' directive in the skill's documented constraints.\n"
                "Reply ONLY: APPROVE (safe) or REJECT <reason in ≤15 words>.\n"
            ),
        ),
        (
            "metric_auditor",
            (
                "You are a metrics auditor. Does this learning signal cite specific measured "
                "values (numbers, percentages, durations) from the actual execution?\n"
                "Reply ONLY: APPROVE (cites real metrics) or REJECT (vague/hallucinated).\n"
            ),
        ),
    ]

    def _adversarial_review_gate(
        self,
        signal: "LearningSignal",
        skill_name: str,
        metrics: "ExecutionMetrics",
    ) -> bool:
        """3-perspective local LLM adversarial fan-out before PRIME commit.

        Three independent local-model calls each take a distinct adversarial lens:
        Skeptic (assume wrong), InvariantGuardian (must/never/always), MetricAuditor
        (are real values cited?).  2/3 APPROVE → proceed; otherwise block.

        Fail-open on any LLM transport failure — a single perspective timeout counts
        as APPROVE so a down endpoint never blocks the self-improvement loop entirely.
        Fail-open when the gate is not yet built (first call lazy-builds the shim).

        Uses Bonsai-8B-gguf via :13305 OmniRouter (iGPU structured-generation tier).
        Quarter-on-a-string: $0 local inference, 48 max-tokens per call, temperature=0.3.
        Bonsai-8B is preferred over deepseek-r1 for short categorical APPROVE/REJECT calls
        (right model for the task — reasoning depth not needed for 48-token outputs).
        """
        chat_fn = self._adversarial_chat_fn
        if chat_fn is None:
            # Build frontier chat function: Fable → Opus → agy → Bonsai-local.
            # Each layer is tried once at build time; the first live path becomes chat_fn.
            _frontier_fn = None
            try:
                from cohezion.inference.frontier_oracle import frontier_complete_sync as _fcs

                def _frontier_wrapper(p: str) -> str:
                    return _fcs(p, timeout=90.0)

                _frontier_fn = _frontier_wrapper
            except Exception as _fe:
                logger.debug("Frontier oracle unavailable, falling back to local: %s", _fe)

            if _frontier_fn is not None:
                chat_fn = _frontier_fn
                self._adversarial_chat_fn = chat_fn
            else:
                # Fall through to local Bonsai-8B-gguf on Lemonade (iGPU, fast structured gen).
                try:
                    from gaia.llm.lemonade_client import (
                        LemonadeClient,  # type: ignore[import-not-found]
                    )

                    from cohezion.inference.gaia_adapter import _GaiaLLMClientShim

                    _model = "Bonsai-8B-gguf"
                    _client = LemonadeClient(
                        base_url="http://localhost:13305/api/v1",
                        model=_model,
                        verbose=False,
                    )
                    chat_fn = _GaiaLLMClientShim(
                        _client, _model, max_tokens=48, temperature=0.3
                    ).prompt
                    self._adversarial_chat_fn = chat_fn
                except Exception as exc:
                    logger.debug("Adversarial reviewer unavailable (fail-open): %s", exc)
                    return True  # all paths down → always proceed

        rec = signal.recommendation
        insight = signal.key_insight
        metric_change = signal.metric_change
        context = (
            f"Skill: {skill_name}\n"
            f"Insight: {insight}\n"
            f"Metric change: {metric_change}\n"
            f"Recommendation: {rec}\n\n"
        )

        approvals = 0
        rejections: list[str] = []
        for name, system_lens in self._ADVERSARIAL_PERSONAS:
            prompt = system_lens + context
            try:
                reply = (chat_fn(prompt) or "").strip().upper()
                if reply.startswith("APPROVE"):
                    approvals += 1
                elif (
                    not reply
                    or "AUTHENTICATION REQUIRED" in reply
                    or "PLEASE LOG IN" in reply
                    or "ACCOUNTS.GOOG" in reply
                ):
                    # Auth redirect or empty reply — reviewer unavailable, fail-open.
                    logger.debug("Adversarial perspective %s auth-error (fail-open)", name)
                    approvals += 1
                else:
                    rejections.append(f"{name}: {reply[:80]}")
            except Exception as exc:
                # Per-perspective failure: fail-open (counts as APPROVE).
                logger.debug("Adversarial perspective %s failed (fail-open): %s", name, exc)
                approvals += 1

        approved = approvals >= 2
        if approved:
            logger.debug("Adversarial review PASSED for %s (%d/3 approve)", skill_name, approvals)
        else:
            logger.info(
                "Adversarial review BLOCKED PRIME promotion for %s: %s",
                skill_name,
                " | ".join(rejections) or "no rejections recorded",
            )
        return approved

    # HITL + observability surface for blocked self-mutations (2026 Agent Confidence Index: human-in-
    # the-loop is the #1 production-confidence lever at 59%, observability #2 at 53%). When the loop
    # autonomously BLOCKS a skill mutation, it must not vanish silently — record it with a legible
    # "why" so an operator can review it. Stdlib only; append-only JSONL the operator can tail.
    _APPROVALS_PATH = Path.home() / ".cohezion" / "pending_skill_approvals.jsonl"

    def _seesaw_check(self, prime_file: "Path", proposed_recommendation: str) -> bool:
        """CB15: block any recommendation that negates an invariant in the PRIME file.

        Scans lines containing anchor words (must/never/always/required/mandatory), extracts
        significant keywords, then rejects when a negation word in the recommendation appears
        within 40 chars of an invariant keyword (shared-root comparison for morphological
        variants).  Fail-open on any read/parse error — never blocks on uncertainty.
        """
        _ANCHORS = frozenset({"must", "never", "always", "required", "mandatory"})
        _NEGATIONS = frozenset(
            {
                "skip",
                "avoid",
                "disable",
                "remove",
                "never",
                "don't",
                "do not",
            }
        )
        try:
            text = prime_file.read_text()
        except Exception:
            return True  # fail-open

        # Collect significant keywords from invariant-anchor lines
        invariant_kws: list[str] = []
        for line in text.splitlines():
            line_lower = line.lower()
            if not any(anc in line_lower for anc in _ANCHORS):
                continue
            for word in line_lower.split():
                word = word.strip(".,;:()[]\"'")
                if len(word) >= 4 and word not in self._SEESAW_STOP and word not in _ANCHORS:
                    invariant_kws.append(word)

        if not invariant_kws:
            return True  # no invariants to protect

        rec_lower = proposed_recommendation.lower()

        for kw in invariant_kws:
            root = kw[: max(4, len(kw) - 1)]
            # Find every occurrence of the root in the recommendation
            start = 0
            while True:
                idx = rec_lower.find(root, start)
                if idx == -1:
                    break
                # Check if a negation word appears within 40 chars of this keyword occurrence
                window_start = max(0, idx - 40)
                window_end = min(len(rec_lower), idx + len(kw) + 40)
                window = rec_lower[window_start:window_end]
                for neg in _NEGATIONS:
                    if neg in window:
                        logger.info(
                            "Seesaw check blocked: negation %r near invariant keyword %r", neg, kw
                        )
                        return False
                start = idx + 1

        return True

    def _record_blocked_promotion(self, skill_name: str, signal: Any, reason: str) -> dict:
        """Turn a silent autonomous block into a visible pending-approval with a 'why' trace."""
        import json
        from datetime import datetime

        insight = getattr(signal, "key_insight", str(signal))
        rec = {
            "ts": datetime.now(UTC).isoformat(),
            "skill": skill_name,
            "reason": reason,
            "proposed_insight": str(insight)[:500],
            "status": "pending_review",
        }
        try:
            self._APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self._APPROVALS_PATH, "a") as f:
                f.write(json.dumps(rec) + "\n")
        except Exception as exc:  # observability must never break the loop
            logger.debug("could not record blocked promotion: %s", exc)
        return rec

    @classmethod
    def get_pending_approvals(cls) -> list[dict]:
        """Operator-facing read of blocked self-mutations awaiting review (empty if none)."""
        import json

        if not cls._APPROVALS_PATH.exists():
            return []
        out = []
        try:
            for line in cls._APPROVALS_PATH.read_text().splitlines():
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        except Exception:
            pass
        return out

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

    # ------------------------------------------------------------------ #
    # SRS: Durable Loop-State Spine (SRS1-SRS3)                           #
    # Serializes cross-session SkillRefiner state so a fresh process can   #
    # restore baselines without a warm-up period.                          #
    # ------------------------------------------------------------------ #

    _DEFAULT_STATE_PATH: str = str(Path.home() / ".cohezion" / "skill_refiner_state.json")

    def to_dict(self) -> dict:
        """Serialize cross-session state to a JSON-safe dict (SRS1).

        Required keys: goal_epoch, goal_consecutive_hits, session_goal,
        goal_call_tally, autodata_wins, process_rewards, erp_history.
        """
        # ERP history: encode (skill, op) tuple keys as "skill::op" strings.
        erp_history: dict[str, list[float]] = {}
        predictor = getattr(self, "_env_predictor", None)
        if predictor is not None:
            for (sn, op), window in predictor._history.items():
                erp_history[f"{sn}::{op}"] = list(window)

        process_rewards: dict[str, list[float]] = {
            k: list(v) for k, v in getattr(self, "_process_rewards", {}).items()
        }

        return {
            "goal_epoch": getattr(self, "_goal_epoch", 0),
            "goal_consecutive_hits": getattr(self, "_goal_consecutive_hits", 0),
            "session_goal": getattr(self, "_session_goal", None),
            "goal_call_tally": dict(getattr(self, "_goal_call_tally", {})),
            "autodata_wins": dict(getattr(self, "_autodata_wins", {})),
            "process_rewards": process_rewards,
            "erp_history": erp_history,
        }

    @classmethod
    def from_dict(cls, state: dict, **kwargs: object) -> "SkillRefiner":
        """Restore a SkillRefiner from a serialized state dict (SRS2).

        Missing keys fall back to safe defaults (CB16 pattern).
        kwargs are forwarded to __init__ for dependency injection.
        """
        instance = cls(**kwargs)  # type: ignore[arg-type]
        instance._goal_epoch = int(state.get("goal_epoch", 0))
        instance._goal_consecutive_hits = int(state.get("goal_consecutive_hits", 0))
        instance._session_goal = state.get("session_goal")
        instance._goal_call_tally = dict(state.get("goal_call_tally") or {})
        instance._autodata_wins = dict(state.get("autodata_wins") or {})

        # Restore process_rewards
        for skill_name, samples in (state.get("process_rewards") or {}).items():
            instance._process_rewards[skill_name] = deque(samples, maxlen=20)

        # Restore ERP history — decode "skill::op" back to (skill, op) tuples.
        predictor = getattr(instance, "_env_predictor", None)
        if predictor is not None:
            for encoded_key, samples in (state.get("erp_history") or {}).items():
                if "::" in encoded_key:
                    sn, op = encoded_key.split("::", 1)
                    predictor._history[(sn, op)] = deque(samples, maxlen=predictor._window_size)

        return instance

    def save_state(self, path: "str | Path | None" = None) -> None:
        """Persist loop state to JSON (SRS3). Creates parent directories."""
        import json

        target = Path(path) if path is not None else Path(self._DEFAULT_STATE_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2))

    def restore_state(self, path: "str | Path | None" = None) -> bool:
        """Restore loop state from JSON (SRS3). Returns False on missing/corrupt file."""
        import json

        target = Path(path) if path is not None else Path(self._DEFAULT_STATE_PATH)
        try:
            data = json.loads(target.read_text())
            self._goal_epoch = int(data.get("goal_epoch", 0))
            self._goal_consecutive_hits = int(data.get("goal_consecutive_hits", 0))
            self._session_goal = data.get("session_goal")
            self._goal_call_tally = dict(data.get("goal_call_tally") or {})
            self._autodata_wins = dict(data.get("autodata_wins") or {})

            for skill_name, samples in (data.get("process_rewards") or {}).items():
                self._process_rewards[skill_name] = deque(samples, maxlen=20)

            predictor = getattr(self, "_env_predictor", None)
            if predictor is not None:
                for encoded_key, samples in (data.get("erp_history") or {}).items():
                    if "::" in encoded_key:
                        sn, op = encoded_key.split("::", 1)
                        predictor._history[(sn, op)] = deque(samples, maxlen=predictor._window_size)
            # Warm the shadow canary from restored process_rewards so the canary's
            # per-skill baseline window isn't empty after a process restart.  Use the
            # process_reward z-scored values as quality proxies: map raw reward magnitudes
            # back to a [0,1] quality range using sigmoid (reward ≥ 0 → quality ≥ 0.5).
            canary = getattr(self, "_shadow_canary", None)
            if canary is not None:
                for skill_name, samples in (data.get("process_rewards") or {}).items():
                    for raw in samples:
                        # Sigmoid maps reward → (0,1); positive rewards → quality > 0.5.
                        import math

                        quality = 1.0 / (1.0 + math.exp(-float(raw)))
                        canary.record(skill_name, quality)
            return True
        except Exception:
            return False

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
    def create(
        mcp_client: Any = None,
        degradation_detector: Any = None,
        journey_tracker: Any = None,
        health_oracle: Any = None,
    ) -> SkillRefiner:
        """Create a new SkillRefiner.

        Args:
            mcp_client: Optional MCPClient for vault operations
            degradation_detector: Optional DegradationDetector for per-skill drift tracking.
            journey_tracker: Optional JourneyTracker for cross-session trajectory history.
            health_oracle: Optional CompoundHealthOracle for HIHO regime tracking.

        Returns:
            SkillRefiner instance
        """
        refiner = SkillRefiner(
            mcp_client,
            degradation_detector=degradation_detector,
            journey_tracker=journey_tracker,
            health_oracle=health_oracle,
        )
        # M1: wire the FAPO R3 behavioral regression gate LIVE (it defaulted dormant). Bind a
        # local-inference runner that executes a candidate skill against a fixture input. No-op
        # until golden fixtures exist; per-fixture fail-open when lemonade is down.
        try:
            from cohezion.compound.local_inference import make_local_execute_fn

            _local = make_local_execute_fn()
            refiner._regression_run_fn = lambda candidate, inp: _local(f"{candidate}\n\n{inp}")[0]
        except Exception:  # never let gate-wiring break refiner creation
            pass
        return refiner

    @staticmethod
    def get_singleton(mcp_client: Any = None) -> SkillRefiner:
        """Get or create singleton SkillRefiner.

        Args:
            mcp_client: Optional MCPClient for vault operations

        Returns:
            Singleton SkillRefiner instance
        """
        if SkillRefinerFactory._instance is None:
            # WIRING H1: delegate to create() so the singleton ALSO wires _regression_run_fn.
            # The old `SkillRefiner(mcp_client)` left the behavioral regression gate dormant on
            # every singleton consumer (the common path), so the gate could never bite.
            SkillRefinerFactory._instance = SkillRefinerFactory.create(mcp_client)
        return SkillRefinerFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        SkillRefinerFactory._instance = None
