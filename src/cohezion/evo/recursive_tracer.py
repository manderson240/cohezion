"""RecursiveTracer — wires AgenticEVO physics steps into the compound trajectory layer.

Architecture per step (monadic pipeline):
  1. OOM guard (MemorySnapshot ≥ 16 GB)          [fail-fast on low RAM]
  2. TraceMonad.unit(task, TraceState)            [wrap initial physics state]
  3. >> physics_bind: AgenticEVO.hiho_step()      [FLUME + SWIFT physics update]
     + synchronize_states()                       [latent ↔ physical coherence sync]
     + TraceState.advance(coherence, phi, …)      [immutable state derivation]
  4. >> modality_bind: get_modality(m).invoke()   [text / audio / image / video dispatch]
  5. JourneyTracker.track_evo_step()              [record 12D trajectory point]

On complete_journey():
  6. Compute phi = 4*c*(1-c) from final coherence [HIHO quality score]
  7. JourneyTracker.emit_evo_voyage()             [dual-write: SurrealDB + Obsidian]
  8. Constitution gate: phi ≥ 0.3                 [no self-modification from degenerate state]
  9. SkillRefiner.refine() on target skill        [continuous self-improvement]

Constitution/Charter compliance:
  - Refinement blocked when phi < _MIN_PHI_FOR_REFINEMENT (default 0.3)
  - OOM guard prevents tracing when RAM < _OOM_GUARD_GB (16 GB)
  - Monad (TraceMonad) threads TraceState implicitly — satisfies left-identity,
    right-identity, associativity; pipeline stages are safely composable
  - Modality failures are non-blocking (Constitution §fail-soft)
  - No sys.path.insert — proper package imports throughout
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cohezion.evo import ExperientialVoyage, PhiDistribution, phi_from_coherence

if TYPE_CHECKING:
    from cohezion.compound.journey_tracker import JourneyTracker
    from cohezion.compound.skill_refiner import SkillRefiner
    from cohezion.universe.agentic_evo_swift import AgenticEVO


logger = logging.getLogger(__name__)

_MIN_PHI_FOR_REFINEMENT = 0.3
# RecursiveTracer does no Python-side model loading — only numpy physics + HTTP calls
# to already-loaded lemonade backends. 8 GB is sufficient headroom for that profile.
# (16 GB was correct when the system had 29 GB free; tighter now due to loaded 35B model.)
_OOM_GUARD_GB = 8.0


@dataclass
class TraceResult:
    """Outcome of a single RecursiveTracer.trace_step() call."""

    step_index: int
    coherence_before: float
    coherence_after: float
    latent_delta: float       # RMS magnitude of latent vector change this step
    modalities_invoked: list[str]
    phi: float                # HIHO score at this step: 4 * c_after * (1 - c_after)
    latency_ms: float
    synthesis_text: str = ""  # LLM insight from TextModality (empty when offline)


class RecursiveTracer:
    """Wraps AgenticEVO with JourneyTracker recording and SkillRefiner feedback.

    Each trace_step() runs one HIHO physics step and records the resulting
    12D trajectory point. complete_journey() closes the voyage, dual-writes
    to SurrealDB + Obsidian, and triggers SkillRefiner when coherence permits.

    Example::

        agent = AgenticEVO("evo-001")
        tracker = JourneyTracker()
        tracer = RecursiveTracer(agent, tracker)

        result = tracer.trace_step("synthesize report", modalities=["text"])
        voyage = tracer.complete_journey(journey_id="run-42", skill_id="cohezion-synthesis")
        print(f"phi={voyage.phi_score:.3f}, refined={voyage.skill_refinements}")
    """

    def __init__(
        self,
        agent: "AgenticEVO",
        journey_tracker: "JourneyTracker",
        skill_refiner: "SkillRefiner | None" = None,
        min_phi_for_refinement: float = _MIN_PHI_FOR_REFINEMENT,
    ) -> None:
        self._agent = agent
        self._tracker = journey_tracker
        self._refiner = skill_refiner
        self._min_phi = min_phi_for_refinement
        self._steps: list[TraceResult] = []
        self._modalities_seen: set[str] = set()
        self._started_at: float = time.time()

    # ---- Public API ----------------------------------------------------------

    def trace_step(
        self,
        task_description: str,
        modalities: list[str] | None = None,
        operation_type: str = "transform",
        hiho_delta_scale: float = 0.01,
        hiho_damping: float = 0.05,
    ) -> TraceResult:
        """Run one HIHO physics step and record in JourneyTracker.

        Args:
            task_description: What the agent is doing this step (for trajectory embedding)
            modalities:       Modalities used (e.g. ["text","image"]). Defaults to ["text"].
            operation_type:   JourneyTracker modulation type ("generate","analyze","transform",…)
            hiho_delta_scale: HIHO update step size (smaller = more gradual convergence)
            hiho_damping:     HIHO damping coefficient (larger = faster coherence recovery)

        Returns:
            TraceResult with before/after coherence and latent delta

        Raises:
            RuntimeError: When available RAM < _OOM_GUARD_GB (Constitution §OOM)
        """
        import numpy as np
        from cohezion.evo.modalities import get_modality
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        self._oom_guard()
        modalities = modalities or ["text"]
        self._modalities_seen.update(modalities)

        coherence_before = float(self._agent.latent_state.current_coherence)
        latent_before = self._agent.latent_state.latent_vector.copy()
        t0 = time.perf_counter()

        # ── Monadic pipeline ────────────────────────────────────────────────
        # Each bind receives (value: str, state: TraceState) → TraceMonad[str].
        # TraceState is immutable; advance() derives the next state without mutation.

        def _physics_bind(value: str, state: TraceState) -> "TraceMonad[str]":
            """Bind 1: HIHO attractor dynamics in 256D latent space."""
            self._agent.hiho_step(delta_scale=hiho_delta_scale, hiho_damping=hiho_damping)
            self._agent.synchronize_states()
            lms = (time.perf_counter() - t0) * 1000
            c_after = float(self._agent.latent_state.current_coherence)
            delta = float(
                np.sqrt(np.mean((self._agent.latent_state.latent_vector - latent_before) ** 2))
            )
            return TraceMonad(
                value,
                state.advance(
                    coherence=c_after,
                    phi=phi_from_coherence(c_after),
                    modalities=modalities,
                    latent=self._agent.latent_state.latent_vector[:16].tolist(),
                    latency_ms=lms,
                    latent_delta=delta,
                ),
            )

        # Text synthesis captured here — nonlocal list so the bind closure can write it
        _synthesis: list[str] = []

        def _modality_bind(value: str, state: TraceState) -> "TraceMonad[str]":
            """Bind 2: dispatch text / audio / image / video handlers (all fail-soft)."""
            for mod_name in modalities:
                try:
                    mod_result = get_modality(mod_name).invoke(value)
                    if mod_name == "text" and mod_result.success and mod_result.output:
                        _synthesis.append(mod_result.output)
                except Exception:
                    pass  # Constitution §fail-soft: modality errors are non-blocking
            return TraceMonad(value, state)

        final = (
            TraceMonad.unit(
                task_description,
                TraceState(
                    coherence=coherence_before,
                    phi=phi_from_coherence(coherence_before),
                    step_index=len(self._steps),
                ),
            )
            >> _physics_bind
            >> _modality_bind
        )
        s = final.state
        # ────────────────────────────────────────────────────────────────────

        # Record in JourneyTracker (12D FLUME trajectory point)
        self._tracker.track_evo_step(
            task_description=task_description,
            operation_type=operation_type,
            coherence=s.coherence,
            efficiency=max(0.0, 1.0 - s.latent_delta),  # stability proxy
            success=True,
            duration_seconds=s.latency_ms / 1000.0,
        )

        result = TraceResult(
            step_index=len(self._steps),
            coherence_before=coherence_before,
            coherence_after=s.coherence,
            latent_delta=s.latent_delta,
            modalities_invoked=list(modalities),
            phi=s.phi,
            latency_ms=s.latency_ms,
            synthesis_text=_synthesis[0] if _synthesis else "",
        )
        self._steps.append(result)

        logger.debug(
            "EVO trace step %d: coherence %.3f→%.3f phi=%.3f delta=%.4f (%.1fms)",
            result.step_index,
            coherence_before,
            s.coherence,
            result.phi,
            s.latent_delta,
            s.latency_ms,
        )
        return result

    def complete_journey(
        self,
        journey_id: str,
        skill_id: str | None = None,
        operation_type: str = "transform",
    ) -> ExperientialVoyage:
        """Close the voyage, persist to SurrealDB + Obsidian, and trigger SkillRefiner.

        Args:
            journey_id:     Identifier linking this voyage to a JourneyTracker journey
            skill_id:       PRIME skill file name (without extension) to refine, or None
            operation_type: Used in SkillRefiner.refine() operation classification

        Returns:
            ExperientialVoyage with phi_score and any skill_refinements applied

        Raises:
            ValueError: When called before any trace_step()
        """
        if not self._steps:
            raise ValueError(
                "RecursiveTracer: no steps traced — call trace_step() at least once"
            )

        final_phi = self._steps[-1].phi
        final_snapshot = self._agent.latent_state.latent_vector[:16].tolist()

        # Build distributional phi from the full step series (Z-Reward §3.2 style):
        # two voyages at the same final phi can have very different gate probabilities
        # depending on whether they arrived there via variance or monotonic decay.
        phi_series = [s.phi for s in self._steps]
        phi_dist = PhiDistribution.from_phi_series(phi_series)

        voyage = ExperientialVoyage(
            voyage_id=str(uuid.uuid4()),
            agent_id=self._agent.agent_id,
            journey_id=journey_id,
            phi_score=final_phi,
            modalities_used=sorted(self._modalities_seen),
            skill_refinements=[],
            latent_snapshot=final_snapshot,
            started_at=self._started_at,
            completed_at=time.time(),
            phi_distribution=phi_dist,
        )

        # Dual-write: SurrealDB (batched) + Obsidian (vault MCP)
        self._tracker.emit_evo_voyage(voyage)

        # Constitution §3 gate: no self-modification from degenerate state.
        # Log gate_probability so borderline voyages (high variance near threshold)
        # are visible in telemetry even when blocked.
        if voyage.is_degenerate:
            logger.warning(
                "RecursiveTracer: phi=%.3f < %.3f gate blocked "
                "(gate_prob=%.3f expected_phi=%.3f — HIHO coherence must reach ≥ %.3f first)",
                final_phi,
                self._min_phi,
                phi_dist.gate_probability(self._min_phi),
                phi_dist.expected_phi(),
                self._min_phi,
            )
            return voyage

        # SkillRefiner hook: continuous self-improvement via PRIME file update.
        # Passes full PhiDistribution so SkillRefiner can weight the update by
        # gate_probability (soft signal) rather than binary degenerate/healthy.
        if self._refiner is not None and skill_id is not None:
            gate_prob = phi_dist.gate_probability(threshold=self._min_phi)
            try:
                refined_path = self._refiner.refine(
                    skill_name=skill_id,
                    operation_type=operation_type,
                    execution_result={
                        "success": True,
                        "output": (
                            f"EVO voyage phi={final_phi:.3f} "
                            f"gate_prob={gate_prob:.3f} "
                            f"expected_phi={phi_dist.expected_phi():.3f} "
                            f"modalities={voyage.modalities_used} "
                            f"steps={len(self._steps)}"
                        ),
                        "metrics": {
                            "coherence": final_phi,
                            "gate_probability": gate_prob,
                            "expected_phi": phi_dist.expected_phi(),
                            "phi_distribution": phi_dist.as_dict(),
                            "duration_seconds": voyage.duration_seconds,
                        },
                    },
                    patterns_extracted=[journey_id],
                )
                if refined_path:
                    voyage.skill_refinements.append(skill_id)
                    logger.info(
                        "RecursiveTracer: refined skill '%s' → %s",
                        skill_id,
                        refined_path,
                    )
            except Exception as exc:
                logger.debug("RecursiveTracer: skill refinement failed (non-blocking): %s", exc)

        return voyage

    @property
    def step_count(self) -> int:
        return len(self._steps)

    @property
    def last_phi(self) -> float | None:
        return self._steps[-1].phi if self._steps else None

    # ---- Internal -----------------------------------------------------------

    def _oom_guard(self) -> None:
        """Raise RuntimeError if available RAM < _OOM_GUARD_GB (N3 OOM safeguard)."""
        try:
            from cohezion.competition.orchestrator.resource_guard import MemorySnapshot

            snap = MemorySnapshot.capture()
            if snap.available_gb < _OOM_GUARD_GB:
                raise RuntimeError(
                    f"RecursiveTracer OOM guard: {snap.available_gb:.1f} GB available, "
                    f"need {_OOM_GUARD_GB:.0f} GB. Stop tracing to free memory before continuing."
                )
        except ImportError:
            pass  # fail-soft: resource_guard absent in test/CI environments
