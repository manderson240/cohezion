"""Unified capability matrix for models, skills, and agents.

Reads from existing tracking systems (ModelQualityClassifier, SkillHealthTracker,
CapabilityRegistry, SmartRouter, CostAwareRouter) to provide a single query
interface for capability assessment, gap analysis, and task recommendation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class CapabilityEntry:
    """Assessment record for a model, skill, or agent."""

    entity_type: str  # "model" | "skill" | "agent"
    entity_id: str
    capabilities: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    speed_tier: int = 3
    success_rate: float = 0.0
    affinity: dict[str, float] = field(default_factory=dict)
    last_assessed: str = ""
    source: str = "static"  # "static" | "benchmark" | "execution-history"
    metadata: dict = field(default_factory=dict)


@dataclass
class CapabilityGap:
    """A missing or weak capability identified by gap analysis."""

    task_type: str
    required_capability: str
    best_available_score: float
    threshold: float
    suggested_action: str  # "scout" | "finetune" | "onboard"
    training_data_count: int = 0


@dataclass
class FinetuneCandidate:
    """A fine-tuning opportunity with ROI estimate."""

    base_model: str
    target_capability: str
    training_data_count: int
    finetune_mode: str  # "soft" | "qlora" | "call"
    estimated_quality_gain: float
    memory_required_gb: float
    feasible: bool


class CapabilityMatrix:
    """Unified assessment registry across models, skills, and agents.

    Reads from existing Cohezion tracking systems without replacing them.
    Provides a unified query layer for capability assessment, task
    recommendation, and gap analysis.
    """

    # Capability dimensions used for affinity scoring
    TASK_TYPES = [
        "coding",
        "reasoning",
        "analysis",
        "creative",
        "tool-calling",
        "long-context",
        "multilingual",
        "research",
    ]

    def __init__(self) -> None:
        self._entries: dict[str, CapabilityEntry] = {}
        self._load_static_models()
        self._load_static_skills()
        self._load_static_agents()

    def _load_static_models(self) -> None:
        """Load model capabilities from SmartRouter and CostAwareRouter."""
        try:
            from cohezion.swarm.cost_aware_router import CostAwareRouter
            from cohezion.swarm.smart_router import LOCAL_MODELS, ModelCapability

            cap_map = {
                ModelCapability.FAST: "fast",
                ModelCapability.ACCURATE: "reasoning",
                ModelCapability.CREATIVE: "creative",
                ModelCapability.LARGE_CONTEXT: "long-context",
                ModelCapability.CODING: "coding",
            }

            for model_id, profile in LOCAL_MODELS.items():
                caps = [cap_map.get(c, str(c)) for c in profile.capabilities]
                quality = CostAwareRouter.MODEL_QUALITY.get(model_id, profile.quality_tier / 5.0)

                affinity: dict[str, float] = {}
                for cap in caps:
                    if cap == "coding":
                        affinity["coding"] = 0.9
                    elif cap == "reasoning":
                        affinity["reasoning"] = 0.8
                        affinity["analysis"] = 0.7
                    elif cap == "creative":
                        affinity["creative"] = 0.8
                    elif cap == "long-context":
                        affinity["long-context"] = 0.9
                        affinity["research"] = 0.6

                entry = CapabilityEntry(
                    entity_type="model",
                    entity_id=model_id,
                    capabilities=caps,
                    quality_score=quality,
                    speed_tier=profile.speed_tier,
                    success_rate=0.0,
                    affinity=affinity,
                    last_assessed=date.today().isoformat(),
                    source="static",
                    metadata={
                        "context_length": profile.context_length,
                        "tps": CostAwareRouter.MODEL_TPS.get(model_id, 0.0),
                        "latency_ms": CostAwareRouter.MODEL_LATENCY.get(model_id, 0.0),
                    },
                )
                self._entries[f"model:{model_id}"] = entry

        except ImportError:
            logger.debug("SmartRouter/CostAwareRouter not available")

    def _load_static_skills(self) -> None:
        """Load skill data from SkillHealthTracker."""
        try:
            from cohezion.compound.skill_health_tracker import SkillHealthTracker

            tracker = SkillHealthTracker()
            for name, record in tracker._records.items():
                entry = CapabilityEntry(
                    entity_type="skill",
                    entity_id=name,
                    capabilities=["skill"],
                    quality_score=record.avg_quality_score,
                    speed_tier=2,
                    success_rate=record.success_rate,
                    affinity={},
                    last_assessed=record.last_used or date.today().isoformat(),
                    source="execution-history" if record.total_invocations > 0 else "static",
                    metadata={
                        "invocations": record.total_invocations,
                        "health_score": record.health_score,
                        "avg_tokens": record.avg_tokens_per_use,
                    },
                )
                self._entries[f"skill:{name}"] = entry

        except Exception:
            logger.debug("SkillHealthTracker not available")

    def _load_static_agents(self) -> None:
        """Load agent metadata from .claude/agents/ directory."""
        agents_dir = Path(".claude/agents")
        if not agents_dir.is_dir():
            return

        for agent_file in agents_dir.glob("*.md"):
            name = agent_file.stem
            content = agent_file.read_text(encoding="utf-8")

            # Extract capabilities from content keywords
            caps: list[str] = []
            lower = content.lower()
            if "security" in lower:
                caps.append("security")
            if "code" in lower or "review" in lower:
                caps.append("coding")
            if "test" in lower:
                caps.append("testing")
            if "research" in lower:
                caps.append("research")
            if "refin" in lower or "skill" in lower:
                caps.append("skill-management")

            # Extract model from frontmatter
            model = "unknown"
            if "model:" in content:
                for line in content.splitlines():
                    if line.strip().startswith("model:"):
                        model = line.split(":", 1)[1].strip()
                        break

            entry = CapabilityEntry(
                entity_type="agent",
                entity_id=name,
                capabilities=caps or ["general"],
                quality_score=0.0,
                speed_tier=3,
                success_rate=0.0,
                affinity={},
                last_assessed=date.today().isoformat(),
                source="static",
                metadata={"model": model, "file": str(agent_file)},
            )
            self._entries[f"agent:{name}"] = entry

    def enrich_from_execution_history(self) -> int:
        """Update entries with runtime data from ModelQualityClassifier."""
        updated = 0
        try:
            from cohezion.compound.model_quality_classifier import ModelQualityClassifier

            mqc = ModelQualityClassifier()
            for model_id, predictor in mqc._predictors.items():
                key = f"model:{model_id}"
                if key in self._entries and predictor.coherence_history:
                    entry = self._entries[key]
                    entry.quality_score = sum(predictor.coherence_history) / len(
                        predictor.coherence_history
                    )
                    entry.success_rate = (
                        sum(predictor.success_history) / len(predictor.success_history)
                        if predictor.success_history
                        else 0.0
                    )
                    entry.source = "execution-history"
                    entry.last_assessed = date.today().isoformat()
                    updated += 1
        except Exception:
            pass
        return updated

    def assess_model(self, model_id: str) -> CapabilityEntry | None:
        """Get or create assessment for a specific model."""
        key = f"model:{model_id}"
        return self._entries.get(key)

    def assess_skill(self, skill_name: str) -> CapabilityEntry | None:
        """Get or create assessment for a specific skill."""
        key = f"skill:{skill_name}"
        return self._entries.get(key)

    def assess_agent(self, agent_name: str) -> CapabilityEntry | None:
        """Get assessment for a specific agent."""
        key = f"agent:{agent_name}"
        return self._entries.get(key)

    def get_matrix(self) -> dict[str, list[CapabilityEntry]]:
        """Get all entries grouped by entity type."""
        result: dict[str, list[CapabilityEntry]] = {"model": [], "skill": [], "agent": []}
        for entry in self._entries.values():
            result.setdefault(entry.entity_type, []).append(entry)
        return result

    def recommend_for_task(
        self,
        task_type: str,
        constraints: dict | None = None,
    ) -> list[CapabilityEntry]:
        """Recommend entities for a task type, sorted by affinity score."""
        constraints = constraints or {}
        max_latency = constraints.get("max_latency_ms", float("inf"))
        min_quality = constraints.get("min_quality", 0.0)
        entity_types = constraints.get("entity_types", ["model"])

        candidates = []
        for entry in self._entries.values():
            if entry.entity_type not in entity_types:
                continue
            if entry.quality_score < min_quality:
                continue
            latency = entry.metadata.get("latency_ms", 0.0)
            if latency > max_latency:
                continue
            affinity = entry.affinity.get(task_type, 0.0)
            candidates.append((affinity + entry.quality_score, entry))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in candidates]

    def run_gap_analysis(self) -> list[CapabilityGap]:
        """Identify capability gaps across all task types."""
        gaps: list[CapabilityGap] = []
        threshold = 0.7

        for task_type in self.TASK_TYPES:
            best_score = 0.0
            for entry in self._entries.values():
                if entry.entity_type == "model":
                    score = entry.affinity.get(task_type, 0.0)
                    best_score = max(best_score, score)

            if best_score < threshold:
                gap = CapabilityGap(
                    task_type=task_type,
                    required_capability=task_type,
                    best_available_score=best_score,
                    threshold=threshold,
                    suggested_action="scout" if best_score < 0.3 else "finetune",
                )
                gaps.append(gap)

        return gaps

    def suggest_finetune_targets(self) -> list[FinetuneCandidate]:
        """Cross-reference gaps with available data and hardware to suggest fine-tuning."""
        gaps = self.run_gap_analysis()
        candidates: list[FinetuneCandidate] = []

        # Estimate training data availability (simple heuristic)
        training_data_path = Path("data/training")
        data_count = 0
        if training_data_path.exists():
            for f in training_data_path.glob("*.jsonl"):
                try:
                    data_count += sum(1 for _ in f.open())
                except Exception:
                    pass

        for gap in gaps:
            if gap.suggested_action != "finetune":
                continue

            # Find best base model to fine-tune
            models = self.recommend_for_task(gap.task_type)
            if not models:
                continue

            base = models[0]
            size_gb = base.metadata.get("size_gb", 5.0)
            memory_needed = size_gb * 3  # 3x for gradients + optimizer

            if data_count < 50:
                mode = "soft"
            elif data_count < 500:
                mode = "qlora"
            else:
                mode = "call"

            candidates.append(
                FinetuneCandidate(
                    base_model=base.entity_id,
                    target_capability=gap.task_type,
                    training_data_count=data_count,
                    finetune_mode=mode,
                    estimated_quality_gain=0.1 if mode == "soft" else 0.2,
                    memory_required_gb=memory_needed,
                    feasible=memory_needed < 100,  # 128GB system, keep 28GB headroom
                )
            )

        return candidates

    def update_from_execution(self, entity_id: str, execution_result: dict) -> None:
        """Update an entity's scores based on a new execution result."""
        for key, entry in self._entries.items():
            if entry.entity_id == entity_id:
                coherence = execution_result.get("coherence", entry.quality_score)
                success = execution_result.get("success", True)

                # Exponential moving average for quality
                entry.quality_score = 0.8 * entry.quality_score + 0.2 * coherence
                # Running success rate
                total = entry.metadata.get("invocations", 0) + 1
                old_successes = entry.success_rate * entry.metadata.get("invocations", 0)
                entry.success_rate = (old_successes + (1.0 if success else 0.0)) / total
                entry.metadata["invocations"] = total
                entry.source = "execution-history"
                entry.last_assessed = date.today().isoformat()
                break

    def export_report(self) -> str:
        """Generate a markdown report of the full capability matrix."""
        lines = ["# Capability Matrix Report", ""]

        matrix = self.get_matrix()
        for entity_type in ["model", "skill", "agent"]:
            entries = sorted(
                matrix.get(entity_type, []), key=lambda e: e.quality_score, reverse=True
            )
            if not entries:
                continue

            lines.append(f"## {entity_type.title()}s ({len(entries)})")
            lines.append("")
            lines.append("| ID | Quality | Speed | Success | Capabilities | Source |")
            lines.append("|---|---|---|---|---|---|")

            for e in entries:
                caps = ", ".join(e.capabilities[:4])
                lines.append(
                    f"| {e.entity_id} | {e.quality_score:.2f} | {e.speed_tier} | "
                    f"{e.success_rate:.0%} | {caps} | {e.source} |"
                )
            lines.append("")

        # Gap analysis
        gaps = self.run_gap_analysis()
        if gaps:
            lines.append("## Capability Gaps")
            lines.append("")
            lines.append("| Task Type | Best Score | Threshold | Action |")
            lines.append("|---|---|---|---|")
            for g in gaps:
                lines.append(
                    f"| {g.task_type} | {g.best_available_score:.2f} | {g.threshold:.2f} | {g.suggested_action} |"
                )
            lines.append("")

        # Fine-tune suggestions
        ft = self.suggest_finetune_targets()
        if ft:
            lines.append("## Fine-Tuning Opportunities")
            lines.append("")
            lines.append("| Base Model | Target | Data | Mode | Gain | Feasible |")
            lines.append("|---|---|---|---|---|---|")
            for c in ft:
                lines.append(
                    f"| {c.base_model} | {c.target_capability} | {c.training_data_count} | "
                    f"{c.finetune_mode} | +{c.estimated_quality_gain:.1f} | {'Yes' if c.feasible else 'No'} |"
                )
            lines.append("")

        return "\n".join(lines)

    def enrich_from_evo_scorecard(self, capability_vector: dict[str, float]) -> None:
        """Update matrix with EVO 6-axis capability metrics from eval/.

        Connects eval/capability_scorecard.py to the unified assessment layer.

        Args:
            capability_vector: Dict with 6 EVO axes (0.0 to 1.0):
                coherence_amplitude, phase_locking, exotic_charge_lifetime,
                orbit_quality, triune_balance, recovery_basin_radius
        """
        try:
            from cohezion.eval.capability_scorecard import AXES, CapabilityScorecard

            scorecard = CapabilityScorecard()
            if not scorecard._validate_vector(capability_vector):
                logger.debug("Invalid EVO capability vector, skipping enrichment")
                return

            # Map EVO axes to affinity scores
            affinity: dict[str, float] = {}
            for axis in AXES:
                value = capability_vector.get(axis, 0.0)
                if axis == "coherence_amplitude":
                    affinity["reasoning"] = value
                elif axis == "phase_locking":
                    affinity["analysis"] = value
                elif axis == "orbit_quality":
                    affinity["coding"] = value
                elif axis == "triune_balance":
                    affinity["creative"] = value
                elif axis == "recovery_basin_radius":
                    affinity["research"] = value

            overall_quality = sum(capability_vector.get(a, 0.0) for a in AXES) / len(AXES)

            entry = CapabilityEntry(
                entity_type="model",
                entity_id="evo_aggregate",
                capabilities=["evo-scorecard"],
                quality_score=overall_quality,
                speed_tier=2,
                success_rate=capability_vector.get("coherence_amplitude", 0.0),
                affinity=affinity,
                last_assessed=date.today().isoformat(),
                source="benchmark",
                metadata={"evo_vector": capability_vector},
            )
            self._entries["model:evo_aggregate"] = entry
            logger.debug("EVO scorecard enrichment applied: quality=%.3f", overall_quality)

        except ImportError:
            logger.debug("eval.capability_scorecard not available")
        except Exception:
            logger.debug("EVO scorecard enrichment failed (non-blocking)", exc_info=True)

    def run_self_evaluation(
        self, plan: str, prd_context: str = ""
    ) -> dict[str, float | bool | str]:
        """Run pre-flight self-evaluation via evaluation/self_eval.

        Connects evaluation/self_eval.py as a quality gate.

        Args:
            plan: Execution plan text to evaluate
            prd_context: Optional PRD context for alignment check

        Returns:
            Dict with score, passed, and feedback
        """
        try:
            from cohezion.evaluation.self_eval import SelfEvaluationEngine

            engine = SelfEvaluationEngine()
            result = engine.evaluate_execution_plan(plan, prd_context)
            return {
                "score": result.score,
                "passed": result.passed,
                "feedback": result.feedback,
            }
        except ImportError:
            logger.debug("evaluation.self_eval not available")
            return {"score": 0.0, "passed": True, "feedback": "Self-eval unavailable"}
        except Exception:
            logger.debug("Self-evaluation failed (non-blocking)", exc_info=True)
            return {"score": 0.0, "passed": True, "feedback": "Self-eval error"}

    def enrich_from_data_mesh(self) -> int:
        """Load data product metadata from data_mesh/ into capability entries.

        Connects data_mesh/data_product.py to the unified assessment layer.
        Each active data product becomes a capability entry representing
        a data domain the system can access.

        Returns:
            Number of data products loaded
        """
        loaded = 0
        try:
            from cohezion.data_mesh.data_product import get_cohezion_data_products

            products = get_cohezion_data_products()
            for product in products:
                if product.status.value != "active":
                    continue
                entry = CapabilityEntry(
                    entity_type="data_product",
                    entity_id=product.name,
                    capabilities=["data-access", product.domain],
                    quality_score={"gold": 1.0, "silver": 0.7, "bronze": 0.4}.get(
                        product.quality_tier.value, 0.5
                    ),
                    speed_tier=2,
                    success_rate=1.0,
                    affinity={product.domain: 0.9},
                    last_assessed=date.today().isoformat(),
                    source="data-mesh",
                    metadata={
                        "owner": product.owner,
                        "quality_tier": product.quality_tier.value,
                    },
                )
                self._entries[f"data_product:{product.name}"] = entry
                loaded += 1
        except (ImportError, Exception):
            logger.debug("Data mesh not available (non-blocking)", exc_info=True)
        return loaded
