#!/usr/bin/env python3
"""
COHEZION Performance DNA: Permanent Knowledge Capture System
Captures optimization patterns, successful workflows, and model intelligence
for continuous framework evolution and competitive advantage preservation.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SuccessPattern:
    """Represents a successful optimization pattern"""

    pattern_id: str
    innovation_type: str  # MoE, OCR, Memory-Aware, etc.
    model_config: dict[str, Any]
    performance_metrics: dict[str, float]
    success_factors: list[str]
    failure_points: list[str]
    timestamp: str
    repeatability_score: float  # 0-1, how easily this can be replicated


@dataclass
class ModelDNA:
    """Performance signature and characteristics of a model"""

    model_name: str
    role: str  # elite, core, specialized, legacy
    capabilities: list[str]
    benchmarks: dict[str, float]
    optimization_profile: dict[str, Any]
    best_use_cases: list[str]
    limitations: list[str]
    memory_signature: dict[str, float]  # GB per task type
    token_efficiency: float | None
    last_updated: str


@dataclass
class WorkflowGenome:
    """DNA of successful compound engineering workflows"""

    workflow_id: str
    models_required: list[str]
    steps: list[dict[str, Any]]
    success_rate: float
    token_efficiency: float
    optimization_gains: dict[str, float]
    resource_requirements: dict[str, float]
    scaling_factors: list[str]
    last_executed: str


class COHEZIONPerformanceDNA:
    """Captures and preserves COHEZION's performance innovations"""

    def __init__(self):
        self.dna_file = Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/data/performance_dna.json"
        )
        self.patterns_file = Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/data/success_patterns.json"
        )
        self.models_file = Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/data/model_dna.json"
        )
        self.workflows_file = Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/data/workflow_genome.json"
        )

        # Ensure data directory exists
        self.dna_file.parent.mkdir(parents=True, exist_ok=True)

        self.success_patterns: dict[str, SuccessPattern] = {}
        self.model_dna: dict[str, ModelDNA] = {}
        self.workflow_genome: dict[str, WorkflowGenome] = {}

        self.load_existing_dna()

    def load_existing_dna(self):
        """Load previously captured performance DNA"""
        try:
            if self.dna_file.exists():
                with open(self.dna_file) as f:
                    dna_data = json.load(f)
                    self.success_patterns = {
                        pid: SuccessPattern(**data)
                        for pid, data in dna_data.get("success_patterns", {}).items()
                    }
                    self.model_dna = {
                        mid: ModelDNA(**data)
                        for mid, data in dna_data.get("model_dna", {}).items()
                    }
                    self.workflow_genome = {
                        wid: WorkflowGenome(**data)
                        for wid, data in dna_data.get("workflow_genome", {}).items()
                    }
                logger.info(
                    f"🧬 Loaded {len(self.success_patterns)} patterns, {len(self.model_dna)} models, {len(self.workflow_genome)} workflows"
                )
        except Exception as e:
            logger.warning(f"⚠️ Failed to load existing DNA: {e}")

    def capture_success_pattern(
        self,
        task_type: str,
        model_config: dict[str, Any],
        outcome: dict[str, Any],
        innovation_type: str,
    ) -> str:
        """Capture a successful optimization pattern for future reuse"""

        pattern_id = (
            f"{task_type}_{innovation_type}_{datetime.now().strftime('%Y%m%d')}"
        )

        # Extract performance metrics
        performance_metrics = {
            "tokens_per_second": outcome.get("tokens_per_second", 0.0),
            "memory_efficiency": outcome.get("memory_efficiency", 0.0),
            "accuracy_improvement": outcome.get("accuracy_improvement", 0.0),
            "latency_reduction": outcome.get("latency_reduction", 0.0),
        }

        # Determine success factors (what made it work)
        success_factors = []
        if innovation_type == "moe_optimization":
            success_factors = ["3B_active_params", "96.25_efficiency", "elite_routing"]
        elif innovation_type == "ocr_optimization":
            success_factors = [
                "90.5_memory_savings",
                "94.62_accuracy",
                "specialized_over_general",
            ]
        elif innovation_type == "memory_aware_routing":
            success_factors = [
                "90_55_20gb_thresholds",
                "graceful_degradation",
                "intelligent_allocation",
            ]
        elif innovation_type == "compound_engineering":
            success_factors = [
                "multi_model_orchestration",
                "token_synergy",
                "workflow_templates",
            ]

        # Determine repeatability (how easy to replicate)
        repeatability_score = self._calculate_repeatability(
            model_config, innovation_type
        )

        pattern = SuccessPattern(
            pattern_id=pattern_id,
            innovation_type=innovation_type,
            model_config=model_config,
            performance_metrics=performance_metrics,
            success_factors=success_factors,
            failure_points=[],  # Would be populated by failures
            timestamp=datetime.now().isoformat(),
            repeatability_score=repeatability_score,
        )

        self.success_patterns[pattern_id] = pattern
        self._save_pattern(pattern)

        logger.info(f"🧬 Captured success pattern: {pattern_id}")
        return pattern_id

    def capture_model_dna(self, model_name: str, model_info: dict[str, Any]) -> str:
        """Capture model performance signature and characteristics"""

        dna_id = f"model_{model_name.replace(':', '_').replace('-', '_')}"

        model_dna = ModelDNA(
            model_name=model_name,
            role=model_info.get("role", "unknown"),
            capabilities=model_info.get("capabilities", []),
            benchmarks=model_info.get("benchmarks", {}),
            optimization_profile=model_info.get("optimization_profile", {}),
            best_use_cases=model_info.get("best_use_cases", []),
            limitations=model_info.get("limitations", []),
            memory_signature=model_info.get("memory_signature", {}),
            token_efficiency=model_info.get("token_efficiency"),
            last_updated=datetime.now().isoformat(),
        )

        self.model_dna[dna_id] = model_dna
        self._save_model_dna(model_dna)

        logger.info(f"🧬 Captured model DNA: {dna_id}")
        return dna_id

    def capture_workflow_genome(
        self, workflow_id: str, models_used: list[str], workflow_data: dict[str, Any]
    ) -> str:
        """Capture successful workflow pattern for future template generation"""

        genome_id = f"workflow_{workflow_id}_{datetime.now().strftime('%Y%m%d')}"

        workflow_genome = WorkflowGenome(
            workflow_id=workflow_id,
            models_required=models_used,
            steps=workflow_data.get("steps", []),
            success_rate=workflow_data.get("success_rate", 1.0),
            token_efficiency=workflow_data.get("token_efficiency", 0.0),
            optimization_gains=workflow_data.get("optimization_gains", {}),
            resource_requirements=workflow_data.get("resource_requirements", {}),
            scaling_factors=workflow_data.get("scaling_factors", []),
            last_executed=datetime.now().isoformat(),
        )

        self.workflow_genome[genome_id] = workflow_genome
        self._save_workflow_genome(workflow_genome)

        logger.info(f"🧬 Captured workflow genome: {genome_id}")
        return genome_id

    def _calculate_repeatability(
        self, model_config: dict[str, Any], innovation_type: str
    ) -> float:
        """Calculate how easy a pattern is to replicate (0-1 scale)"""
        base_score = 0.8  # Start with decent repeatability

        # Factors that increase repeatability
        if "docker" in model_config.get("deployment", []) or "ollama" in str(
            model_config
        ):
            base_score += 0.1  # Containerized deployment

        if "automatic" in model_config.get("routing", []):
            base_score += 0.05  # Automated routing

        if innovation_type in ["moe_optimization", "ocr_optimization"]:
            base_score += 0.1  # Well-documented optimizations

        return min(base_score, 1.0)

    def get_best_pattern_for_task(
        self, task_type: str, constraints: dict[str, Any]
    ) -> SuccessPattern | None:
        """Get best historical pattern for a given task type"""
        task_patterns = [
            p
            for p in self.success_patterns.values()
            if task_type in p.pattern_id.lower()
        ]

        if not task_patterns:
            return None

        # Sort by repeatability and recent success
        task_patterns.sort(
            key=lambda p: (p.repeatability_score, p.timestamp), reverse=True
        )
        return task_patterns[0]

    def get_optimal_model_by_dna(self, task_requirements: dict[str, Any]) -> str | None:
        """Get optimal model based on historical DNA matching"""
        required_capabilities = task_requirements.get("capabilities", [])
        available_memory = task_requirements.get("available_memory_gb", 125)

        best_match = None
        best_score = 0.0

        for model_id, model_dna in self.model_dna.items():
            # Check if model has required capabilities
            if any(cap in model_dna.capabilities for cap in required_capabilities):
                # Check memory compatibility
                model_memory = (
                    max(model_dna.memory_signature.values())
                    if model_dna.memory_signature
                    else 0
                )

                if model_memory <= available_memory:
                    # Calculate match score
                    capability_score = len(
                        set(required_capabilities) & set(model_dna.capabilities)
                    ) / len(required_capabilities)
                    efficiency_score = model_dna.token_efficiency or 0.8

                    total_score = capability_score * 0.6 + efficiency_score * 0.4

                    if total_score > best_score:
                        best_score = total_score
                        best_match = model_id

        return best_match

    def get_workflow_template_by_genome(
        self, workflow_type: str
    ) -> WorkflowGenome | None:
        """Get best workflow template based on historical genome data"""
        workflow_genomes = [
            w
            for w in self.workflow_genome.values()
            if workflow_type in w.workflow_id.lower()
        ]

        if not workflow_genomes:
            return None

        # Sort by success rate and token efficiency
        workflow_genomes.sort(
            key=lambda w: (w.success_rate, w.token_efficiency), reverse=True
        )
        return workflow_genomes[0]

    def learn_from_failure(self, task_type: str, failure_data: dict[str, Any]):
        """Learn from failures to update failure points in patterns"""
        # Find related success patterns
        related_patterns = [
            p
            for p in self.success_patterns.values()
            if task_type in p.pattern_id.lower()
        ]

        for pattern in related_patterns:
            # Analyze failure and add to failure points
            failure_reason = failure_data.get("reason", "unknown")
            if failure_reason not in pattern.failure_points:
                pattern.failure_points.append(failure_reason)
                logger.info(
                    f"🧬 Learned from failure: Added failure point '{failure_reason}' to pattern {pattern.pattern_id}"
                )

    def get_competitive_insights(self) -> dict[str, Any]:
        """Get insights about competitive positioning based on DNA"""
        total_patterns = len(self.success_patterns)
        elite_patterns = len(
            [p for p in self.success_patterns.values() if "elite" in p.innovation_type]
        )

        avg_efficiency = 0.0
        if self.success_patterns:
            efficiencies = [
                p.performance_metrics.get("memory_efficiency", 0.0)
                for p in self.success_patterns.values()
            ]
            avg_efficiency = sum(efficiencies) / len(efficiencies)

        return {
            "total_patterns_captured": total_patterns,
            "elite_innovations": elite_patterns,
            "average_efficiency": avg_efficiency,
            "model_diversity": len(self.model_dna),
            "workflow_diversity": len(self.workflow_genome),
            "competitive_advantages": self._analyze_competitive_advantages(),
        }

    def _analyze_competitive_advantages(self) -> list[str]:
        """Analyze COHEZION's competitive advantages based on DNA"""
        advantages = []

        # Check for elite innovations
        if any("elite" in p.innovation_type for p in self.success_patterns.values()):
            advantages.append("Elite model integration with frontier performance")

        # Check for compound engineering
        if any(
            "compound_engineering" in p.innovation_type
            for p in self.success_patterns.values()
        ):
            advantages.append("Multi-model orchestration capability")

        # Check for optimization patterns
        if any(p.repeatability_score > 0.8 for p in self.success_patterns.values()):
            advantages.append("Highly repeatable optimization patterns")

        # Check for specialized models
        specialized_models = [
            m for m in self.model_dna.values() if m.role == "specialized"
        ]
        if len(specialized_models) > 3:
            advantages.append("Deep specialized model ecosystem")

        return advantages

    def _save_pattern(self, pattern: SuccessPattern):
        """Save pattern to file"""
        try:
            self.patterns_file.parent.mkdir(parents=True, exist_ok=True)
            patterns_data = {pid: asdict(p) for pid, p in self.success_patterns.items()}
            with open(self.patterns_file, "w") as f:
                json.dump(patterns_data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save pattern: {e}")

    def _save_model_dna(self, model_dna: ModelDNA):
        """Save model DNA to file"""
        try:
            self.models_file.parent.mkdir(parents=True, exist_ok=True)
            models_data = {mid: asdict(m) for mid, m in self.model_dna.items()}
            with open(self.models_file, "w") as f:
                json.dump(models_data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save model DNA: {e}")

    def _save_workflow_genome(self, workflow_genome: WorkflowGenome):
        """Save workflow genome to file"""
        try:
            self.workflows_file.parent.mkdir(parents=True, exist_ok=True)
            workflows_data = {wid: asdict(w) for wid, w in self.workflow_genome.items()}
            with open(self.workflows_file, "w") as f:
                json.dump(workflows_data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save workflow genome: {e}")

    def export_dna_summary(self) -> dict[str, Any]:
        """Export comprehensive DNA summary for analysis"""
        return {
            "export_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_patterns": len(self.success_patterns),
                "total_models": len(self.model_dna),
                "total_workflows": len(self.workflow_genome),
                "innovation_breakdown": self._get_innovation_breakdown(),
                "competitive_insights": self.get_competitive_insights(),
                "top_patterns": self._get_top_patterns(),
                "model_portfolio_analysis": self._get_model_analysis(),
            },
        }

    def _get_innovation_breakdown(self) -> dict[str, int]:
        """Break down patterns by innovation type"""
        breakdown = {}
        for pattern in self.success_patterns.values():
            innovation_type = pattern.innovation_type
            breakdown[innovation_type] = breakdown.get(innovation_type, 0) + 1
        return breakdown

    def _get_top_patterns(self) -> list[dict[str, Any]]:
        """Get top patterns by repeatability and performance"""
        patterns = list(self.success_patterns.values())
        patterns.sort(
            key=lambda p: (
                p.repeatability_score,
                p.performance_metrics.get("tokens_per_second", 0),
            ),
            reverse=True,
        )
        return [asdict(p) for p in patterns[:10]]

    def _get_model_analysis(self) -> dict[str, Any]:
        """Analyze model portfolio"""
        models = list(self.model_dna.values())

        return {
            "total_models": len(models),
            "by_role": {
                role: len([m for m in models if m.role == role])
                for role in set(m.role for m in models)
            },
            "elite_models": len([m for m in models if m.role == "elite"]),
            "specialized_models": len([m for m in models if m.role == "specialized"]),
            "avg_token_efficiency": sum(m.token_efficiency or [0.8] for m in models)
            / len(models),
            "top_performers": sorted(
                [asdict(m) for m in models],
                key=lambda m: (
                    m.get("benchmarks", {}).get("swe_bench", 0)
                    + m.get("benchmarks", {}).get("accuracy", 0),
                    m.get("token_efficiency", 0.8),
                ),
                reverse=True,
            )[:5],
        }


# Global DNA instance for framework-wide access
PERFORMANCE_DNA = COHEZIONPerformanceDNA()


# Convenience functions
def capture_success_pattern(
    task_type: str,
    model_config: dict[str, Any],
    outcome: dict[str, Any],
    innovation_type: str,
) -> str:
    """Capture success pattern using global DNA instance"""
    return PERFORMANCE_DNA.capture_success_pattern(
        task_type, model_config, outcome, innovation_type
    )


def capture_model_dna(model_name: str, model_info: dict[str, Any]) -> str:
    """Capture model DNA using global DNA instance"""
    return PERFORMANCE_DNA.capture_model_dna(model_name, model_info)


def get_optimal_model_by_dna(task_requirements: dict[str, Any]) -> str | None:
    """Get optimal model based on DNA matching"""
    return PERFORMANCE_DNA.get_optimal_model_by_dna(task_requirements)


def get_workflow_template_by_genome(workflow_type: str) -> WorkflowGenome | None:
    """Get workflow template by genome"""
    return PERFORMANCE_DNA.get_workflow_template_by_genome(workflow_type)


def export_performance_dna() -> dict[str, Any]:
    """Export performance DNA summary"""
    return PERFORMANCE_DNA.export_dna_summary()
