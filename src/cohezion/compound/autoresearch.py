# ruff: noqa: SIM102, S112, E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Autoresearch-driven refinement and experiential learning.

This module provides:
1. AutoresearchEngine - Identifies optimization opportunities from metrics
2. VaultLearningCapture - Captures learnings to vault for compound growth
   (formerly RetrospectionEngine; renamed 2026-04-22 in Sprint A to disambiguate
   from core.compound.retrospection.RetrospectionEngine which parses KG files,
   and from compound.retrospection_summary.CycleRetrospectionEngine which
   summarizes per-cycle metrics). The old name is re-exported at module bottom.
3. AsyncMetricsSkillRefiner - Async metric-based skill refinement
   (formerly SkillRefiner; renamed same reason — canonical SkillRefiner is
   compound.skill_refiner.SkillRefiner).
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime as dt_class
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics from a single execution."""

    request: str
    tokens_used: int
    prompt_tokens: int
    response_tokens: int
    duration_seconds: float
    cache_hits: int
    cache_misses: int
    coherence: float
    success: bool
    skill_used: str | None = None
    timestamp: str = field(default_factory=lambda: dt_class.now(UTC).isoformat())
    lessons: list[str] = field(default_factory=list)


@dataclass
class ImprovementOpportunity:
    """An identified improvement opportunity."""

    category: str  # "cache", "token_efficiency", "parallelism", "architecture"
    priority: int  # 1-10, 10 being highest
    current_value: float
    target_value: float
    potential_impact: str
    implementation_effort: str  # "low", "medium", "high"
    recommendation: str


class AutoresearchEngine:
    """Engine that analyzes execution metrics and suggests improvements.

    Similar to thermal autoresearch but focused on MCP integration
    and compound engineering optimization.
    """

    # HIHO balance threshold: exploit when coherence >= this, explore when below
    HIHO_THRESHOLD = 0.5

    def __init__(self):
        self.thresholds = {
            "min_cache_hit_rate": 0.80,
            "max_tokens_per_request": 5000,
            "max_vault_latency_ms": 100,
            "min_coherence": 0.70,
        }
        self._logged_opportunity_hashes: set[str] = set()

    def _opportunity_hash(self, opp: "ImprovementOpportunity") -> str:
        key = f"{opp.category}:{opp.recommendation}:{opp.priority}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _mark_logged(self, opp: "ImprovementOpportunity") -> None:
        self._logged_opportunity_hashes.add(self._opportunity_hash(opp))

    def _is_duplicate(self, opp: "ImprovementOpportunity") -> bool:
        return self._opportunity_hash(opp) in self._logged_opportunity_hashes

    async def analyze(self, metrics: dict[str, Any]) -> list[ImprovementOpportunity]:
        """Analyze metrics and identify improvement opportunities.

        Args:
            metrics: Execution metrics dictionary

        Returns:
            List of improvement opportunities sorted by priority
        """
        opportunities = []

        # Check cache hit rate
        cache_hit_rate = metrics.get("cache_hit_rate", 0)
        if cache_hit_rate < self.thresholds["min_cache_hit_rate"]:
            opportunities.append(
                ImprovementOpportunity(
                    category="cache",
                    priority=9,
                    current_value=cache_hit_rate,
                    target_value=self.thresholds["min_cache_hit_rate"],
                    potential_impact="Reduce token costs by 60%",
                    implementation_effort="medium",
                    recommendation="Increase semantic_cache_size to 4096 entries and enable cross_model_sharing",
                )
            )

        # Check token efficiency
        tokens_per_request = metrics.get("avg_tokens_per_request", 0)
        if tokens_per_request > self.thresholds["max_tokens_per_request"]:
            opportunities.append(
                ImprovementOpportunity(
                    category="token_efficiency",
                    priority=8,
                    current_value=tokens_per_request,
                    target_value=self.thresholds["max_tokens_per_request"],
                    potential_impact="Achieve 12x efficiency target",
                    implementation_effort="low",
                    recommendation="Enable LOCAL_OFFLOAD_PRIME for embeddings and classification",
                )
            )

        # Check vault write latency
        vault_latency = metrics.get("vault_write_latency_ms", 0)
        if vault_latency > self.thresholds["max_vault_latency_ms"]:
            opportunities.append(
                ImprovementOpportunity(
                    category="architecture",
                    priority=7,
                    current_value=vault_latency,
                    target_value=self.thresholds["max_vault_latency_ms"],
                    potential_impact="Reduce session overhead by 40%",
                    implementation_effort="high",
                    recommendation="Implement async batch writes to vault with write-behind caching",
                )
            )

        # Check coherence
        coherence = metrics.get("avg_coherence", 1.0)
        if coherence < self.thresholds["min_coherence"]:
            opportunities.append(
                ImprovementOpportunity(
                    category="cache",
                    priority=8,
                    current_value=coherence,
                    target_value=self.thresholds["min_coherence"],
                    potential_impact="Reduce rework by 50%",
                    implementation_effort="medium",
                    recommendation="Enhance RequestAlignmentAnalyzer with skill-specific thresholds",
                )
            )

        # Sort by priority (descending)
        return sorted(opportunities, key=lambda x: x.priority, reverse=True)

    async def generate_research_plan(
        self, opportunities: list[ImprovementOpportunity]
    ) -> dict[str, Any]:
        """Generate a research plan based on opportunities.

        Args:
            opportunities: List of improvement opportunities

        Returns:
            Research plan with experiments
        """
        experiments = []

        for opp in opportunities[:3]:  # Top 3 priorities
            experiments.append(
                {
                    "hypothesis": f"Implementing {opp.recommendation} will improve {opp.category}",
                    "method": "A/B test: compare current vs optimized implementation",
                    "metrics": ["token_efficiency", "cache_hit_rate", "duration"],
                    "expected_outcome": f"{opp.potential_impact}",
                    "priority": opp.priority,
                }
            )

        return {
            "title": f"MCP Optimization Research Plan ({dt_class.now(UTC).strftime('%Y-%m-%d')})",
            "experiments": experiments,
            "estimated_effort": "medium",
            "expected_roi": "12x token efficiency improvement",
        }

    async def generate_next_experiments(
        self,
        n: int = 5,
        session_metrics: dict[str, Any] | None = None,
        retired_labels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate n next experiments using HIHO balance.

        Exploit (tune parameters) when coherence >= HIHO_THRESHOLD.
        Explore (new hypotheses) when coherence < HIHO_THRESHOLD.
        If retired_labels provided, generate replacement experiments first.
        """
        metrics = session_metrics or {}
        coherence = metrics.get("avg_coherence", self.HIHO_THRESHOLD)
        mode = "exploit" if coherence >= self.HIHO_THRESHOLD else "explore"

        results: list[dict[str, Any]] = []

        # First: generate replacements for retired experiments
        for label in (retired_labels or []):
            if len(results) >= n:
                break
            results.append({
                "mode": mode,
                "replaces": label,
                "hypothesis": (
                    f"Parameter sweep of {label} (exploit variant)"
                    if mode == "exploit"
                    else f"New hypothesis replacing {label}"
                ),
                "parameter": f"{label}_lr" if mode == "exploit" else None,
                "priority": "high",
            })

        exploit_templates = [
            {"parameter": "learning_rate", "range": [0.5, 1.0, 1.5, 2.0]},
            {"parameter": "n_phase", "range": [3, 5, 7, 10]},
            {"parameter": "coherence_threshold", "range": [0.6, 0.7, 0.8, 0.85]},
            {"parameter": "batch_size", "range": [2, 4, 8, 16]},
            {"parameter": "retirement_cv", "range": [0.03, 0.05, 0.07]},
        ]
        explore_templates = [
            {"hypothesis": "Adaptive lr based on gap magnitude reduces overshoot"},
            {"hypothesis": "Parallel deliberations increase diversity score"},
            {"hypothesis": "Coherence-weighted voting improves overall quality 5%+"},
            {"hypothesis": "Multi-cycle compounding produces geometric delta decay"},
            {"hypothesis": "Voice-specific calibration outperforms uniform adjustment"},
        ]

        idx = 0
        while len(results) < n:
            if mode == "exploit":
                t = exploit_templates[idx % len(exploit_templates)]
                results.append({
                    "mode": "exploit",
                    "hypothesis": f"Sweep {t['parameter']} over {t['range']}",
                    "parameter": t["parameter"],
                    "priority": "medium",
                })
            else:
                t = explore_templates[idx % len(explore_templates)]
                results.append({
                    "mode": "explore",
                    "hypothesis": t["hypothesis"],
                    "priority": "medium",
                })
            idx += 1

        return results[:n]


