r"""METR Negentropy Controller & Long-Horizon AGI Benchmark Governor.
===================================================================
Orchestrates long-horizon (100+ step) agent trajectories for the Kaggle/METR
'Measuring Progress Toward AGI' benchmark (due April 16, 2026):

1. Enforces the $50/day AI Models API quota with deterministic budgeting.
2. Applies the My Big TOE Negentropy Tripwire: tracks sliding window entropy \Delta S.
   If \Delta S > 0 over consecutive steps, halts execution and rolls back to the
   last autopoietically closed state in SurrealDB, eliminating token waste.
3. Delegates all AST parsing, syntax validation, and tool-call checks to
   AutoHarness 0-cost bytecode verifiers before escalating to cloud models.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from cohezion.agi.autoharness_policy import ActionPolicyResult, AutoHarnessPolicy
from cohezion.contracts import PoincarePoint
from cohezion.data_mesh.durable_precipitation_bridge import (
    DurablePrecipitationBridge,
    DurableWitnessMark,
)
from cohezion.memory.autopoietic_memory_fabric import AutopoieticMemoryFabric
from cohezion.physics.my_big_toe_entropy_engine import (
    EntropyState,
    MyBigTOEEntropyEngine,
)

logger = logging.getLogger("metr_negentropy_controller")

DAILY_QUOTA_LIMIT_USD: float = 50.00
TRIPWIRE_DRIFT_STEPS_THRESHOLD: int = 2
MAX_ALLOWABLE_ENTROPY_DRIFT: float = 0.05


@dataclass(frozen=True, slots=True)
class AgentStepRecord:
    """A single discrete step in a long-horizon agent trajectory."""

    step_number: int
    action_description: str
    state_point: Sequence[float]
    coherence: float
    cost_usd: float
    autoharness_bypassed_llm: bool
    entropy_state: EntropyState
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class ControllerDecision:
    """The governor's decision on whether an agent may proceed, must verify, or must roll back."""

    allowed: bool
    action: str  # "PROCEED", "TRIPWIRE_ROLLBACK", "QUOTA_HALT", "AUTOHARNESS_REJECT"
    current_daily_spend_usd: float
    remaining_daily_budget_usd: float
    sliding_delta_entropy: float
    last_stable_checkpoint_step: int
    reason: str
    execution_latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


