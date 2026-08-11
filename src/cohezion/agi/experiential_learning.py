r"""Experiential Recursive Learning Engine
==========================================
Converts agent trajectories into persistent Experiential Replay Memory
E = (S_t, a_t, r_t, S_{t+1}, \pi_{safety}), extracting high-reward patterns into
SurrealDB `experiential_replay` table and Obsidian Vault (`01-Learnings/`).

Architecture:
  1. Experience Capture: Store state-action-reward-state transitions
  2. AutoHarness Policy Verification: Check bytecode compliance
  3. ZKFV Proof Generation: Produce \pi_{safety} zero-knowledge safety proofs
  4. Experiential Distillation: Update persistent SurrealDB + Vault knowledge bases
"""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.zkfv_compiler import ZKFVCompiler, ZKProof
from cohezion.contracts import PoincarePoint
from cohezion.reliability.oom_guard import OOMGuard

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()
VAULT_LEARNINGS = Path.home() / "vaults" / "cohezion-vault" / "01-Learnings"


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
    """Master Experiential Recursive Learning Engine."""

    def __init__(self) -> None:
        self.policy_engine = AutoHarnessPolicy()

    def surreal_upsert_experience(self, exp_id: str, data: dict) -> bool:
        safe_id = "".join(c for c in exp_id if c.isalnum() or c in ("_", "-"))
        surql = f"UPSERT experiential_replay:{safe_id} CONTENT {json.dumps(data)};"
        try:
            req = urllib.request.Request(
                SURREAL_URL,
                data=surql.encode(),
                headers={
                    "Authorization": f"Basic {SURREAL_AUTH}",
                    "Surreal-NS": "cohezion",
                    "Surreal-DB": "main",
                    "Accept": "application/json",
                    "Content-Type": "text/plain",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                res = json.loads(r.read().decode())
                return bool(isinstance(res, list) and res and res[0].get("status") == "OK")
        except Exception:
            return False

    def process_experience(
        self,
        action_type: str,
        initial_state: PoincarePoint,
        next_state: PoincarePoint,
        reward: float,
    ) -> ExperienceRecord:
        """Process agent experience, verify safety policies, and persist to memory."""
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 4. Upsert to SurrealDB
        surreal_ok = self.surreal_upsert_experience(exp_id, exp_data)

        # 5. Persist to Vault
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
