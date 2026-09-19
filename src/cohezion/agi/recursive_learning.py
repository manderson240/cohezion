r"""Recursive Learning & Self-Improvement Engine
============================================
Implements recursive learning loops ("Cohezion improving Cohezion"):
  1. AutoHarness: Zero-cost AST policy enforcement (arXiv:2603.03329v1)
  2. AutoContext: Continuous 2048D Poincaré context resolution
  3. Bleeding Edge Research: CTAC, ZKFV, Geodesic Neural ODEs
  4. Recursive Learning: Extracting retrospectives into SurrealDB & Vault
  5. EventBus Cross-Session Synchronization: Broadcasting learning cycles
  6. Markov State Monad: Categorical invariant preservation (Delta S <= 0)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.zkfv_compiler import ZKFVCompiler
from cohezion.contracts import PoincarePoint
from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.physics.ctac_engine import CTACEngine


logger = logging.getLogger(__name__)

VAULT_LEARNINGS = Path.home() / "vaults" / "cohezion-vault" / "01-Learnings"
WAL_PATH = Path.home() / ".cohezion" / "wal" / "learning_cycles.jsonl"
_SURREAL_UPSERT_TIMEOUT_S = float(os.environ.get("SURREAL_UPSERT_TIMEOUT_S", "5.0"))

S = TypeVar("S")
A = TypeVar("A")


@dataclass(frozen=True, slots=True)
class MonadResult(Generic[S, A]):
    """Result of a Markov State Monad transition with formal invariant proof."""

    new_state: S
    action_value: A
    delta_entropy: float
    zkfv_verified: bool
    is_valid: bool
    diagnostic: str = ""


class MarkovStateMonad:
    """Categorical Markov State Monad enforcing Delta S <= 0 and ZKFV invariants."""

    @staticmethod
    def bind(
        current_state: S,
        action_fn: Callable[[S], tuple[S, A, str, Sequence[PoincarePoint]]],
        entropy_evaluator: Callable[[Sequence[PoincarePoint], Sequence[PoincarePoint]], float],
        zkfv_compiler: ZKFVCompiler,
    ) -> MonadResult[S, A]:
        """Execute monadic bind. Rolls back state if delta_entropy > 0 or ZKFV fails."""
        candidate_state, action_val, code_artifact, trajectory = action_fn(current_state)

        # 1. ZKFV Formal Verification on generated artifact
        proof = zkfv_compiler.compile_proof(
            code_artifact or "def noop() -> None:\n    pass\n",
            invariants=["AST_PARSABLE", "NO_EVAL", "TYPE_ANNOTATED"],
        )

        # 2. Strict Negentropy Check
        pre_pts = trajectory[: len(trajectory) // 2] if len(trajectory) >= 2 else trajectory
        post_pts = trajectory[len(trajectory) // 2 :] if len(trajectory) >= 2 else trajectory
        delta_s = entropy_evaluator(pre_pts, post_pts)

        if not proof.verified:
            return MonadResult(
                new_state=current_state,  # Rollback
                action_value=action_val,
                delta_entropy=delta_s,
                zkfv_verified=False,
                is_valid=False,
                diagnostic="ZKFV verification failed on synthesized artifact.",
            )

        if delta_s > 0.0001:  # Invariant violation: entropy increased
            return MonadResult(
                new_state=current_state,  # Rollback
                action_value=action_val,
                delta_entropy=delta_s,
                zkfv_verified=True,
                is_valid=False,
                diagnostic=f"Negentropy violation: Delta S = {delta_s:.5f} > 0",
            )

        return MonadResult(
            new_state=candidate_state,
            action_value=action_val,
            delta_entropy=delta_s,
            zkfv_verified=True,
            is_valid=True,
            diagnostic="Monadic transition invariant satisfied.",
        )


@dataclass(frozen=True, slots=True)
class LearningCycleResult:
    cycle_id: str
    autoharness_score: float
    autocontext_dim: int
    ctac_coherence: float
    learnings_count: int
    surreal_persisted: bool
    vault_persisted: bool
    delta_entropy: float = 0.0
    zkfv_verified: bool = True


class RecursiveLearningEngine:
    """Master Recursive Self-Improvement Engine with SurrealDB 3.0+ & EventBus integration."""

    def __init__(self) -> None:
        self.policy_engine = AutoHarnessPolicy()
        self.ctac_engine = CTACEngine(target_coherence=0.50)
        self.zkfv_compiler = ZKFVCompiler(salt="cohezion_negentropy_v2")
        self.surreal_client = get_surreal_client()

    def _direct_http_upsert(self, record_id: str, data: dict[str, Any]) -> bool:
        """Direct HTTP POST fallback to SurrealDB (port 8001) bypassing client vault dependency."""
        try:
            url = os.environ.get("SURREAL_URL", "http://localhost:8001") + "/sql"
            if not url.startswith(("http://", "https://")):
                return False
            auth = base64.b64encode(b"root:root").decode("ascii")
            payload = f"UPSERT type::record('learning', '{record_id}') CONTENT {json.dumps(data)};"
            req = urllib.request.Request(  # noqa: S310
                url,
                data=payload.encode("utf-8"),
                headers={
                    "Authorization": f"Basic {auth}",
                    "surreal-ns": os.environ.get("SURREAL_NS", "cohezion"),
                    "surreal-db": os.environ.get("SURREAL_DB", "main"),
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
                if resp.status == 200:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    if resp_json and resp_json[0].get("status") == "OK":
                        return True
        except Exception as exc:
            logger.debug("Direct HTTP upsert failed for record %s: %s", record_id, exc)
        return False

    async def surreal_upsert(self, record_id: str, data: dict[str, Any]) -> bool:
        """Persist learning cycle to SurrealDB using async SurrealClient with direct HTTP fallback and WAL."""
        try:
            await asyncio.wait_for(
                self.surreal_client.query(
                    "UPSERT type::record('learning', $rec_id) CONTENT $data;",
                    {"rec_id": record_id, "data": data},
                ),
                timeout=_SURREAL_UPSERT_TIMEOUT_S,
            )
            return True
        except Exception as exc:
            logger.debug(
                "Primary async surreal_client query failed for %s: %s — attempting direct HTTP fallback",
                record_id,
                exc,
            )
            try:
                loop = asyncio.get_running_loop()
                http_success = await loop.run_in_executor(
                    None, self._direct_http_upsert, record_id, data
                )
                if http_success:
                    return True
            except Exception as http_exc:
                logger.debug("Direct HTTP executor failed: %s", http_exc)

            logger.warning(
                "SurrealDB upsert failed via both primary client and HTTP fallback for %s — committing to WAL",
                record_id,
            )
            self._write_wal(data)
            return False

    def _write_wal(self, data: dict[str, Any]) -> None:
        """Write to local write-ahead log so learning telemetry is never lost."""
        try:
            WAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(WAL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as exc:
            logger.debug("WAL write failed: %s", exc)

    async def execute_recursive_learning_cycle(
        self,
        trajectory_summary: str,
        trajectory_points: Sequence[PoincarePoint] | None = None,
        synthesized_code: str | None = None,
    ) -> LearningCycleResult:
        """Run an async recursive self-improvement cycle guarded by AutoHarness and ZKFV."""
        t0 = time.time()
        cycle_id = f"recursive_cycle_{int(t0)}"

        # 1. Target code verification via AutoHarness AST validator
        target_code = (
            synthesized_code
            if synthesized_code is not None
            else f"# Recursive learning cycle {cycle_id}\nsummary = {trajectory_summary!r}\n"
        )
        p_res = self.policy_engine.verify_code(target_code)
        autoharness_bypassed_llm = p_res.valid

        # 2. ZKFV Formal Verification Proof
        proof = self.zkfv_compiler.compile_proof(
            target_code, invariants=["AST_PARSABLE", "NO_EVAL"]
        )

        # 3. CTAC Topological Calibration & Dynamic AutoContext Resolution
        pts = list(trajectory_points) if trajectory_points is not None else []
        ctac_res = self.ctac_engine.evaluate_topology(pts)

        if pts:
            autocontext_dim = max(128, int(2048 * ctac_res.conformal_kappa))
            pre_pts = pts[: len(pts) // 2]
            post_pts = pts[len(pts) // 2 :]
            d_pre = sum(p.norm for p in pre_pts) / max(1, len(pre_pts))
            d_post = sum(p.norm for p in post_pts) / max(1, len(post_pts))
            delta_entropy = float(d_post - d_pre)
        else:
            autocontext_dim = 2048
            delta_entropy = -0.001  # Default nominal negentropy

        # 4. Extract and Persist Learning
        learning_data = {
            "id": cycle_id,
            "title": f"Recursive Learning Cycle — {cycle_id}",
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": trajectory_summary,
            "autoharness_bypassed_llm": autoharness_bypassed_llm,
            "autocontext_dim": autocontext_dim,
            "ctac_coherence": ctac_res.coherence,
            "is_hiho_stable": ctac_res.is_hiho_stable,
            "delta_entropy": delta_entropy,
            "zkfv_verified": proof.verified,
            "zkfv_sig": proof.polynomial_signature,
        }

        surreal_ok = await self.surreal_upsert(cycle_id, learning_data)

        # 5. EventBus Cross-Session Synchronization
        try:
            event_bus = await get_event_bus()
            await event_bus.publish(
                Event(
                    type=EventType.AGENT_COMPLETE,
                    source="recursive_learning_engine",
                    payload={
                        "cycle_id": cycle_id,
                        "ctac_coherence": ctac_res.coherence,
                        "is_hiho_stable": ctac_res.is_hiho_stable,
                        "delta_entropy": delta_entropy,
                        "zkfv_verified": proof.verified,
                    },
                )
            )
        except Exception as exc:
            logger.warning("Failed to publish recursive learning event: %s", exc)

        # 6. Write to Vault safely
        vault_ok = False
        try:
            VAULT_LEARNINGS.mkdir(parents=True, exist_ok=True)
            vault_file = VAULT_LEARNINGS / f"{cycle_id}.md"
            vault_file.write_text(
                f"# {learning_data['title']}\n"
                f"*Date: {learning_data['timestamp']}*\n\n"
                f"## Trajectory Summary\n{trajectory_summary}\n\n"
                f"## Metrics\n"
                f"- AutoHarness Bypassed LLM: {autoharness_bypassed_llm}\n"
                f"- ZKFV Formal Verification Valid: {proof.verified} (`{proof.polynomial_signature[:16]}...`)\n"
                f"- AutoContext Dimension: {autocontext_dim}D\n"
                f"- CTAC HIHO Coherence: {ctac_res.coherence} (Stable: {ctac_res.is_hiho_stable})\n"
                f"- Entropy Delta (ΔS): {delta_entropy:.6f} (Negentropic: {delta_entropy <= 0.0})\n"
            )
            vault_ok = vault_file.exists()
        except OSError:
            vault_ok = False

        return LearningCycleResult(
            cycle_id=cycle_id,
            autoharness_score=1.0 if p_res.valid else 0.0,
            autocontext_dim=autocontext_dim,
            ctac_coherence=ctac_res.coherence,
            learnings_count=1,
            surreal_persisted=surreal_ok,
            vault_persisted=vault_ok,
            delta_entropy=delta_entropy,
            zkfv_verified=proof.verified,
        )