class METRNegentropyController:
    """Controller enforcing negentropy tripwires and quota governance for long-horizon AGI tasks."""

    def __init__(
        self,
        daily_quota_usd: float = DAILY_QUOTA_LIMIT_USD,
        tripwire_steps: int = TRIPWIRE_DRIFT_STEPS_THRESHOLD,
        entropy_engine: MyBigTOEEntropyEngine | None = None,
        autoharness: AutoHarnessPolicy | None = None,
        vault_dir: Path | None = None,
    ) -> None:
        self.daily_quota_usd = daily_quota_usd
        self.tripwire_steps = tripwire_steps
        self.entropy_engine = entropy_engine or MyBigTOEEntropyEngine()
        self.autoharness = autoharness or AutoHarnessPolicy()
        self.vault_dir = vault_dir
        self.bridge = DurablePrecipitationBridge(vault_dir=self.vault_dir)

        self._trajectory: list[AgentStepRecord] = []
        self._daily_spend_usd: float = 0.0
        self._last_checkpoint_step: int = 0

    @property
    def current_spend(self) -> float:
        return self._daily_spend_usd

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.daily_quota_usd - self._daily_spend_usd)

    def record_step(
        self,
        action_desc: str,
        state_point: Sequence[float],
        coherence: float = 0.50,
        estimated_cost_usd: float = 0.0,
        bypassed_llm: bool = True,
    ) -> AgentStepRecord:
        """Record an executed step and evaluate its entropy state."""
        step_num = len(self._trajectory) + 1
        current_entropy = self.entropy_engine.calculate_state_entropy(
            [state_point], [coherence]
        )

        record = AgentStepRecord(
            step_number=step_num,
            action_description=action_desc,
            state_point=state_point,
            coherence=coherence,
            cost_usd=estimated_cost_usd,
            autoharness_bypassed_llm=bypassed_llm,
            entropy_state=current_entropy,
        )
        self._trajectory.append(record)
        self._daily_spend_usd += estimated_cost_usd

        # If coherence is near 0.50 and step is valid, mark as stable checkpoint
        if abs(coherence - 0.50) <= 0.02 and record.step_number > self._last_checkpoint_step:
            self._last_checkpoint_step = record.step_number

        return record

    def evaluate_proposed_action(
        self,
        proposed_action: str,
        proposed_state_point: Sequence[float],
        proposed_coherence: float = 0.50,
        estimated_cost_usd: float = 0.0,
        action_payload: dict[str, Any] | None = None,
    ) -> ControllerDecision:
        """Evaluate a proposed action against daily quota and the My Big TOE Negentropy Tripwire."""
        t0 = time.perf_counter()

        # Gate 1: Check Daily API Quota Floor
        projected_spend = self._daily_spend_usd + estimated_cost_usd
        if projected_spend > self.daily_quota_usd:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return ControllerDecision(
                allowed=False,
                action="QUOTA_HALT",
                current_daily_spend_usd=self._daily_spend_usd,
                remaining_daily_budget_usd=self.remaining_budget,
                sliding_delta_entropy=0.0,
                last_stable_checkpoint_step=self._last_checkpoint_step,
                reason=f"Exceeds daily quota limit (${self.daily_quota_usd:.2f})",
                execution_latency_ms=dt_ms,
            )

        # Gate 2: AutoHarness Deterministic Pre-Verification
        payload = action_payload or {"coherence": proposed_coherence}
        h_res = self.autoharness.evaluate_policy(proposed_action, payload)
        if not h_res.allowed:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return ControllerDecision(
                allowed=False,
                action="AUTOHARNESS_REJECT",
                current_daily_spend_usd=self._daily_spend_usd,
                remaining_daily_budget_usd=self.remaining_budget,
                sliding_delta_entropy=0.0,
                last_stable_checkpoint_step=self._last_checkpoint_step,
                reason=f"AutoHarness rejected action: {h_res.reason}",
                execution_latency_ms=dt_ms,
            )

        # Gate 3: My Big TOE Negentropy Tripwire
        # Compare proposed state entropy with trajectory history
        if not self._trajectory:
            # First step: unconditionally allowed if within budget and policy
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return ControllerDecision(
                allowed=True,
                action="PROCEED",
                current_daily_spend_usd=self._daily_spend_usd,
                remaining_daily_budget_usd=self.remaining_budget,
                sliding_delta_entropy=0.0,
                last_stable_checkpoint_step=self._last_checkpoint_step,
                reason="Initial state transition within bounds",
                execution_latency_ms=dt_ms,
            )

        # Calculate transition entropy from previous state
        prev_step = self._trajectory[-1]
        transition = self.entropy_engine.evaluate_transition(
            pre_points=[prev_step.state_point],
            post_points=[proposed_state_point],
            pre_coherences=[prev_step.coherence],
            post_coherences=[proposed_coherence],
        )

        sliding_delta_s = transition.delta_entropy

        # Check consecutive drift
        drift_count = 0
        if len(self._trajectory) >= self.tripwire_steps:
            for i in range(1, self.tripwire_steps):
                p_curr = self._trajectory[-i]
                p_prev = self._trajectory[-(i + 1)]
                if p_curr.entropy_state.total_system_entropy > p_prev.entropy_state.total_system_entropy:
                    drift_count += 1

        if sliding_delta_s > MAX_ALLOWABLE_ENTROPY_DRIFT and drift_count >= (self.tripwire_steps - 1):
            # Tripwire activated! Compounding entropy detected
            dt_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning(
                "NEGENTROPY TRIPWIRE TRIGGERED: delta_s=%.4f, drift_count=%d. Halting and rolling back.",
                sliding_delta_s,
                drift_count,
            )
            return ControllerDecision(
                allowed=False,
                action="TRIPWIRE_ROLLBACK",
                current_daily_spend_usd=self._daily_spend_usd,
                remaining_daily_budget_usd=self.remaining_budget,
                sliding_delta_entropy=sliding_delta_s,
                last_stable_checkpoint_step=self._last_checkpoint_step,
                reason=(
                    f"Compounding entropy drift detected (Delta S = {sliding_delta_s:.4f} > {MAX_ALLOWABLE_ENTROPY_DRIFT}). "
                    f"Rollback to checkpoint step {self._last_checkpoint_step} required."
                ),
                execution_latency_ms=dt_ms,
            )

        # Negentropy invariant satisfied (Delta S <= 0 or within acceptable micro-fluctuation)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return ControllerDecision(
            allowed=True,
            action="PROCEED",
            current_daily_spend_usd=self._daily_spend_usd,
            remaining_daily_budget_usd=self.remaining_budget,
            sliding_delta_entropy=sliding_delta_s,
            last_stable_checkpoint_step=self._last_checkpoint_step,
            reason="Negentropy invariant satisfied; state transition allowed",
            execution_latency_ms=dt_ms,
        )

    def execute_rollback(self) -> int:
        """Roll back trajectory to the last stable autopoietic checkpoint."""
        if self._last_checkpoint_step == 0 or not self._trajectory:
            self._trajectory.clear()
            logger.info("Rolled back to origin state.")
            return 0

        target_idx = self._last_checkpoint_step
        discarded_steps = len(self._trajectory) - target_idx
        self._trajectory = self._trajectory[:target_idx]
        logger.info("Rolled back %d steps to checkpoint step %d.", discarded_steps, target_idx)
        return target_idx
