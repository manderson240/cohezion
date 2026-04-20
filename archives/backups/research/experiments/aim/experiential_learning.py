"""
Experiential Learning Engine for AIMO

Learns from:
- Success patterns (what worked)
- Failure patterns (what didn't)
- Strategy effectiveness (which approaches succeed)
- Problem similarity (transfer learning)

Continuously improves through vault-based knowledge sharing.
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class LearningExperience:
    """Single learning experience."""

    experience_id: str
    problem_id: str
    problem_type: str
    strategy_used: str
    success: bool
    accuracy: float
    coherence: float
    tokens_used: int
    duration_seconds: float
    timestamp: str
    lessons_learned: List[str]
    similar_experiences: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperientialLearningEngine:
    """
    Experiential learning engine for AIMO.

    Features:
    - Success pattern extraction
    - Failure pattern analysis
    - Strategy effectiveness tracking
    - Problem similarity clustering
    - Vault-based knowledge sharing
    """

    def __init__(
        self,
        vault_path: str = "~/vaults/cohezion-vault/regions/cerebrum/aimo/experiences",
        learning_rate: float = 0.1,
    ):
        self.vault_path = Path(vault_path).expanduser()
        self.vault_path.mkdir(parents=True, exist_ok=True)

        self.learning_rate = learning_rate

        # Experience storage
        self.experiences: List[LearningExperience] = []
        self.success_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.failure_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.strategy_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {
                "attempts": 0,
                "successes": 0,
                "avg_coherence": 0.0,
                "avg_tokens": 0,
            }
        )

        # Problem type clustering
        self.problem_clusters: Dict[str, List[str]] = defaultdict(list)

        # Load existing experiences
        self._load_experiences()

    def record_experience(
        self,
        problem_id: str,
        problem_type: str,
        strategy_used: str,
        success: bool,
        accuracy: float,
        coherence: float,
        tokens_used: int,
        duration_seconds: float,
        lessons_learned: Optional[List[str]] = None,
    ) -> LearningExperience:
        """Record a learning experience."""
        experience_id = f"exp_{int(time.time() * 1000)}_{problem_id}"

        # Find similar experiences
        similar = self._find_similar_experiences(problem_type)

        experience = LearningExperience(
            experience_id=experience_id,
            problem_id=problem_id,
            problem_type=problem_type,
            strategy_used=strategy_used,
            success=success,
            accuracy=accuracy,
            coherence=coherence,
            tokens_used=tokens_used,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat(),
            lessons_learned=lessons_learned or [],
            similar_experiences=similar,
        )

        # Store
        self.experiences.append(experience)

        # Update patterns
        self._update_patterns(experience)

        # Update strategy stats
        self._update_strategy_stats(experience)

        # Update problem clusters
        self.problem_clusters[problem_type].append(problem_id)

        # Persist to vault
        self._persist_experience(experience)

        logger.info(
            f"Recorded experience: {experience_id} (success={success}, coherence={coherence:.3f})"
        )

        return experience

    def _update_patterns(self, experience: LearningExperience):
        """Update success/failure patterns."""
        pattern_data = {
            "problem_type": experience.problem_type,
            "strategy": experience.strategy_used,
            "coherence": experience.coherence,
            "tokens": experience.tokens_used,
            "lessons": experience.lessons_learned,
            "timestamp": experience.timestamp,
        }

        if experience.success:
            self.success_patterns[experience.problem_type].append(pattern_data)
            # Keep only last 20 patterns per type
            if len(self.success_patterns[experience.problem_type]) > 20:
                self.success_patterns[experience.problem_type] = self.success_patterns[
                    experience.problem_type
                ][-20:]
        else:
            self.failure_patterns[experience.problem_type].append(pattern_data)
            if len(self.failure_patterns[experience.problem_type]) > 20:
                self.failure_patterns[experience.problem_type] = self.failure_patterns[
                    experience.problem_type
                ][-20:]

    def _update_strategy_stats(self, experience: LearningExperience):
        """Update strategy effectiveness statistics."""
        stats = self.strategy_stats[experience.strategy_used]

        stats["attempts"] += 1
        if experience.success:
            stats["successes"] += 1

        # Running average
        n = stats["attempts"]
        stats["avg_coherence"] = (stats["avg_coherence"] * (n - 1) + experience.coherence) / n
        stats["avg_tokens"] = (stats["avg_tokens"] * (n - 1) + experience.tokens_used) / n

    def _find_similar_experiences(self, problem_type: str, limit: int = 5) -> List[str]:
        """Find similar experiences for transfer learning."""
        similar_ids = []

        for exp in reversed(self.experiences[-50:]):  # Last 50 experiences
            if exp.problem_type == problem_type:
                similar_ids.append(exp.experience_id)
                if len(similar_ids) >= limit:
                    break

        return similar_ids

    def _persist_experience(self, experience: LearningExperience):
        """Persist experience to vault."""
        # Save individual experience
        exp_file = self.vault_path / f"{experience.experience_id}.json"
        with open(exp_file, "w") as f:
            json.dump(experience.to_dict(), f, indent=2)

        # Update experience index
        index_file = self.vault_path / "index.json"
        if index_file.exists():
            with open(index_file) as f:
                index = json.load(f)
        else:
            index = {"experiences": [], "last_updated": None}

        index["experiences"].append(experience.experience_id)
        index["last_updated"] = datetime.now().isoformat()

        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)

    def _load_experiences(self):
        """Load experiences from vault."""
        index_file = self.vault_path / "index.json"
        if not index_file.exists():
            return

        with open(index_file) as f:
            index = json.load(f)

        for exp_id in index.get("experiences", [])[-100:]:  # Load last 100
            exp_file = self.vault_path / f"{exp_id}.json"
            if exp_file.exists():
                with open(exp_file) as f:
                    data = json.load(f)
                    exp = LearningExperience(**data)
                    self.experiences.append(exp)
                    self._update_patterns(exp)
                    self._update_strategy_stats(exp)

        logger.info(f"Loaded {len(self.experiences)} experiences from vault")

    def get_best_strategy(self, problem_type: str) -> str:
        """Get best strategy for problem type based on historical success."""
        # Check success patterns
        if problem_type in self.success_patterns:
            patterns = self.success_patterns[problem_type]
            if patterns:
                # Most successful strategy
                strategy_counts = defaultdict(int)
                for p in patterns:
                    strategy_counts[p["strategy"]] += 1

                best = max(strategy_counts, key=strategy_counts.get)
                logger.info(
                    f"Best strategy for {problem_type}: {best} ({strategy_counts[best]} successes)"
                )
                return best

        # Fallback to strategy stats
        best_strategy = None
        best_success_rate = 0.0

        for strategy, stats in self.strategy_stats.items():
            if stats["attempts"] > 0:
                success_rate = stats["successes"] / stats["attempts"]
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_strategy = strategy

        return best_strategy or "standard"

    def get_lessons_for_problem(self, problem_type: str) -> List[str]:
        """Get lessons learned for similar problems."""
        lessons = []

        # From success patterns
        for pattern in self.success_patterns.get(problem_type, [])[-5:]:
            lessons.extend(pattern.get("lessons", []))

        # From failure patterns (what to avoid)
        for pattern in self.failure_patterns.get(problem_type, [])[-5:]:
            for lesson in pattern.get("lessons", []):
                if "avoid" not in lesson.lower():
                    lessons.append(f"Avoid: {lesson}")

        return list(set(lessons))  # Deduplicate

    def get_strategy_recommendation(self, problem_type: str) -> Dict[str, Any]:
        """Get strategy recommendation with reasoning."""
        best_strategy = self.get_best_strategy(problem_type)
        lessons = self.get_lessons_for_problem(problem_type)

        stats = self.strategy_stats.get(best_strategy, {})

        return {
            "recommended_strategy": best_strategy,
            "confidence": stats.get("successes", 0) / max(stats.get("attempts", 1), 1),
            "avg_coherence": stats.get("avg_coherence", 0.0),
            "avg_tokens": stats.get("avg_tokens", 0),
            "lessons": lessons,
            "similar_problems_solved": len(self.problem_clusters.get(problem_type, [])),
        }

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of all learning."""
        total = len(self.experiences)
        successes = sum(1 for e in self.experiences if e.success)

        return {
            "total_experiences": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "problem_types": len(self.problem_clusters),
            "strategies_evaluated": len(self.strategy_stats),
            "success_patterns": sum(len(v) for v in self.success_patterns.values()),
            "failure_patterns": sum(len(v) for v in self.failure_patterns.values()),
            "vault_path": str(self.vault_path),
        }

    def export_for_skill_refinement(self) -> str:
        """Export learning for skill refinement."""
        export_file = self.vault_path / "skill_refinement_export.json"

        export_data = {
            "summary": self.get_learning_summary(),
            "best_strategies": {
                ptype: self.get_best_strategy(ptype) for ptype in self.problem_clusters.keys()
            },
            "strategy_stats": dict(self.strategy_stats),
            "success_patterns": dict(self.success_patterns),
            "failure_patterns": dict(self.failure_patterns),
            "recommendations": [],
        }

        # Generate recommendations
        for problem_type in self.problem_clusters.keys():
            rec = self.get_strategy_recommendation(problem_type)
            export_data["recommendations"].append(
                {
                    "problem_type": problem_type,
                    **rec,
                }
            )

        with open(export_file, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported learning to: {export_file}")
        return str(export_file)


# Global learning engine instance
_global_learning_engine: Optional[ExperientialLearningEngine] = None


def get_learning_engine() -> ExperientialLearningEngine:
    """Get or create global learning engine instance."""
    global _global_learning_engine

    if _global_learning_engine is None:
        _global_learning_engine = ExperientialLearningEngine()

    return _global_learning_engine
