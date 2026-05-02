"""Dynamic context policy for adaptive breadth/depth control.

Classifies tasks into profiles (ROUTINE, FOCUSED, EXPLORATORY) and
produces ContextBudget parameters that tune how FLUX and ContextManager
gather context. Supports proactive (pre-task) classification and
hybrid reactive adjustment (immediate for critical signals, vault-logged
for soft signals).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from cohezion.flux.types import FluxSource


if TYPE_CHECKING:
    from cohezion.compound.exp_persistence.vault import VaultLogger


logger = logging.getLogger(__name__)


# Intent keyword clusters from RequestAlignmentAnalyzer (reused, not duplicated)
_INTENT_CLUSTERS: dict[str, list[str]] = {
    "generate": ["generate", "create", "write", "compose", "draft", "produce", "build"],
    "analyze": ["analyze", "evaluate", "assess", "examine", "review", "inspect", "verify"],
    "search": ["search", "find", "locate", "discover", "identify", "scan", "lookup"],
    "transform": ["transform", "convert", "format", "extract", "parse", "reformat"],
    "persist": ["persist", "save", "store", "log", "record", "commit", "push"],
}

# Cross-domain terms that signal EXPLORATORY tasks
_CROSS_DOMAIN_TERMS = frozenset(
    {
        "physics",
        "swarm",
        "compound",
        "universe",
        "bioelectric",
        "flume",
        "governance",
        "architecture",
        "design",
        "refactor",
        "migrate",
    }
)

# File/module reference pattern (signals FOCUSED)
_FILE_REF_PATTERN = re.compile(r"\b[\w/]+\.py\b|\b[\w_]+_module\b|\b(src|tests)/")


# ---------------------------------------------------------------------------
# YAML frontmatter helpers
# ---------------------------------------------------------------------------

_LEARNED_BUDGETS_BODY = """
# Learned Context Budgets