class VaultLearningCapture:
    """Captures execution learnings to vault for compound growth.

    Renamed from RetrospectionEngine 2026-04-22 to disambiguate from
    core.compound.retrospection.RetrospectionEngine (KG parser) and
    compound.retrospection_summary.CycleRetrospectionEngine (per-cycle
    summaries). See patterns/deferred-sprints-consolidation-and-skills-migration.md.
    The old name is re-exported at the bottom of this module for backward compat.
    """

    def __init__(self, vault_path: str = "cloud-vault-mcp/vault"):
        self.vault_path = Path(vault_path)

    async def capture_learning(
        self, execution_result: dict[str, Any], mcp_client=None
    ) -> str | None:
        """Capture learning from execution to vault.

        Args:
            execution_result: Result from execution
            mcp_client: MCP client for vault operations

        Returns:
            Path to saved learning note or None
        """
        try:
            # Build learning entry
            learning = {
                "title": f"Session Learning: {execution_result.get('request', 'Unknown')[:50]}",
                "timestamp": dt_class.now(UTC).isoformat(),
                "metrics": {
                    "tokens_used": execution_result.get("tokens_used", 0),
                    "cache_hits": execution_result.get("cache_hits", 0),
                    "duration_seconds": execution_result.get("duration_seconds", 0),
                    "coherence": execution_result.get("coherence", 0.0),
                },
                "lessons": execution_result.get("lessons", []),
                "success": execution_result.get("success", True),
                "skill_used": execution_result.get("skill_used"),
            }

            logger.info(f"Attempting to capture learning: {learning['title']}")

            # Persist via MCP if available
            if mcp_client:
                # 1. Store in Obsidian Vault
                try:
                    # Convert lessons list to markdown string
                    lessons_str = "\n".join([f"- {L}" for L in learning["lessons"]])

                    logger.info(f"Logging to vault via {mcp_client.config.server_url}...")
                    path = await mcp_client.vault_log_experiment(
                        project="cohezion",
                        title=learning["title"],
                        hypothesis="Session execution",
                        method="Automated capture",
                        result="success" if learning["success"] else "failure",
                        learnings=lessons_str,
                        **learning["metrics"],
                    )
                    logger.info(f"Vault capture success: {path}")
                except Exception as vault_e:
                    logger.error(f"Vault capture failed: {vault_e}")
                    path = None

                # 2. Store in SurrealDB (Universe Nodes)
                try:
                    # Generate a learning ID
                    import hashlib

                    l_id = f"L_{hashlib.sha256(learning['title'].encode()).hexdigest()[:8]}"

                    logger.info(f"Storing learning in SurrealDB: {l_id}...")
                    await mcp_client._call_tool(
                        "store_learning",
                        {
                            "learning_id": l_id,
                            "title": learning["title"],
                            "content": json.dumps(learning, indent=2),
                            "pattern": learning.get("skill_used", "general"),
                            "score": float(learning["metrics"].get("coherence", 0.7)),
                        },
                    )
                    logger.info("SurrealDB storage success.")
                except Exception as db_e:
                    logger.warning(f"Failed to store learning in SurrealDB: {db_e}")

                if path:
                    logger.info(f"Learning captured to vault and database: {path}")
                return path
            else:
                logger.warning(
                    "No mcp_client provided to capture_learning, falling back to local file."
                )
                # Fallback to local file
                fallback_path = (
                    self.vault_path
                    / "logs"
                    / f"learning_{dt_class.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
                )
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
                fallback_path.write_text(json.dumps(learning, indent=2))
                logger.info(f"Learning captured locally: {fallback_path}")
                return str(fallback_path)

        except Exception as e:
            logger.exception(f"Unexpected error in capture_learning: {e}")
            return None

    async def extract_patterns(self, learning_paths: list[str]) -> list[dict]:
        """Extract recurring patterns from multiple learnings.

        Args:
            learning_paths: List of paths to learning files

        Returns:
            List of identified patterns
        """
        patterns = []

        # Aggregate lessons
        all_lessons = []
        for path in learning_paths:
            try:
                data = json.loads(Path(path).read_text())
                all_lessons.extend(data.get("lessons", []))
            except Exception:
                continue

        # Identify recurring patterns
        lesson_counts: dict[str, int] = {}
        for lesson in all_lessons:
            lesson_counts[lesson] = lesson_counts.get(lesson, 0) + 1

        # Extract patterns that appear multiple times
        for lesson, count in lesson_counts.items():
            if count >= 2:
                patterns.append(
                    {
                        "pattern": lesson,
                        "frequency": count,
                        "confidence": min(count / 5, 1.0),  # Cap at 5 occurrences
                        "type": "recurring_lesson",
                    }
                )

        return patterns


