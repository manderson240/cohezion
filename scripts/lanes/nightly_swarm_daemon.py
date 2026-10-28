"""The Night Shift — Autonomous Self-Improving Swarm Daemon.

Runs continuous nightly self-evaluation, code audit verification (AutoHarness & ZKFV),
EVI-gated self-healing, and retrospective knowledge extraction into SurrealDB & Obsidian.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.sleep_framework import SleepFramework
from cohezion.agi.zkfv_compiler import ZKFVCompiler
from cohezion.core.event_bus import EventBus
from cohezion.inference.strix_halo_optimizer import StrixHaloSiliconOptimizer
from cohezion.physics.poincare_manifold import PoincareManifoldTracker
from cohezion.proactive.evi_healer import EVIHealer


logger = logging.getLogger("nightly_swarm_daemon")


class NightlySwarmDaemon:
    """Autonomous self-improving nightly swarm daemon."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self.optimizer = StrixHaloSiliconOptimizer()
        self.healer = EVIHealer()
        self.policy = AutoHarnessPolicy()
        self.zkfv = ZKFVCompiler()
        self.tracker = PoincareManifoldTracker()
        self.event_bus = EventBus()
        self.sleep_framework = SleepFramework(dimension=12, ewc_lambda=100.0)

    async def run_nightly_cycle(self, max_files: int = 5) -> dict[str, Any]:
        """Execute a full autonomous self-healing and verification cycle."""
        logger.info("=== STARTING NIGHTLY SELF-IMPROVING SWARM CYCLE ===")

        # 1. Preflight Fleet Safety Check
        preflight_ok = self.optimizer.verify_wave32_alignment()
        logger.info(
            "Strix Halo Wave32 Alignment: %s", "✅ ALIGNED" if preflight_ok else "⚠️ MISALIGNED"
        )

        # 2. Collect Python Target Files for Verification
        targets = sorted(
            p
            for p in (self.repo_root / "src" / "cohezion").rglob("*.py")
            if "__pycache__" not in str(p) and "test_" not in p.name
        )[:max_files]

        verified_count = 0
        violations_found = []
        zkfv_proofs = []

        for target in targets:
            try:
                code_str = target.read_text(encoding="utf-8")
                # AutoHarness <1 ms AST verification
                ver_res = self.policy.verify_code(code_str)
                if ver_res.valid:
                    verified_count += 1
                else:
                    violations_found.extend(ver_res.violations)

                # ZKFV Polynomial Proof Compilation
                proof = self.zkfv.compile_proof(code_str)
                zkfv_proofs.append(proof)

                # Track Trajectory in Poincaré Manifold
                self.tracker.project_and_track(
                    state_id=target.stem,
                    raw_vector=np.frombuffer(proof.code_hash.encode(), dtype=np.uint8).astype(
                        float
                    ),
                    timestamp=time.time(),
                )

                # Record waking experience in SleepFramework episodic buffer
                hash_bytes = proof.code_hash.encode()[:12]
                state_vec = [float(b) / 255.0 for b in hash_bytes]
                if len(state_vec) < 12:
                    state_vec += [0.0] * (12 - len(state_vec))

                self.sleep_framework.record_experience(
                    task_description=f"Nightly verification of {target.name}",
                    action_sequence=("autoharness_verify", "zkfv_compile", "poincare_track"),
                    state_vector=state_vec,
                    reward=1.0 if ver_res.valid else 0.2,
                    loss=0.0 if ver_res.valid else 0.8,
                    entropy=0.1,
                    session_id="nightly_swarm",
                )
            except Exception as exc:
                logger.warning("Error inspecting %s: %s", target.name, exc)

        # 3. Dynamic EVI Self-Healing Evaluation
        if violations_found:
            healing_action = self.healer.evaluate_healing_candidate(
                component="autoharness_verifier",
                issue_description=f"Detected {len(violations_found)} AST policy violations",
                proposed_remediation="Refactor non-compliant AST constructs to enforce return types and safe exception handling",
                quality_gap=0.4,
                issue_severity=0.8,
                remediation_cost=0.3,
            )
        else:
            healing_action = self.healer.evaluate_healing_candidate(
                component="system_health",
                issue_description="Nightly AST verification clean",
                proposed_remediation="No remediation required",
                quality_gap=0.0,
                issue_severity=0.1,
                remediation_cost=0.1,
                )

        # 4. Offline Sleep Consolidation (Google Research SLEEP Framework)
        sleep_summary = self.sleep_framework.sleep(batch_size=16, num_dreams=6)
        logger.info(
            "Sleep Consolidation: %d experiences consolidated, retention=%.4f, dreams_verified=%d/%d",
            sleep_summary.consolidation.experiences_consolidated,
            sleep_summary.consolidation.knowledge_retention_score,
            sleep_summary.dreaming.dreams_verified,
            sleep_summary.dreaming.dreams_generated,
        )

        # 5. Retrospective Persistence to Obsidian & Kanban
        learnings_dir = Path.home() / "vaults" / "cohezion-vault" / "01-Learnings"
        learnings_dir.mkdir(parents=True, exist_ok=True)
        retro_path = learnings_dir / f"nightly_retro_{int(time.time())}.md"
        retro_content = (
            f"# Nightly Swarm Retrospective\n\n"
            f"- **Timestamp**: {time.asctime()}\n"
            f"- **Files Inspected**: {len(targets)}\n"
            f"- **AutoHarness Verified**: {verified_count}/{len(targets)}\n"
            f"- **ZKFV Proofs Generated**: {len(zkfv_proofs)}\n"
            f"- **Hyperbolic Trajectory Drift**: {self.tracker.get_trajectory_drift():.4f}\n"
            f"- **Self-Healing EVI Score**: {healing_action.evi_score:.4f}\n"
            f"- **Self-Healing Status**: {'APPROVED' if healing_action.approved else 'REJECTED'}\n"
            f"- **Sleep Cycle ID**: {sleep_summary.cycle_id}\n"
            f"- **Knowledge Retention**: {sleep_summary.consolidation.knowledge_retention_score:.4f}\n"
            f"- **EWC Quadratic Penalty**: {sleep_summary.consolidation.ewc_penalty:.4f}\n"
            f"- **Dream Verification Rate**: {sleep_summary.dreaming.verification_rate * 100:.1f}%\n"
            f"- **Counterfactual Discoveries**: {sleep_summary.dreaming.counterfactual_discoveries}\n"
        )
        try:
            retro_path.write_text(retro_content, encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to write Obsidian retrospective: %s", exc)

        summary = {
            "files_inspected": len(targets),
            "verified_count": verified_count,
            "zkfv_proofs": len(zkfv_proofs),
            "trajectory_drift": self.tracker.get_trajectory_drift(),
            "evi_score": healing_action.evi_score,
            "approved": healing_action.approved,
            "sleep_cycle_id": sleep_summary.cycle_id,
            "retention_score": sleep_summary.consolidation.knowledge_retention_score,
            "dreams_verified": sleep_summary.dreaming.dreams_verified,
        }

        logger.info("=== NIGHTLY SWARM CYCLE COMPLETED SUCCESSFULLY ===")
        return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Autonomous Nightly Swarm Daemon")
    ap.add_argument("--files", type=int, default=5, help="Number of files to verify per pass")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    daemon = NightlySwarmDaemon()
    asyncio.run(daemon.run_nightly_cycle(max_files=args.files))


if __name__ == "__main__":
    import numpy as np

    main()