Cross-platform context policy for Cohezion compound engineering.
Updated automatically by `ContextPolicy.record_outcome()`.
"""


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Split a YAML frontmatter markdown file into (frontmatter, body).

    Returns ("", text) if no frontmatter delimiters found.
    """
    if not text.startswith("---"):
        return "", text
    end = text.find("---", 3)
    if end == -1:
        return "", text
    return text[3:end].strip(), text[end + 3 :]


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Parse YAML frontmatter from a markdown file."""
    fm_str, _ = _split_frontmatter(text)
    if not fm_str:
        return None
    return yaml.safe_load(fm_str)


class TaskProfile(Enum):
    """Task shape determines context strategy."""

    FOCUSED = "focused"
    EXPLORATORY = "exploratory"
    ROUTINE = "routine"


@dataclass(frozen=True)
class ContextBudget:
    """Dynamic context parameters for a single execution."""

    flux_top_k: int
    flux_min_relevance: float
    flux_sources: tuple[FluxSource, ...] | None  # None = all sources
    token_budget: int
    skill_overlay: bool


# Profile → default budget mapping
_PROFILE_BUDGETS: dict[TaskProfile, ContextBudget] = {
    TaskProfile.FOCUSED: ContextBudget(
        flux_top_k=5,
        flux_min_relevance=0.7,
        flux_sources=(FluxSource.VAULT, FluxSource.HISTORY),
        token_budget=800,
        skill_overlay=True,
    ),
    TaskProfile.EXPLORATORY: ContextBudget(
        flux_top_k=10,
        flux_min_relevance=0.3,
        flux_sources=None,
        token_budget=1500,
        skill_overlay=True,
    ),
    TaskProfile.ROUTINE: ContextBudget(
        flux_top_k=2,
        flux_min_relevance=0.8,
        flux_sources=(FluxSource.CACHE, FluxSource.VAULT),
        token_budget=300,
        skill_overlay=False,
    ),
}


@dataclass(frozen=True)
class ContextSignals:
    """Runtime signals used for reactive budget adjustment."""

    coherence_state: float = 1.0
    token_usage: int = 0
    alignment_score: float = 1.0
    template_hit: bool = False


class ContextPolicy:
    """Adaptive context breadth/depth controller.

    Proactive: classify_task() → TaskProfile → ContextBudget
    Reactive Tier 1: adjust_immediate() for critical signals
    Reactive Tier 2: record_soft_signal() for vault learning

    Persistence: Reads learned budgets from .context/policy/learned-budgets.json
    on init (warm start). Writes back on record_outcome() (cross-session learning).
    """

    BUDGETS_FILENAME = "learned-budgets.md"

    def __init__(
        self,
        vault_logger: VaultLogger | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._vault_logger = vault_logger
        self._budgets_path = self._resolve_budgets_path(project_root)
        self._task_overrides: list[dict[str, Any]] = []
        self._outcome_summary: dict[str, Any] = {"total_executions": 0, "by_profile": {}}
        # Instance-level copy to avoid singleton pollution across tests/instances
        self._budgets: dict[TaskProfile, ContextBudget] = dict(_PROFILE_BUDGETS)
        self._load_learned_budgets()

    # ------------------------------------------------------------------
    # Persistence: warm start + write-back
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_budgets_path(project_root: Path | None) -> Path | None:
        """Find the learned-budgets.json file."""
        if project_root is not None:
            candidate = project_root / ".context" / "policy" / ContextPolicy.BUDGETS_FILENAME
            return candidate if candidate.parent.exists() else None

        # Auto-detect: walk up from cwd
        current = Path.cwd()
        while current != current.parent:
            candidate = current / ".context" / "policy" / ContextPolicy.BUDGETS_FILENAME
            if candidate.parent.exists():
                return candidate
            current = current.parent
        return None

    def _load_learned_budgets(self) -> None:
        """Read learned budgets from YAML frontmatter markdown file.

        Silent fallback to hardcoded defaults if file missing or invalid.
        """
        if self._budgets_path is None or not self._budgets_path.exists():
            logger.debug("No learned-budgets.md found, using hardcoded defaults")
            return

        try:
            raw = self._budgets_path.read_text(encoding="utf-8")
            data = _parse_frontmatter(raw)
            if data is None:
                logger.warning("No YAML frontmatter in %s, using defaults", self._budgets_path)
                return

            profiles = data.get("profiles", {})

            for profile_name, budget_data in profiles.items():
                try:
                    profile = TaskProfile(profile_name)
                except ValueError:
                    continue

                self._budgets[profile] = ContextBudget(
                    flux_top_k=budget_data.get("flux_top_k", _PROFILE_BUDGETS[profile].flux_top_k),
                    flux_min_relevance=budget_data.get(
                        "flux_min_relevance", _PROFILE_BUDGETS[profile].flux_min_relevance
                    ),
                    flux_sources=_PROFILE_BUDGETS[profile].flux_sources,  # Not persisted
                    token_budget=budget_data.get(
                        "token_budget", _PROFILE_BUDGETS[profile].token_budget
                    ),
                    skill_overlay=budget_data.get(
                        "skill_overlay", _PROFILE_BUDGETS[profile].skill_overlay
                    ),
                )

            self._task_overrides = data.get("task_overrides", [])
            self._outcome_summary = data.get(
                "outcome_summary", {"total_executions": 0, "by_profile": {}}
            )
            logger.info(
                "Loaded learned budgets from %s (%d overrides, %d executions)",
                self._budgets_path,
                len(self._task_overrides),
                self._outcome_summary.get("total_executions", 0),
            )
        except (yaml.YAMLError, KeyError, TypeError) as e:
            logger.warning("Invalid learned-budgets.md, using defaults: %s", e)

    def save_learned_budgets(self) -> None:
        """Write current profile budgets and overrides to YAML frontmatter markdown."""
        if self._budgets_path is None:
            return

        data = {
            "version": "1.0.0",
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "profiles": {},
            "task_overrides": self._task_overrides,
            "outcome_summary": self._outcome_summary,
        }

        for profile in TaskProfile:
            budget = self._budgets[profile]
            data["profiles"][profile.value] = {
                "flux_top_k": budget.flux_top_k,
                "flux_min_relevance": budget.flux_min_relevance,
                "token_budget": budget.token_budget,
                "skill_overlay": budget.skill_overlay,
            }

        # Preserve markdown body if it exists, otherwise use default
        body = _LEARNED_BUDGETS_BODY
        if self._budgets_path.exists():
            raw = self._budgets_path.read_text(encoding="utf-8")
            _, existing_body = _split_frontmatter(raw)
            if existing_body.strip():
                body = existing_body

        frontmatter = yaml.dump(data, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter}---\n{body}"

        try:
            self._budgets_path.write_text(content, encoding="utf-8")
            logger.debug("Saved learned budgets to %s", self._budgets_path)
        except OSError as e:
            logger.warning("Failed to save learned budgets: %s", e)

    # ------------------------------------------------------------------
    # Proactive classification
    # ------------------------------------------------------------------

    def classify_task(
        self,
        task_description: str,
        operation_type: str,
        template_similarity: float = 0.0,
        drift_risk: float = 0.0,
    ) -> TaskProfile:
        """Classify a task into a profile before execution starts.

        Args:
            task_description: What the task does
            operation_type: Operation type (generate, analyze, search, etc.)
            template_similarity: Similarity score from template match (0-1)
            drift_risk: Drift risk from alignment analysis (0-1)

        Returns:
            TaskProfile determining context strategy
        """
        # ROUTINE: high template match (strongest signal — skip everything else)
        if template_similarity > 0.8:
            logger.debug(
                "Task classified as ROUTINE (template_similarity=%.2f)", template_similarity
            )
            return TaskProfile.ROUTINE

        # EXPLORATORY: high drift risk overrides simple-task heuristics
        if drift_risk > 0.3:
            logger.debug("Task classified as EXPLORATORY (drift_risk=%.2f)", drift_risk)
            return TaskProfile.EXPLORATORY

        desc_lower = task_description.lower()
        desc_len = len(task_description)

        # ROUTINE: simple persist/search with short description
        if operation_type in ("persist", "search") and desc_len < 100:
            logger.debug("Task classified as ROUTINE (short %s task)", operation_type)
            return TaskProfile.ROUTINE

        domain_hits = sum(1 for term in _CROSS_DOMAIN_TERMS if term in desc_lower)
        if domain_hits >= 2:
            logger.debug("Task classified as EXPLORATORY (%d cross-domain terms)", domain_hits)
            return TaskProfile.EXPLORATORY

        cluster_hits = self._count_intent_clusters(desc_lower)
        if cluster_hits >= 2 and desc_len > 200:
            logger.debug(
                "Task classified as EXPLORATORY (%d intent clusters, %d chars)",
                cluster_hits,
                desc_len,
            )
            return TaskProfile.EXPLORATORY

        # FOCUSED: default (single-domain, moderate complexity)
        logger.debug("Task classified as FOCUSED (default)")
        return TaskProfile.FOCUSED

    def get_budget(self, profile: TaskProfile) -> ContextBudget:
        """Get the ContextBudget for a given profile (learned or default)."""
        return self._budgets[profile]

    # ------------------------------------------------------------------
    # Reactive Tier 1: Immediate adjustment
    # ------------------------------------------------------------------

    def adjust_immediate(
        self,
        current: ContextBudget,
        signals: ContextSignals,
    ) -> ContextBudget:
        """Adjust budget immediately for critical signals.

        Only fires for coherence collapse or token overflow — signals
        that indicate the current execution is at risk.

        Args:
            current: Active context budget
            signals: Runtime execution signals

        Returns:
            Adjusted budget (may be identical if no critical signals)
        """
        adjustments: dict[str, Any] = {}

        # Critical: coherence below HIHO threshold → broaden search
        if signals.coherence_state < 0.5:
            adjustments["flux_top_k"] = min(current.flux_top_k + 3, 15)
            adjustments["flux_min_relevance"] = max(current.flux_min_relevance - 0.1, 0.1)
            logger.info(
                "Tier 1 adjustment: coherence %.2f < 0.5 → broadening (top_k=%d, min_rel=%.2f)",
                signals.coherence_state,
                adjustments["flux_top_k"],
                adjustments["flux_min_relevance"],
            )

        # Critical: token overflow → narrow search
        if current.token_budget > 0 and signals.token_usage > current.token_budget * 0.8:
            adjustments["flux_top_k"] = min(adjustments.get("flux_top_k", current.flux_top_k), 2)
            adjustments["flux_min_relevance"] = max(
                adjustments.get("flux_min_relevance", current.flux_min_relevance),
                current.flux_min_relevance + 0.1,
            )
            logger.info(
                "Tier 1 adjustment: tokens %d > 80%% of %d → narrowing",
                signals.token_usage,
                current.token_budget,
            )

        if not adjustments:
            return current

        return replace(current, **adjustments)

    # ------------------------------------------------------------------
    # Reactive Tier 2: Soft signal learning
    # ------------------------------------------------------------------

    def record_soft_signal(
        self,
        signals: ContextSignals,
        profile: TaskProfile,
        task_description: str,
    ) -> None:
        """Log soft signals to vault and persist as task overrides.

        These don't change the current budget — they inform future
        classify_task() calls via vault pattern queries and persisted
        task_overrides in .context/policy/learned-budgets.json.

        Args:
            signals: Runtime execution signals
            profile: Profile used for this execution
            task_description: Task description for vault indexing
        """
        entries: list[dict[str, Any]] = []

        if signals.alignment_score < 0.6:
            entries.append(
                {
                    "signal": "drift_prone",
                    "alignment_score": signals.alignment_score,
                    "profile": profile.value,
                    "recommendation": "include HISTORY source for similar tasks",
                }
            )

        if signals.template_hit and profile == TaskProfile.EXPLORATORY:
            entries.append(
                {
                    "signal": "over_classified",
                    "profile": profile.value,
                    "recommendation": "downgrade to ROUTINE for similar tasks",
                }
            )

        if not entries:
            return

        # Persist to task_overrides in JSON (cross-session)
        for entry in entries:
            self._task_overrides.append(
                {
                    "signal": entry["signal"],
                    "profile": entry["profile"],
                    "task_snippet": task_description[:100],
                    "recommendation": entry["recommendation"],
                    "recorded_at": datetime.now(tz=UTC).isoformat(),
                }
            )
        self.save_learned_budgets()

        # Also log to vault if available
        if self._vault_logger is not None:
            for entry in entries:
                try:
                    self._vault_logger.log_experiment(
                        project="cohezion",
                        hypothesis=f"Context profile {profile.value} optimal for task type",
                        method="context_policy_feedback",
                        result=f"Signal: {entry['signal']}",
                        learnings=f"Recommendation: {entry['recommendation']}",
                        title=f"context-policy-{entry['signal']}",
                    )
                    logger.debug("Tier 2: recorded soft signal '%s'", entry["signal"])
                except Exception:
                    logger.debug("Failed to record soft signal to vault (non-blocking)")

    # ------------------------------------------------------------------
    # Outcome feedback
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        profile: TaskProfile,
        budget: ContextBudget,
        execution_success: bool,
        coherence_final: float,
    ) -> None:
        """Log context strategy outcome and persist to JSON file.

        Updates outcome_summary and writes back to .context/policy/learned-budgets.json
        so the next session (any tool) warm-starts with accumulated experience.

        Args:
            profile: Profile used for this execution
            budget: Budget used (may have been adjusted)
            execution_success: Whether the task succeeded
            coherence_final: Final coherence score
        """
        # Update in-memory summary
        self._outcome_summary["total_executions"] = (
            self._outcome_summary.get("total_executions", 0) + 1
        )
        by_profile = self._outcome_summary.setdefault("by_profile", {})
        profile_stats = by_profile.setdefault(
            profile.value, {"successes": 0, "failures": 0, "avg_coherence": 0.0, "count": 0}
        )
        if execution_success:
            profile_stats["successes"] += 1
        else:
            profile_stats["failures"] += 1
        n = profile_stats["count"] + 1
        profile_stats["avg_coherence"] = (
            profile_stats["avg_coherence"] * profile_stats["count"] + coherence_final
        ) / n
        profile_stats["count"] = n

        # Persist to JSON file (cross-session, cross-platform)
        self.save_learned_budgets()

        # Also log to vault if available
        if self._vault_logger is not None:
            try:
                self._vault_logger.log_experiment(
                    project="cohezion",
                    hypothesis=f"Profile {profile.value} produces good outcomes",
                    method="context_policy_outcome",
                    result=f"success={execution_success}, coherence={coherence_final:.2f}",
                    learnings=(
                        f"Budget: top_k={budget.flux_top_k}, "
                        f"min_rel={budget.flux_min_relevance:.2f}, "
                        f"tokens={budget.token_budget}"
                    ),
                    title=f"context-outcome-{profile.value}",
                )
            except Exception:
                logger.debug("Failed to record context outcome to vault (non-blocking)")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_intent_clusters(text: str) -> int:
        """Count how many distinct intent clusters are referenced."""
        count = 0
        for keywords in _INTENT_CLUSTERS.values():
            if any(kw in text for kw in keywords):
                count += 1
        return count