class AsyncMetricsSkillRefiner:
    """Updates skill definitions based on execution feedback (async, metric-driven).

    Renamed from SkillRefiner 2026-04-22. Canonical synchronous implementation
    is compound.skill_refiner.SkillRefiner. This async version is kept for
    callers that need metric-based refinement inside an async pipeline.
    Re-exported as SkillRefiner at module bottom for backward compat.
    """

    def __init__(self, skills_dir: str = "src/cohezion/skills"):
        self.skills_dir = Path(skills_dir)
        self.max_refinements = 5  # Prevent infinite loops

    async def refine_from_execution(
        self, skill_name: str, metrics: ExecutionMetrics, mcp_client=None
    ) -> dict[str, Any]:
        """Refine a skill based on execution metrics.

        Args:
            skill_name: Name of skill to refine
            metrics: Execution metrics
            mcp_client: MCP client for vault operations

        Returns:
            Refinement result
        """
        refinements = []

        # Check token efficiency
        if metrics.tokens_used > 5000:
            refinements.append(
                {
                    "type": "token_optimization",
                    "finding": f"High token usage: {metrics.tokens_used}",
                    "recommendation": "Add prompt template optimization",
                }
            )

        # Check coherence
        if metrics.coherence < 0.7:
            refinements.append(
                {
                    "type": "coherence_improvement",
                    "finding": f"Low coherence: {metrics.coherence:.2f}",
                    "recommendation": "Enhance skill description with examples",
                }
            )

        # Check cache utilization
        if metrics.cache_hits == 0 and metrics.tokens_used > 1000:
            refinements.append(
                {
                    "type": "cache_optimization",
                    "finding": "No cache hits on large request",
                    "recommendation": "Add semantic cache key pattern",
                }
            )

        # Log refinement to vault
        if mcp_client and refinements:
            await mcp_client.vault_write(
                f"cerebellum/skill-refinements/{skill_name}_{dt_class.now(UTC).strftime('%Y%m%d')}.md",
                json.dumps(
                    {
                        "skill": skill_name,
                        "refinements": refinements,
                        "metrics": {
                            "tokens_used": metrics.tokens_used,
                            "coherence": metrics.coherence,
                            "cache_hits": metrics.cache_hits,
                        },
                    },
                    indent=2,
                ),
            )

        return {
            "skill": skill_name,
            "refinements": refinements,
            "refinement_count": len(refinements),
            "success": len(refinements) > 0,
        }

    async def apply_refinement(self, skill_path: str, refinement: dict[str, Any]) -> bool:
        """Apply a refinement to a skill file.

        Args:
            skill_path: Path to skill file
            refinement: Refinement to apply

        Returns:
            True if successfully applied
        """
        try:
            # Read current skill
            skill_file = Path(skill_path)
            if not skill_file.exists():
                logger.warning(f"Skill file not found: {skill_path}")
                return False

            content = skill_file.read_text()

            # Apply refinement based on type
            if refinement["type"] == "token_optimization":
                # Add token efficiency note
                if "Token Efficiency" not in content:
                    content += "\n\n## Token Efficiency\n\n"
                    content += "This skill is optimized for minimal token usage.\n"

            elif refinement["type"] == "coherence_improvement":
                # Add examples section
                if "Examples" not in content:
                    content += "\n\n## Examples\n\n"
                    content += "### Example 1: Basic Usage\n"
                    content += "```\n[example here]\n```\n"

            # Write back
            skill_file.write_text(content)
            logger.info(f"Applied refinement to {skill_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply refinement: {e}")
            return False


