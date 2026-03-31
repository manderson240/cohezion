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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


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


class SkillRefiner:
    """Refines PRIME skill definitions based on execution results."""

    SKILLS_DIR = Path(__file__).parent.parent / "skills"

    def __init__(self, mcp_client: Any = None):
        """Initialize skill refiner.

        Args:
            mcp_client: Optional MCPClient for vault operations
        """
        self.mcp_client = mcp_client

    def refine(
        self,
        skill_name: str,
        operation_type: str,
        execution_result: dict[str, Any],
        patterns_extracted: list[str] | None = None,
    ) -> str | None:
        """Learn from execution result and refine PRIME skill.

        Analyzes execution metrics and appends learned refinements
        to the PRIME skill definition file.

        Args:
            skill_name: Name of the skill that was executed
            operation_type: Type of operation (generate, analyze, search, etc.)
            execution_result: ExecutionResult dict with metrics and outputs
            patterns_extracted: List of vault pattern paths from execution

        Returns:
            Path to refined skill file if successful, None otherwise
        """
        try:
            # Extract metrics
            metrics = self._extract_metrics(execution_result)

            # Only refine on success
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
            )

            persist_learning(learning)
            logger.info("Knowledge bridge: persisted skill refinement for %s", skill_name)

        except Exception:
            logger.debug("Skill refinement vault persistence failed (non-blocking)", exc_info=True)

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
        recommendation = self._generate_recommendation(metrics, operation_type)
        confidence = min(0.95, metrics.quality_score)

        return LearningSignal(
            skill_name=skill_name,
            operation_type=operation_type,
            key_insight=key_insight,
            metric_change=metric_change,
            recommendation=recommendation,
            confidence=confidence,
        )

    def _generate_recommendation(self, metrics: ExecutionMetrics, operation_type: str) -> str:
        """Generate recommendation based on metrics.

        Args:
            metrics: ExecutionMetrics
            operation_type: Type of operation

        Returns:
            Recommendation string
        """
        if metrics.quality_score > 0.9:
            return f"Prioritize this configuration for {operation_type} operations"
        elif metrics.token_efficiency < 200:
            return f"High token efficiency - consider as baseline for {operation_type}"
        elif metrics.cached_hits > 2:
            return "Cache-friendly pattern - promote to fast path"
        else:
            return f"Acceptable performance for {operation_type} operations"

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
