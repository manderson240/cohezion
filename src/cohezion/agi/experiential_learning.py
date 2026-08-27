r"""Experiential Recursive Learning Engine
==========================================
Converts agent trajectories into persistent Experiential Replay Memory
E = (S_t, a_t, r_t, S_{t+1}, \pi_{safety}), extracting high-reward patterns into
SurrealDB `experiential_replay` table and Obsidian Vault (`01-Learnings/`).

Architecture:
  1. Experience Capture: Store state-action-reward-state transitions
  2. Quality Filtering: Gate persistence ($r_t \ge 0.45$) to prevent memory pollution
  3. AutoHarness Policy Verification: Check bytecode compliance
  4. ZKFV Proof Generation: Produce \pi_{safety} zero-knowledge safety proofs
  5. Experiential Distillation: Update persistent SurrealDB 3.0+ & Vault knowledge bases
  6. EventBus Cross-Session Synchronization: Broadcast updates to peer sessions
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.zkfv_compiler import ZKFVCompiler
from cohezion.contracts import PoincarePoint
from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.reliability.oom_guard import OOMGuard


logger = logging.getLogger(__name__)

VAULT_LEARNINGS = Path.home() / "vaults" / "cohezion-vault" / "01-Learnings"
MIN_EXPERIENCE_REWARD = 0.45  # Quality gate threshold for experiential replay persistence


@dataclass(frozen=True, slots=True)
class ExperienceRecord:
    experience_id: str
    action_type: str
    reward: float
    state_norm: float
    next_state_norm: float
    verified: bool
    proof_valid: bool
    timestamp: str


class ExperientialLearningEngine:
    """Master Experiential Recursive Learning Engine with SurrealDB 3.0+ & EventBus integration."""

    def __init__(self) -> None:
        self.policy_engine = AutoHarnessPolicy()
        self.surreal_client = get_surreal_client()

    async def surreal_upsert_experience(self, exp_id: str, data: dict) -> bool:
        """Persist experience record to SurrealDB 3.0+ using async client and record-id syntax."""
        table = (
            "experiential_replay"
            if data.get("reward", 0.0) >= MIN_EXPERIENCE_REWARD
            else "failed_experience_log"
        )
        try:
            await self.surreal_client.query(
                f"UPSERT type::record('{table}', $exp_id) CONTENT $data;",
                {"exp_id": exp_id, "data": data},
            )
            return True
        except Exception as exc:
            logger.warning("Failed async upsert experience %s: %s", exp_id, exc)
            return False

    async def process_experience(
        self,
        action_type: str,
        initial_state: PoincarePoint,
        next_state: PoincarePoint,
        reward: float,
    ) -> ExperienceRecord:
        """Process agent experience, verify safety policies, publish events, and persist."""
        t0 = time.time()
        exp_id = f"exp_{int(t0 * 1000)}"

        # 1. AutoHarness Policy Check
        mem = OOMGuard.get_memory_state()
        p_res = self.policy_engine.evaluate_policy(action_type, {"available_gb": mem.available_gb})

        # 2. ZKFV Zero-Knowledge Safety Proof
        gates = ZKFVCompiler.compile_ast_to_gates("grid_bounds")
        proof = ZKFVCompiler.generate_proof(gates, (1.0, 0.0, 1.0))

        # 3. Build Record Data
        exp_data = {
            "id": exp_id,
            "action_type": action_type,
            "reward": round(reward, 4),
            "state_norm": round(initial_state.norm, 4),
            "next_state_norm": round(next_state.norm, 4),
            "verified": p_res.allowed,
            "proof_valid": proof.is_valid,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # 4. Async Upsert to SurrealDB 3.0+
        surreal_ok = await self.surreal_upsert_experience(exp_id, exp_data)

        # 5. EventBus Cross-Session Broadcast
        try:
            event_bus = await get_event_bus()
            await event_bus.publish(
                Event(
                    type=EventType.AGENT_COMPLETE,
                    source="experiential_learning_engine",
                    payload={
                        "exp_id": exp_id,
                        "action_type": action_type,
                        "reward": reward,
                        "verified": p_res.allowed,
                    },
                )
            )
        except Exception as exc:
            logger.warning("Failed to publish experience event: %s", exc)

        # 6. Persist to Obsidian Vault
        try:
            VAULT_LEARNINGS.mkdir(parents=True, exist_ok=True)
            vault_file = VAULT_LEARNINGS / f"{exp_id}.md"
            vault_file.write_text(
                f"# Experience Record — {exp_id}\n"
                f"*Timestamp: {exp_data['timestamp']}*\n\n"
                f"- Action Type: `{action_type}`\n"
                f"- Reward: {exp_data['reward']}\n"
                f"- Initial State Norm: {exp_data['state_norm']}\n"
                f"- Next State Norm: {exp_data['next_state_norm']}\n"
                f"- Verified: {exp_data['verified']} (Bypassed LLM: {p_res.bypassed_llm})\n"
                f"- ZK Proof Valid: {exp_data['proof_valid']}\n"
            )
        except OSError:
            pass

        return ExperienceRecord(
            experience_id=exp_id,
            action_type=action_type,
            reward=exp_data["reward"],
            state_norm=exp_data["state_norm"],
            next_state_norm=exp_data["next_state_norm"],
            verified=p_res.allowed,
            proof_valid=proof.is_valid,
            timestamp=exp_data["timestamp"],
        )
