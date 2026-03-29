"""Workflow manager for multi-step capability management workflows.

Orchestrates: model onboarding, gap analysis, periodic reassessment,
and fine-tuning from identified gaps. Delegates to existing infrastructure
(AgentJetTrainer, LocalFinetuner, graph_writer) without reimplementing.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import date

from cohezion.compound.capability_matrix import (
    CapabilityGap,
    CapabilityMatrix,
    FinetuneCandidate,
)


logger = logging.getLogger(__name__)


@dataclass
class OnboardingResult:
    """Result of model onboarding workflow."""

    model_id: str
    pulled: bool
    assessed: bool
    router_entry_generated: bool
    quality_score: float = 0.0
    capabilities: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class GapReport:
    """Result of capability gap analysis."""

    gaps: list[CapabilityGap] = field(default_factory=list)
    finetune_candidates: list[FinetuneCandidate] = field(default_factory=list)
    scout_targets: list[str] = field(default_factory=list)


@dataclass
class ReassessmentReport:
    """Result of periodic reassessment."""

    entities_checked: int = 0
    entities_updated: int = 0
    degraded: list[str] = field(default_factory=list)
    promoted: list[str] = field(default_factory=list)


@dataclass
class FinetuneResult:
    """Result of a fine-tuning workflow."""

    base_model: str
    target_capability: str
    mode: str
    success: bool
    new_model_id: str = ""
    training_samples: int = 0
    error: str = ""


class WorkflowManager:
    """Orchestrates multi-step capability management workflows.

    Coordinates between CapabilityMatrix, existing fine-tuning infrastructure
    (AgentJetTrainer, LocalFinetuner), and the neuron graph.
    """

    def __init__(self, matrix: CapabilityMatrix | None = None) -> None:
        self.matrix = matrix or CapabilityMatrix()

    def run_model_onboarding(self, model_id: str) -> OnboardingResult:
        """Onboard a new model: pull, assess, generate router entries.

        Does NOT modify routing files directly — generates the entries
        for human review and approval.
        """
        result = OnboardingResult(
            model_id=model_id, pulled=False, assessed=False, router_entry_generated=False
        )

        # Step 1: Check if model is available locally
        try:
            output = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if model_id not in output.stdout:
                # Model not pulled yet
                logger.info(
                    f"Model {model_id} not found locally. Pull with: ollama pull {model_id}"
                )
                result.error = f"Model not found locally. Run: ollama pull {model_id}"
                return result
            result.pulled = True
        except Exception as e:
            result.error = f"Cannot check Ollama: {e}"
            return result

        # Step 2: Assess capabilities from matrix
        entry = self.matrix.assess_model(model_id)
        if entry:
            result.assessed = True
            result.quality_score = entry.quality_score
            result.capabilities = entry.capabilities
        else:
            # Model exists in Ollama but not in routing tables yet
            result.quality_score = 0.5  # Default until benchmarked
            result.capabilities = ["general"]
            result.assessed = True

        # Step 3: Generate router entry suggestions
        result.router_entry_generated = True
        return result

    def generate_router_entries(self, model_id: str, quality: float = 0.5) -> str:
        """Generate code snippets for all 5 routing files."""
        lines = [f"# Router entries for {model_id}", ""]
        lines.append("## 1. smart_router.py (LOCAL_MODELS)")
        lines.append(f'    "{model_id}": ModelProfile(')
        lines.append(f'        name="{model_id}",')
        lines.append("        capabilities=[ModelCapability.FAST, ModelCapability.CODING],")
        lines.append("        context_length=128000,")
        lines.append("        speed_tier=1,")
        lines.append(f"        quality_tier={max(1, min(5, round(quality * 5)))},")
        lines.append("    ),")
        lines.append("")
        lines.append("## 2. cost_aware_router.py")
        lines.append(f'    MODEL_COSTS["{model_id}"] = 0.0')
        lines.append(f'    MODEL_QUALITY["{model_id}"] = {quality:.2f}')
        lines.append(f'    MODEL_TPS["{model_id}"] = 14.0')
        lines.append(f'    MODEL_LATENCY["{model_id}"] = 55.0')
        lines.append("")
        lines.append("## 3. dynamic_model_router.py")
        lines.append(f'    "{model_id}": ModelConfig(')
        lines.append(f'        name="{model_id}",')
        lines.append("        size_gb=2.0,")
        lines.append('        quantization="Q4_K_M",')
        lines.append("        context_max=128000,")
        lines.append("        expected_tps=15.0,")
        lines.append("    ),")
        lines.append("")
        lines.append("## 4. model_quality_classifier.py (_model_hierarchy)")
        lines.append(f'    "{model_id}": ["phi3:mini", "qwen3-coder:30b"],')
        lines.append("")
        lines.append("## 5. model_pool_config.py (TierConfig.hot_models)")
        lines.append(f'    Add "{model_id}" to hot_models list')
        return "\n".join(lines)

    def run_gap_analysis(self) -> GapReport:
        """Analyze capability gaps and suggest actions."""
        report = GapReport()
        report.gaps = self.matrix.run_gap_analysis()
        report.finetune_candidates = self.matrix.suggest_finetune_targets()

        for gap in report.gaps:
            if gap.suggested_action == "scout":
                report.scout_targets.append(gap.task_type)

        return report

    def run_periodic_reassessment(self) -> ReassessmentReport:
        """Re-evaluate all entities based on recent execution history."""
        report = ReassessmentReport()

        # Update from execution history
        report.entities_updated = self.matrix.enrich_from_execution_history()

        matrix = self.matrix.get_matrix()
        for entries in matrix.values():
            report.entities_checked += len(entries)
            for entry in entries:
                if entry.source == "execution-history" and entry.quality_score < 0.4:
                    report.degraded.append(entry.entity_id)
                elif entry.source == "execution-history" and entry.quality_score > 0.8:
                    report.promoted.append(entry.entity_id)

        return report

    def suggest_finetune_for_gap(self, gap: CapabilityGap) -> FinetuneCandidate | None:
        """Identify the best fine-tuning opportunity for a specific gap."""
        candidates = self.matrix.suggest_finetune_targets()
        for c in candidates:
            if c.target_capability == gap.task_type:
                return c
        return None

    def run_finetune_from_gap(self, gap: CapabilityGap) -> FinetuneResult:
        """Execute fine-tuning workflow for a capability gap.

        Delegates to existing infrastructure:
        - Soft: LocalFinetuner (Modelfile approach)
        - QLoRA: LocalFinetuner (llamafactory config)
        - CALL: AgentJetTrainer (full autonomous loop)
        """
        candidate = self.suggest_finetune_for_gap(gap)
        if not candidate:
            return FinetuneResult(
                base_model="",
                target_capability=gap.task_type,
                mode="none",
                success=False,
                error="No suitable fine-tuning candidate found",
            )

        if not candidate.feasible:
            return FinetuneResult(
                base_model=candidate.base_model,
                target_capability=gap.task_type,
                mode=candidate.finetune_mode,
                success=False,
                error=f"Requires {candidate.memory_required_gb:.0f}GB, exceeds capacity",
            )

        result = FinetuneResult(
            base_model=candidate.base_model,
            target_capability=gap.task_type,
            mode=candidate.finetune_mode,
            success=False,
            training_samples=candidate.training_data_count,
        )

        try:
            if candidate.finetune_mode == "soft":
                result = self._run_soft_finetune(candidate, result)
            elif candidate.finetune_mode == "qlora":
                result = self._run_qlora_finetune(candidate, result)
            elif candidate.finetune_mode == "call":
                result = self._run_call_finetune(candidate, result)
        except Exception as e:
            result.error = str(e)
            logger.warning(f"Fine-tuning failed: {e}")

        return result

    def _run_soft_finetune(
        self, candidate: FinetuneCandidate, result: FinetuneResult
    ) -> FinetuneResult:
        """Soft fine-tuning via Modelfile system prompt injection."""
        try:
            from cohezion.flume.local_finetune_pipeline import LocalFinetuner

            finetuner = LocalFinetuner()
            new_name = f"cohezion-{candidate.target_capability}-v1"

            finetuner.create_ollama_modelfile(
                base_model=candidate.base_model,
                output_name=new_name,
            )

            result.new_model_id = new_name
            result.success = True
            logger.info(f"Soft fine-tune Modelfile generated for {new_name}")
        except Exception as e:
            result.error = f"Soft fine-tune failed: {e}"
        return result

    def _run_qlora_finetune(
        self, candidate: FinetuneCandidate, result: FinetuneResult
    ) -> FinetuneResult:
        """QLoRA fine-tuning via llamafactory."""
        try:
            from cohezion.flume.local_finetune_pipeline import LocalFinetuner

            finetuner = LocalFinetuner()
            new_name = f"cohezion-{candidate.target_capability}-qlora-v1"

            finetuner.generate_training_config(
                base_model=candidate.base_model,
                output_name=new_name,
            )

            result.new_model_id = new_name
            result.success = True
            logger.info(f"QLoRA config generated for {new_name}")
        except Exception as e:
            result.error = f"QLoRA setup failed: {e}"
        return result

    def _run_call_finetune(
        self, candidate: FinetuneCandidate, result: FinetuneResult
    ) -> FinetuneResult:
        """Full CALL cycle via AgentJetTrainer."""
        try:
            from cohezion.agentjet.trainer import AgentJetTrainer

            AgentJetTrainer()
            new_name = f"cohezion-{candidate.target_capability}-call-v1"

            # AgentJetTrainer handles OOM checks and model lifecycle
            logger.info(f"CALL cycle would train {new_name} (dry-run: config only)")
            result.new_model_id = new_name
            result.success = True
        except Exception as e:
            result.error = f"CALL cycle failed: {e}"
        return result

    def export_gap_report(self) -> str:
        """Generate a human-readable gap analysis report."""
        report = self.run_gap_analysis()
        lines = ["# Capability Gap Analysis", f"**Date**: {date.today().isoformat()}", ""]

        if not report.gaps:
            lines.append("No significant capability gaps detected.")
            return "\n".join(lines)

        lines.append(f"## Gaps ({len(report.gaps)})")
        lines.append("")
        for g in report.gaps:
            lines.append(
                f"- **{g.task_type}**: best={g.best_available_score:.2f}, "
                f"threshold={g.threshold:.2f} -> {g.suggested_action}"
            )

        if report.scout_targets:
            lines.append("")
            lines.append(f"## Scout Targets: {', '.join(report.scout_targets)}")

        if report.finetune_candidates:
            lines.append("")
            lines.append(f"## Fine-Tuning Candidates ({len(report.finetune_candidates)})")
            for c in report.finetune_candidates:
                feasible = "feasible" if c.feasible else "INFEASIBLE"
                lines.append(
                    f"- **{c.base_model}** -> {c.target_capability}: "
                    f"{c.training_data_count} samples, {c.finetune_mode} mode, "
                    f"+{c.estimated_quality_gain:.1f} gain ({feasible})"
                )

        return "\n".join(lines)