class ExperientialLearningLoop:
    """Main loop that ties together autoresearch, retrospection, and refinement."""

    def __init__(self):
        self.autoresearch = AutoresearchEngine()
        self.retrospection = VaultLearningCapture()
        self.refiner = AsyncMetricsSkillRefiner()
        self.learning_buffer = []

    async def process_execution(
        self, execution_result: dict[str, Any], mcp_client=None
    ) -> dict[str, Any]:
        """Process a single execution through the learning loop.

        Args:
            execution_result: Result from execution
            mcp_client: MCP client for vault operations

        Returns:
            Processing results
        """
        results = {}

        # Ensure client is connected if provided
        if mcp_client and hasattr(mcp_client, "connect"):
            try:
                await mcp_client.connect()
            except Exception as conn_e:
                logger.warning(f"MCP Client connection failed: {conn_e}")

        # Step 1: Capture learning to vault
        learning_path = await self.retrospection.capture_learning(execution_result, mcp_client)
        results["learning_captured"] = learning_path is not None

        # Step 2: Refine skill if applicable
        skill = execution_result.get("skill_used")
        if skill:
            metrics = ExecutionMetrics(
                request=execution_result.get("request", ""),
                tokens_used=execution_result.get("tokens_used", 0),
                prompt_tokens=execution_result.get("prompt_tokens", 0),
                response_tokens=execution_result.get("response_tokens", 0),
                duration_seconds=execution_result.get("duration_seconds", 0),
                cache_hits=execution_result.get("cache_hits", 0),
                cache_misses=execution_result.get("cache_misses", 0),
                coherence=execution_result.get("coherence", 0.0),
                success=execution_result.get("success", True),
                skill_used=skill,
            )

            refinement = await self.refiner.refine_from_execution(skill, metrics, mcp_client)
            results["skill_refinement"] = refinement

        # Step 3: Check if we should run autoresearch
        self.learning_buffer.append(execution_result)
        if len(self.learning_buffer) >= 10:
            # Analyze accumulated metrics
            avg_cache_hit = sum(
                r.get("cache_hits", 0) / max(r.get("cache_hits", 0) + r.get("cache_misses", 0), 1)
                for r in self.learning_buffer
            ) / len(self.learning_buffer)

            avg_tokens = sum(r.get("tokens_used", 0) for r in self.learning_buffer) / len(
                self.learning_buffer
            )

            metrics = {
                "cache_hit_rate": avg_cache_hit,
                "avg_tokens_per_request": avg_tokens,
                "vault_write_latency_ms": 50,  # Estimated
                "avg_coherence": 0.85,  # Estimated
            }

            opportunities = await self.autoresearch.analyze(metrics)
            if opportunities:
                research_plan = await self.autoresearch.generate_research_plan(opportunities)
                results["research_plan"] = research_plan

            # Clear buffer
            self.learning_buffer = []

        return results


# Backward-compat aliases. Deprecated — prefer the new names which disambiguate
# from core.compound.retrospection.RetrospectionEngine (KG parser) and
# compound.skill_refiner.SkillRefiner (canonical sync implementation).
# These aliases will be removed in a future release once all callers migrate.
RetrospectionEngine = VaultLearningCapture
SkillRefiner = AsyncMetricsSkillRefiner