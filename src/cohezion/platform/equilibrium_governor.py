r"""Master Cybernetic Equilibrium Governor.
========================================
Implements Viable System Model (VSM) cybernetic governance balancing:
  1. Silicon Resources: AMD Zen 5 CPU (AVX-512), Radeon 8060S iGPU (GTT UMA), XDNA 2 NPU (SRAM).
  2. Model Tiers: Tier 1 Local (:13305) -> Tier 2 Ollama Cloud MoE -> Tier 3 Thinking Cloud.
  3. Somatosensory Mechanoreceptors: Proprioceptive Sensor & Autogenic Inhibition.
  4. Hyperbolic Conformal Alignment: CTAC 0.50 HIHO Coherence Attractor in Poincaré space.
  5. Lyapunov Drift-Plus-Penalty: Optimal dynamic dispatch minimizing queue surge and resource cost.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from cohezion.cybernetics.proprioceptive_sensor import ProprioceptiveCyberneticsEngine
from cohezion.physics.ctac_engine import CTACEngine
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.polyglot.runtime_audit import PolyglotCapabilities, audit_polyglot_capabilities
from cohezion.polyglot.rust_bridge import is_rust_accelerated


logger = logging.getLogger(__name__)


class DispatchTier(StrEnum):
    """Execution tiers governed by the equilibrium policy."""

    TIER1_LOCAL_NPU = "tier1_npu"
    TIER1_LOCAL_CPU = "tier1_cpu"
    TIER1_LOCAL_IGPU = "tier1_igpu"
    TIER2_OLLAMA_CLOUD = "tier2_cloud"
    TIER3_THINKING_API = "tier3_api"


@dataclass(frozen=True, slots=True)
class GovernorAction:
    """Action decision issued by the Master Equilibrium Governor."""

    tier: DispatchTier
    model_hint: str
    allowed: bool
    reason: str
    hiho_coherence: float
    gtt_strain: float
    conformal_kappa: float
    lyapunov_penalty: float


@dataclass
class QueueState:
    """Current pending task queue lengths across primary lanes."""

    kaggle_tasks: int = 0
    research_tasks: int = 0
    refactor_tasks: int = 0
    verify_tasks: int = 0

    def total_backlog(self) -> int:
        return self.kaggle_tasks + self.research_tasks + self.refactor_tasks + self.verify_tasks


class MasterEquilibriumGovernor:
    """Central Viable System Model (VSM System 3) Governor."""

    def __init__(self, lyapunov_tradeoff_v: float = 10.0) -> None:
        self.lyapunov_v = lyapunov_tradeoff_v
        self.proprioception = ProprioceptiveCyberneticsEngine()
        self.ctac = CTACEngine(target_coherence=0.50)
        self.caps: PolyglotCapabilities = audit_polyglot_capabilities()
        self.queue_state = QueueState()
        self.conformal_kappa: float = 1.0

    def record_queue_arrival(self, lane: str, count: int = 1) -> None:
        """Track incoming task arrivals for Lyapunov queue drift calculation."""
        if lane == "kaggle":
            self.queue_state.kaggle_tasks += count
        elif lane == "research":
            self.queue_state.research_tasks += count
        elif lane == "refactor":
            self.queue_state.refactor_tasks += count
        elif lane == "verify":
            self.queue_state.verify_tasks += count

    def record_queue_completion(self, lane: str, count: int = 1) -> None:
        """Decrement queue length upon task completion."""
        if lane == "kaggle":
            self.queue_state.kaggle_tasks = max(0, self.queue_state.kaggle_tasks - count)
        elif lane == "research":
            self.queue_state.research_tasks = max(0, self.queue_state.research_tasks - count)
        elif lane == "refactor":
            self.queue_state.refactor_tasks = max(0, self.queue_state.refactor_tasks - count)
        elif lane == "verify":
            self.queue_state.verify_tasks = max(0, self.queue_state.verify_tasks - count)

    def compute_lyapunov_drift_plus_penalty(
        self, candidate_tier: DispatchTier, resource_cost: float
    ) -> float:
        """Calculate Lyapunov Drift-Plus-Penalty: Delta L(Q) + V * P."""
        q = float(self.queue_state.total_backlog())
        # Lyapunov drift component: (q + 1)^2 - q^2 = 2q + 1
        drift = 2.0 * q + 1.0

        # Tier cost multiplier
        cost_weight = {
            DispatchTier.TIER1_LOCAL_NPU: 0.1,  # Zero UMA, <2W
            DispatchTier.TIER1_LOCAL_CPU: 0.2,  # Sub-4GB
            DispatchTier.TIER1_LOCAL_IGPU: 0.8,  # GTT aperture footprint
            DispatchTier.TIER2_OLLAMA_CLOUD: 0.5,  # Remote compute
            DispatchTier.TIER3_THINKING_API: 2.0,  # Expensive premium API
        }.get(candidate_tier, 1.0)

        penalty = self.lyapunov_v * (resource_cost * cost_weight)
        return float(drift + penalty)

    def evaluate_dispatch(
        self,
        task_type: str,
        code_context: str = "",
        estimated_tokens: int = 4000,
        required_reasoning: str = "medium",
    ) -> GovernorAction:
        """Evaluate optimal homeostatic dispatch matching Ashby's Requisite Variety."""
        # 1. Somatosensory Mechanoreceptor Sampling
        proprio_state = self.proprioception.sample(code_context)
        inhibited, inhibit_reason = self.proprioception.check_autogenic_inhibition_reflex(
            proprio_state
        )

        if inhibited:
            return GovernorAction(
                tier=DispatchTier.TIER1_LOCAL_NPU,
                model_hint="qwen3.5-4b-FLM",
                allowed=False,
                reason=f"Autogenic inhibition tripped: {inhibit_reason}",
                hiho_coherence=0.50,
                gtt_strain=proprio_state.gtt_memory_strain,
                conformal_kappa=self.conformal_kappa,
                lyapunov_penalty=999.0,
            )

        # 2. Conformal Topology Calibration (CTAC HIHO 0.50 Attractor)
        # Vectorized projection into Poincaré ball
        norm = max(0.01, min(0.95, proprio_state.context_occupancy_ratio))
        pt = PoincareManifoldND.project([norm] * 12, target_dim=12)
        ctac_state = self.ctac.evaluate_topology([pt], current_kappa=self.conformal_kappa)
        self.conformal_kappa = ctac_state.conformal_kappa

        # 3. Silicon GTT Aperture Guard Check
        memory_strain = proprio_state.gtt_memory_strain
        gtt_safe = memory_strain < 0.70

        # 4. Multi-Tier Arbitration via EVI and Lyapunov Drift-Plus-Penalty
        is_deep_reasoning = required_reasoning in ("high", "xhigh", "max") or task_type in (
            "formal_proof",
            "grandmaster_logic",
            "meta_architecture",
        )
        is_large_coding = (
            task_type in ("coding_refactor", "multi_file_patch") or estimated_tokens > 8000
        )

        if is_deep_reasoning and required_reasoning == "max":
            chosen_tier = DispatchTier.TIER3_THINKING_API
            model_hint = "gemini-3.8-flash-high"
            cost = 5.0
        elif is_large_coding:
            chosen_tier = DispatchTier.TIER2_OLLAMA_CLOUD
            model_hint = "glm-5.3:cloud"
            cost = 1.0
        elif is_deep_reasoning:
            chosen_tier = DispatchTier.TIER2_OLLAMA_CLOUD
            model_hint = "deepseek-v4-pro:cloud"
            cost = 1.2
        elif task_type in ("ast_verify", "health_probe", "sentinel"):
            chosen_tier = DispatchTier.TIER1_LOCAL_NPU
            model_hint = "qwen3.5-4b-FLM"
            cost = 0.05
        elif gtt_safe and self.caps.simd.has_avx512f and is_rust_accelerated():
            chosen_tier = DispatchTier.TIER1_LOCAL_CPU
            model_hint = "cohezion_physics_core_avx512"
            cost = 0.1
        else:
            chosen_tier = DispatchTier.TIER1_LOCAL_NPU
            model_hint = "qwen3.5-4b-FLM"
            cost = 0.1

        dpp = self.compute_lyapunov_drift_plus_penalty(chosen_tier, cost)

        return GovernorAction(
            tier=chosen_tier,
            model_hint=model_hint,
            allowed=True,
            reason=f"Equilibrium dispatch selected: HIHO C={ctac_state.coherence:.3f}, GTT strain={memory_strain:.3f}, DPP={dpp:.2f}",
            hiho_coherence=ctac_state.coherence,
            gtt_strain=memory_strain,
            conformal_kappa=self.conformal_kappa,
            lyapunov_penalty=round(dpp, 3),
        )


_GOVERNOR_SINGLETON: MasterEquilibriumGovernor | None = None


def get_equilibrium_governor() -> MasterEquilibriumGovernor:
    """Retrieve or initialize the global MasterEquilibriumGovernor instance."""
    global _GOVERNOR_SINGLETON
    if _GOVERNOR_SINGLETON is None:
        _GOVERNOR_SINGLETON = MasterEquilibriumGovernor()
    return _GOVERNOR_SINGLETON
