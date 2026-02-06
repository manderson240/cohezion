"""
ASCENDED COHEZION - Compound Evolution Engine
Recursive Self-Improvement via Cloud Feedback Integration

Applies cloud grading feedback to improve future universe simulations:
- Physics parameter tuning
- Algorithm optimization
- Resource allocation refinement
- Cross-track pattern transfer
- Knowledge Graph accumulation

Implements maximum compound engineering:
- Every run improves the next
- Patterns transfer between tracks
- Learnings accumulate in Knowledge Graph
- 20 runs → near-optimal system

Email: manderson240@gmail.com
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvolutionState:
    """State of the evolution system"""

    track_type: str
    run_count: int = 0
    average_grade: float = 0.0
    best_grade: str = "F"
    improvement_rate: float = 0.0
    applied_changes: list[dict] = field(default_factory=list)
    pattern_library: dict[str, Any] = field(default_factory=dict)
    hiho_convergence_avg: float = 0.0


@dataclass
class Improvement:
    """Single improvement action"""

    criterion: str
    action: str
    old_value: Any
    new_value: Any
    reason: str
    confidence: float
    applied: bool = False
    result_grade: str | None = None


class CompoundEvolutionEngine:
    """
    Compound Evolution Engine for ASCENDED COHEZION

    Core principle: Each feature built makes all future features easier.

    Manages:
    - Cloud feedback parsing and action extraction
    - Physics parameter optimization
    - Cross-track pattern transfer
    - Knowledge Graph accumulation
    - Next-run configuration generation
    """

    def __init__(self, knowledge_graph_path: str | None = None):
        """Initialize the evolution engine"""
        self.knowledge_graph_path = (
            knowledge_graph_path
            or "/home/mike-anderson/dev/cohezion/data/knowledge_graph"
        )
        self.evolution_state_dir = Path(
            "/home/mike-anderson/dev/cohezion/data/evolution"
        )
        self.evolution_state_dir.mkdir(parents=True, exist_ok=True)

        # Track evolution state per track
        self.track_states: dict[str, EvolutionState] = {}
        self._load_states()

        # Applied improvements history
        self.improvement_history: list[Improvement] = []

        # Pattern library for cross-track transfer
        self.pattern_library: dict[str, Any] = {}
        self._load_patterns()

        logger.info("🔄 CompoundEvolutionEngine initialized")
        logger.info(f"   Knowledge Graph: {self.knowledge_graph_path}")
        logger.info(f"   Tracks monitored: {list(self.track_states.keys())}")

    def _load_states(self):
        """Load evolution states from disk"""
        for state_file in self.evolution_state_dir.glob("*_state.json"):
            track_type = state_file.stem.replace("_state", "")
            try:
                data = json.loads(state_file.read_text())
                self.track_states[track_type] = EvolutionState(
                    track_type=track_type,
                    run_count=data.get("run_count", 0),
                    average_grade=data.get("average_grade", 0.0),
                    best_grade=data.get("best_grade", "F"),
                    improvement_rate=data.get("improvement_rate", 0.0),
                    applied_changes=data.get("applied_changes", []),
                    pattern_library=data.get("pattern_library", {}),
                    hiho_convergence_avg=data.get("hiho_convergence_avg", 0.0),
                )
            except Exception as e:
                logger.warning(f"Could not load state for {track_type}: {e}")

    def _save_state(self, track_type: str):
        """Save evolution state to disk"""
        if track_type not in self.track_states:
            return

        state = self.track_states[track_type]
        state_file = self.evolution_state_dir / f"{track_type}_state.json"

        state_data = {
            "track_type": state.track_type,
            "run_count": state.run_count,
            "average_grade": state.average_grade,
            "best_grade": state.best_grade,
            "improvement_rate": state.improvement_rate,
            "applied_changes": state.applied_changes,
            "pattern_library": state.pattern_library,
            "hiho_convergence_avg": state.hiho_convergence_avg,
            "last_updated": datetime.now().isoformat(),
        }

        state_file.write_text(json.dumps(state_data, indent=2))

    def _load_patterns(self):
        """Load successful patterns from Knowledge Graph"""
        patterns_file = Path(self.knowledge_graph_path) / "patterns.json"
        if patterns_file.exists():
            try:
                self.pattern_library = json.loads(patterns_file.read_text())
            except Exception as e:
                logger.warning(f"Could not load patterns: {e}")

    def _save_patterns(self):
        """Save patterns to Knowledge Graph"""
        patterns_file = Path(self.knowledge_graph_path) / "patterns.json"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        patterns_file.write_text(json.dumps(self.pattern_library, indent=2))

    async def apply_cloud_feedback(
        self,
        track_type: str,
        grade_report: dict[str, Any],
        mission_data: dict[str, Any],
    ) -> list[Improvement]:
        """
        Main entry point: Apply cloud grading feedback to improve system

        Returns list of improvements that were applied
        """
        logger.info(f"🔄 Applying cloud feedback for {track_type}")
        logger.info(f"   Grade: {grade_report.get('overall_grade', 'N/A')}")

        # Initialize track state if needed
        if track_type not in self.track_states:
            self.track_states[track_type] = EvolutionState(track_type=track_type)

        state = self.track_states[track_type]
        state.run_count += 1

        # Update grade tracking
        current_grade = grade_report.get("overall_score", 0)
        state.average_grade = (
            state.average_grade * (state.run_count - 1) + current_grade
        ) / state.run_count

        # Track best grade
        grade_order = {"F": 0, "D": 1, "C": 2, "C+": 3, "B": 4, "B+": 5, "A": 6}
        current_grade_letter = grade_report.get("overall_grade", "F")
        if grade_order.get(current_grade_letter, 0) > grade_order.get(
            state.best_grade, 0
        ):
            state.best_grade = current_grade_letter

        # Extract improvements from feedback
        improvements = self._extract_improvements(
            grade_report.get("feedback", ""),
            grade_report.get("improvement_suggestions", []),
            grade_report.get("criterion_scores", {}),
        )

        # Apply improvements
        applied = []
        for improvement in improvements:
            success = await self._apply_improvement(
                track_type, improvement, mission_data
            )
            if success:
                improvement.applied = True
                applied.append(improvement)
                state.applied_changes.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "criterion": improvement.criterion,
                        "action": improvement.action,
                        "confidence": improvement.confidence,
                    }
                )

        # Calculate improvement rate
        if len(state.applied_changes) > 1:
            recent_grades = [current_grade]  # Simplified - would track more history
            state.improvement_rate = self._calculate_improvement_rate(recent_grades)

        # Extract and store patterns
        patterns = self._extract_patterns(mission_data, grade_report)
        await self._store_patterns(track_type, patterns)

        # Cross-track pattern transfer
        await self._cross_pollinate(track_type, patterns)

        # Save state
        self._save_state(track_type)

        logger.info(f"✅ Applied {len(applied)} improvements for {track_type}")
        logger.info(f"   Total runs: {state.run_count}")
        logger.info(f"   Average grade: {state.average_grade:.1f}")
        logger.info(f"   Best grade: {state.best_grade}")

        return applied

    def _extract_improvements(
        self, feedback: str, suggestions: list[str], criterion_scores: dict[str, Any]
    ) -> list[Improvement]:
        """Extract actionable improvements from cloud feedback"""

        improvements = []

        # Process criterion scores to identify weak areas
        for criterion, data in criterion_scores.items():
            score = data.get("score", 0)

            if score < 70:  # Below C grade
                # Identify specific actions based on criterion
                if criterion == "physics_realism":
                    improvements.append(
                        Improvement(
                            criterion=criterion,
                            action="adjust_damping",
                            old_value=0.15,
                            new_value=0.15 * 1.1,  # Increase by 10%
                            reason=f"Low physics realism score ({score}), increase damping",
                            confidence=0.7,
                        )
                    )

                elif criterion == "hiho_stability":
                    improvements.append(
                        Improvement(
                            criterion=criterion,
                            action="tighten_hiho_range",
                            old_value=[0.45, 0.55],
                            new_value=[0.48, 0.52],
                            reason=f"HIHO convergence issues ({score}), tighten target range",
                            confidence=0.8,
                        )
                    )

                elif criterion == "visual_clarity":
                    improvements.append(
                        Improvement(
                            criterion=criterion,
                            action="simplify_visualization",
                            old_value="12D full projection",
                            new_value="3D primary + 9D compressed",
                            reason=f"Visual clarity low ({score}), simplify 12D projection",
                            confidence=0.75,
                        )
                    )

                elif criterion == "emergent_complexity":
                    improvements.append(
                        Improvement(
                            criterion=criterion,
                            action="increase_coupling",
                            old_value=0.6,
                            new_value=0.6 * 1.15,
                            reason=f"Low emergent complexity ({score}), increase particle coupling",
                            confidence=0.65,
                        )
                    )

                elif criterion == "efficiency":
                    improvements.append(
                        Improvement(
                            criterion=criterion,
                            action="reduce_particle_count",
                            old_value=100000,
                            new_value=80000,
                            reason=f"Efficiency low ({score}), reduce particle count by 20%",
                            confidence=0.6,
                        )
                    )

        # Process specific suggestions
        for suggestion in suggestions:
            improvement = self._parse_suggestion(suggestion)
            if improvement:
                improvements.append(improvement)

        # Sort by confidence (apply highest confidence first)
        improvements.sort(key=lambda x: x.confidence, reverse=True)

        return improvements[:5]  # Limit to top 5 improvements per run

    def _parse_suggestion(self, suggestion: str) -> Improvement | None:
        """Parse a text suggestion into an improvement action"""
        suggestion_lower = suggestion.lower()

        # Pattern matching for common suggestions
        if "damping" in suggestion_lower:
            return Improvement(
                criterion="physics_realism",
                action="adjust_damping_from_suggestion",
                old_value=0.15,
                new_value=0.165,
                reason=suggestion,
                confidence=0.7,
            )

        if "checkpoint" in suggestion_lower or "granularity" in suggestion_lower:
            return Improvement(
                criterion="narrative_quality",
                action="increase_checkpoints",
                old_value=4,
                new_value=8,
                reason=suggestion,
                confidence=0.65,
            )

        if "simplify" in suggestion_lower or "clutter" in suggestion_lower:
            return Improvement(
                criterion="visual_clarity",
                action="simplify_dashboard",
                old_value="complex",
                new_value="simplified",
                reason=suggestion,
                confidence=0.75,
            )

        if "coupling" in suggestion_lower:
            return Improvement(
                criterion="emergent_complexity",
                action="adjust_coupling",
                old_value=0.6,
                new_value=0.69,
                reason=suggestion,
                confidence=0.7,
            )

        return None

    async def _apply_improvement(
        self, track_type: str, improvement: Improvement, mission_data: dict
    ) -> bool:
        """Apply a single improvement to the system"""

        logger.info(f"Applying improvement: {improvement.action}")
        logger.info(f"   Criterion: {improvement.criterion}")
        logger.info(f"   Confidence: {improvement.confidence}")

        # Update mission configuration
        config_updated = await self._update_track_config(track_type, improvement)

        # Log to improvement history
        self.improvement_history.append(improvement)

        return config_updated

    async def _update_track_config(
        self, track_type: str, improvement: Improvement
    ) -> bool:
        """Update track configuration based on improvement"""

        config_file = self.evolution_state_dir / f"{track_type}_config.json"

        # Load or create config
        if config_file.exists():
            config = json.loads(config_file.read_text())
        else:
            config = self._get_default_config(track_type)

        # Apply improvement
        if (
            improvement.action == "adjust_damping"
            or improvement.action == "adjust_damping_from_suggestion"
        ):
            for universe in config.get("universes", []):
                universe["physics_laws"]["damping"] = improvement.new_value

        elif improvement.action == "tighten_hiho_range":
            config["hiho_target_range"] = improvement.new_value

        elif improvement.action == "simplify_visualization":
            config["visualization_mode"] = "simplified_3d"

        elif improvement.action == "increase_coupling":
            for universe in config.get("universes", []):
                universe["physics_laws"]["coupling"] = improvement.new_value

        elif improvement.action == "reduce_particle_count":
            for universe in config.get("universes", []):
                universe["particle_count"] = int(improvement.new_value)

        elif improvement.action == "increase_checkpoints":
            config["checkpoint_frequency"] = improvement.new_value

        # Save updated config
        config["last_updated"] = datetime.now().isoformat()
        config["evolution_version"] = config.get("evolution_version", 0) + 1

        config_file.write_text(json.dumps(config, indent=2))

        return True

    def _get_default_config(self, track_type: str) -> dict:
        """Get default configuration for a track"""

        defaults = {
            "rapid": {
                "universes": [
                    {
                        "name": f"rapid_{i}",
                        "physics_laws": {
                            "damping": 0.1,
                            "coupling": 0.5,
                            "entropy_rate": 0.01,
                        },
                        "particle_count": 10000,
                        "epochs": 20,
                    }
                    for i in range(6)
                ],
                "hiho_target_range": [0.45, 0.55],
                "checkpoint_frequency": 4,
                "visualization_mode": "full_12d",
            },
            "balanced": {
                "universes": [
                    {
                        "name": f"balanced_{i}",
                        "physics_laws": {
                            "damping": 0.15,
                            "coupling": 0.6,
                            "entropy_rate": 0.005,
                        },
                        "particle_count": 100000,
                        "epochs": 20,
                    }
                    for i in range(3)
                ],
                "hiho_target_range": [0.45, 0.55],
                "checkpoint_frequency": 4,
                "visualization_mode": "full_12d",
            },
            "deep": {
                "universes": [
                    {
                        "name": "deep_cosmos",
                        "physics_laws": {
                            "damping": 0.2,
                            "coupling": 0.7,
                            "entropy_rate": 0.002,
                        },
                        "particle_count": 1000000,
                        "epochs": 24,
                    }
                ],
                "hiho_target_range": [0.45, 0.55],
                "checkpoint_frequency": 6,
                "visualization_mode": "full_12d",
            },
        }

        return defaults.get(track_type, {})

    def _extract_patterns(self, mission_data: dict, grade_report: dict) -> list[dict]:
        """Extract successful patterns from mission"""

        patterns = []

        # Extract physics parameters that led to good grades
        if grade_report.get("overall_score", 0) > 80:
            for universe in mission_data.get("universes", []):
                pattern = {
                    "type": "physics_success",
                    "universe_type": universe.get("type", "unknown"),
                    "damping": universe.get("physics_laws", {}).get("damping"),
                    "coupling": universe.get("physics_laws", {}).get("coupling"),
                    "grade": grade_report.get("overall_grade"),
                    "score": grade_report.get("overall_score"),
                    "timestamp": datetime.now().isoformat(),
                }
                patterns.append(pattern)

        # Extract HIHO convergence patterns
        convergence_epoch = mission_data.get("coherence_metrics", {}).get(
            "convergence_epoch"
        )
        if convergence_epoch and convergence_epoch < 10:
            patterns.append(
                {
                    "type": "fast_convergence",
                    "convergence_epoch": convergence_epoch,
                    "track_type": mission_data.get("track_type"),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return patterns

    async def _store_patterns(self, track_type: str, patterns: list[dict]):
        """Store patterns in library and Knowledge Graph"""

        # Update track's pattern library
        if track_type not in self.pattern_library:
            self.pattern_library[track_type] = []

        self.pattern_library[track_type].extend(patterns)

        # Keep only recent patterns (last 50)
        self.pattern_library[track_type] = self.pattern_library[track_type][-50:]

        # Save to disk
        self._save_patterns()

        logger.info(f"Stored {len(patterns)} patterns for {track_type}")

    async def _cross_pollinate(self, source_track: str, patterns: list[dict]):
        """Transfer successful patterns between tracks"""

        # Define transfer rules
        transfer_map = {
            "rapid": ["balanced"],  # Fast discoveries go to balanced
            "balanced": ["deep", "rapid"],  # Balanced insights transfer both ways
            "deep": ["balanced"],  # Deep insights improve balanced
        }

        targets = transfer_map.get(source_track, [])

        for target_track in targets:
            if target_track not in self.track_states:
                continue

            # Transfer high-quality patterns
            for pattern in patterns:
                if pattern.get("score", 0) > 85:  # Only excellent patterns
                    await self._apply_pattern_to_track(pattern, target_track)
                    logger.info(
                        f"Cross-pollinated pattern from {source_track} to {target_track}"
                    )

    async def _apply_pattern_to_track(self, pattern: dict, target_track: str):
        """Apply a pattern from another track"""

        config_file = self.evolution_state_dir / f"{target_track}_config.json"

        if not config_file.exists():
            return

        config = json.loads(config_file.read_text())

        # Apply physics pattern if applicable
        if pattern.get("type") == "physics_success":
            for universe in config.get("universes", []):
                if universe.get("type") == pattern.get("universe_type"):
                    # Gradually adopt successful parameters
                    old_damping = universe["physics_laws"]["damping"]
                    new_damping = (old_damping + pattern["damping"]) / 2
                    universe["physics_laws"]["damping"] = new_damping

        config["cross_pollinated_from"] = pattern.get("source_track", "unknown")
        config["last_updated"] = datetime.now().isoformat()

        config_file.write_text(json.dumps(config, indent=2))

    def _calculate_improvement_rate(self, recent_grades: list[float]) -> float:
        """Calculate rate of improvement over recent runs"""

        if len(recent_grades) < 2:
            return 0.0

        # Simple linear trend
        x = list(range(len(recent_grades)))
        y = recent_grades

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi**2 for xi in x)

        slope = (
            (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
            if (n * sum_x2 - sum_x**2) != 0
            else 0
        )

        return slope

    async def generate_next_run_config(self, track_type: str) -> dict:
        """Generate optimized configuration for next run"""

        config_file = self.evolution_state_dir / f"{track_type}_config.json"

        if config_file.exists():
            config = json.loads(config_file.read_text())
        else:
            config = self._get_default_config(track_type)

        # Add evolution metadata
        state = self.track_states.get(track_type, EvolutionState(track_type=track_type))

        config["evolution_metadata"] = {
            "run_number": state.run_count + 1,
            "target_grade": self._calculate_target_grade(state),
            "improvement_focus": self._identify_focus_area(state),
            "cross_pollinated_patterns": len(self.pattern_library.get(track_type, [])),
            "generated_at": datetime.now().isoformat(),
        }

        return config

    def _calculate_target_grade(self, state: EvolutionState) -> str:
        """Calculate target grade for next run"""

        grade_order = {"F": 0, "D": 1, "C": 2, "C+": 3, "B": 4, "B+": 5, "A": 6}
        current = grade_order.get(state.best_grade, 0)

        # Aim for one grade higher than best
        target = min(current + 1, 6)

        # Map back to letter
        for letter, score in grade_order.items():
            if score == target:
                return letter

        return "A"

    def _identify_focus_area(self, state: EvolutionState) -> str:
        """Identify which area needs most improvement"""

        # Default focus areas
        areas = [
            "physics_realism",
            "hiho_stability",
            "visual_clarity",
            "emergent_complexity",
        ]

        # In real implementation, would analyze which criterion is weakest
        # For now, rotate focus
        return areas[state.run_count % len(areas)]

    def get_evolution_summary(self) -> dict[str, Any]:
        """Get summary of evolution across all tracks"""

        return {
            "tracks": {
                track: {
                    "runs": state.run_count,
                    "average_grade": state.average_grade,
                    "best_grade": state.best_grade,
                    "improvement_rate": state.improvement_rate,
                    "patterns_stored": len(state.pattern_library),
                }
                for track, state in self.track_states.items()
            },
            "total_improvements": len(self.improvement_history),
            "total_patterns": sum(
                len(patterns) for patterns in self.pattern_library.values()
            ),
            "last_updated": datetime.now().isoformat(),
        }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        engine = CompoundEvolutionEngine()

        # Simulate cloud feedback
        grade_report = {
            "overall_grade": "B+",
            "overall_score": 85,
            "criterion_scores": {
                "physics_realism": {"score": 82},
                "hiho_stability": {"score": 88},
                "visual_clarity": {"score": 80},
                "emergent_complexity": {"score": 87},
                "efficiency": {"score": 83},
                "narrative_quality": {"score": 86},
            },
            "feedback": "Good emergent behavior with consistent physics",
            "improvement_suggestions": [
                "Increase damping by 10% for faster convergence",
                "Simplify 12D projection for clarity",
            ],
            "confidence": 0.92,
        }

        mission_data = {
            "track_type": "balanced",
            "universes": [
                {
                    "name": "balanced_0",
                    "type": "Entropy Garden",
                    "physics_laws": {"damping": 0.15, "coupling": 0.6},
                },
                {
                    "name": "balanced_1",
                    "type": "Memory Ocean",
                    "physics_laws": {"damping": 0.15, "coupling": 0.6},
                },
                {
                    "name": "balanced_2",
                    "type": "Symbiotic Lattice",
                    "physics_laws": {"damping": 0.15, "coupling": 0.6},
                },
            ],
            "epochs_completed": 20,
            "coherence_metrics": {"convergence_epoch": 7, "average": 0.498},
        }

        # Apply feedback
        improvements = await engine.apply_cloud_feedback(
            "balanced", grade_report, mission_data
        )

        print(f"\nApplied {len(improvements)} improvements")
        for imp in improvements:
            print(f"  - {imp.criterion}: {imp.action} (confidence: {imp.confidence})")

        # Get next run config
        next_config = await engine.generate_next_run_config("balanced")
        print(
            f"\nNext run config generated (run #{next_config['evolution_metadata']['run_number']})"
        )
        print(f"  Target grade: {next_config['evolution_metadata']['target_grade']}")

        # Get evolution summary
        summary = engine.get_evolution_summary()
        print(f"\nEvolution Summary: {summary}")

    asyncio.run(main())
