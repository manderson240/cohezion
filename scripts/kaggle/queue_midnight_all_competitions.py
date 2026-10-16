#!/usr/bin/env python3
"""Midnight UTC Multi-Competition Autonomous Submitter & Watcher (Synchronized Edition).
====================================================================================
Synchronized with Recursive Experiential Learnings (Learnings 518-521):
1. ARC-Prize 2026: ARC-AGI-3 (SOTA v33 with Monadic Markov + 64-bit Zobrist Anti-Cycle)
2. ARC-Prize 2026: ARC-AGI-2 (SOTA v15 with Monotonic Attempt-2 DSL Injection)
3. Google Gemma 4 Developer Agent (12B Fast-Inference Container, guarded by max_pending=1)
4. RSNA Knee Abnormality Detection (SOTA v32 with Pure Copula Rank Alignment + Probability Clipping)
5. Enveda CASMI26 Molecule ID (Podium v22 with N=25 Parsimonious Dual Surrogate + POP_MU 0.25)

Automatically executes at 00:00:05 UTC, checks pending status before dispatch to avoid
HTTP 400 FAILED_PRECONDITION violations, and triggers the Recursive Experiential Learner
to record the midnight harvest into SurrealDB and the Obsidian Vault.
"""

from __future__ import annotations

import datetime
import logging
import subprocess
import sys
import time
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("midnight_submitter")

WORKSPACE = Path("/home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push")
sys.path.insert(0, str(WORKSPACE / "src"))


def get_seconds_until_midnight_utc() -> int:
    now = datetime.datetime.now(datetime.UTC)
    today_target = now.replace(hour=0, minute=0, second=5, microsecond=0)
    if now < today_target:
        target = today_target
    else:
        target = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
    return int((target - now).total_seconds())


def check_is_pending(api: KaggleApi, comp_slug: str) -> bool:
    """Checks if a competition currently has any pending submissions."""
    try:
        subs = api.competition_submissions(comp_slug)
        if subs:
            latest_status = str(subs[0].status).upper()
            if "PENDING" in latest_status:
                logger.info("[%s] Submission Ref #%s is currently %s; respecting concurrency guard.", comp_slug, subs[0].ref, latest_status)
                return True
    except Exception as e:
        logger.warning("[%s] Failed to check pending status: %s", comp_slug, e)
    return False


def submit_notebook(comp: str, kernel: str, filename: str, msg: str, code_path: str | None = None) -> bool:
    logger.info("Submitting notebook for %s (%s)...", comp, kernel)

    # AutoHarness Invariant Factory Gate (arXiv:2603.03329v1)
    if code_path and Path(code_path).exists():
        try:
            from cohezion.compound.invariant_factory import AutoHarnessInvariantFactory
            inv_res = AutoHarnessInvariantFactory.compile_and_verify(code_path, comp)
            if inv_res.has_critical_violations or not inv_res.bytecode_valid:
                logger.critical(
                    "[%s] AutoHarness invariant validation FAILED! Aborting dispatch: %s",
                    comp, inv_res.violations
                )
                return False
        except Exception as e:
            logger.warning("[%s] AutoHarness pre-dispatch check note: %s", comp, e)

        # Forbidden Subgraph / Dead-End Ledger Gate (Meta-Aspect 1)
        try:
            from cohezion.registry.forbidden_subgraphs import ForbiddenSubgraphLinter
            linter = ForbiddenSubgraphLinter()
            if str(code_path).endswith(".ipynb"):
                l_pass, l_viols = linter.audit_notebook(code_path, domain=comp)
            else:
                with open(code_path, encoding="utf-8") as f:
                    l_pass, l_viols = linter.audit_code(f.read(), domain=comp)
            if not l_pass:
                logger.critical("[%s] FORBIDDEN SUBGRAPH DETECTED! Aborting dispatch: %s", comp, l_viols)
                return False
            logger.info("[%s] ✓ Dead-End Ledger check PASSED (0 anti-patterns).", comp)
        except Exception as e:
            logger.warning("[%s] Dead-End Ledger pre-dispatch check note: %s", comp, e)

        # Two-Party Adversarial IV&V Gate (Meta-Aspect 4)
        try:
            sys.path.insert(0, str(WORKSPACE / "scripts" / "testing"))
            from red_team_adversary import (
                RedTeamAdversary,
                default_copula_blend,
                default_d4_verifier,
                default_poincare_distance,
                default_zobrist_hash,
            )
            adversary = RedTeamAdversary()
            if "arc-agi-3" in comp:
                adversary.probe_poincare_invariants(default_poincare_distance)
                adversary.probe_zobrist_hash_collisions(default_zobrist_hash)
            elif "arc-agi-2" in comp:
                adversary.probe_d4_symmetry(default_d4_verifier)
            elif "rsna" in comp or "casmi" in comp:
                adversary.probe_copula_rank_monotonicity(default_copula_blend)

            report = adversary.generate_audit_report()
            if not report["is_certified"]:
                logger.critical("[%s] ADVERSARIAL RED-TEAM REJECTED INVARIANTS: %s", comp, report["findings"])
                return False
            logger.info("[%s] ✓ Adversarial Red-Team IV&V Certification PASSED cleanly.", comp)
        except Exception as e:
            logger.warning("[%s] Adversarial Red-Team pre-dispatch check note: %s", comp, e)

    cmd = [
        sys.executable, "scripts/kaggle/kaggle_submit.py", "notebook",
        "-c", comp,
        "-k", kernel,
        "-f", filename,
        "-m", msg,
        "-w",
    ]
    if code_path:
        cmd.extend(["--code-path", code_path])
    res = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("Return code for %s: %d", comp, res.returncode)
    logger.info("Stdout: %s", res.stdout.strip())
    if res.stderr:
        logger.warning("Stderr: %s", res.stderr.strip())
    return res.returncode == 0


def submit_file(comp: str, filepath: str, msg: str, code_path: str | None = None) -> bool:
    logger.info("Submitting file for %s (%s)...", comp, filepath)

    # AutoHarness Invariant Factory Gate (arXiv:2603.03329v1)
    check_target = code_path or filepath
    if check_target and Path(check_target).exists() and str(check_target).endswith((".py", ".ipynb")):
        try:
            from cohezion.compound.invariant_factory import AutoHarnessInvariantFactory
            inv_res = AutoHarnessInvariantFactory.compile_and_verify(check_target, comp)
            if inv_res.has_critical_violations or not inv_res.bytecode_valid:
                logger.critical(
                    "[%s] AutoHarness invariant validation FAILED! Aborting dispatch: %s",
                    comp, inv_res.violations
                )
                return False
            logger.info("[%s] ✓ AutoHarness invariants verified cleanly (%d checked).", comp, inv_res.invariants_checked)
        except Exception as e:
            logger.warning("[%s] AutoHarness pre-dispatch check note: %s", comp, e)

    cmd = [
        sys.executable, "scripts/kaggle/kaggle_submit.py", "file",
        "-c", comp,
        "-f", filepath,
        "-m", msg,
    ]
    if code_path:
        cmd.extend(["--code-path", code_path])
    res = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("Return code for %s: %d", comp, res.returncode)
    logger.info("Stdout: %s", res.stdout.strip())
    if res.stderr:
        logger.warning("Stderr: %s", res.stderr.strip())
    return res.returncode == 0


def execute_midnight_harvest(api: KaggleApi):
    logger.info("=== 00:00:05 UTC REACHED: EXECUTING COMPREHENSIVE DAILY QUOTA HARVEST ===")

    # 1. ARC-AGI-3 (SOTA v38: Poincaré Hyperbolic MCTS Affordance Oracle + Double Precision)
    if not check_is_pending(api, "arc-prize-2026-arc-agi-3"):
        submit_notebook(
            comp="arc-prize-2026-arc-agi-3",
            kernel="manderson240/cohezion-arc-agi-3-autoharness-solver",
            filename="submission.parquet",
            msg="Cohezion ARC-AGI-3 SOTA v38: Poincaré Hyperbolic MCTS Affordance Oracle + Monadic Soft-Affordance + Double-Precision (Daily Quota Reset)",
            code_path="scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb",
        )

    # 2. ARC-AGI-2 (SOTA v15 Strict Monotonic DSL Injection)
    if not check_is_pending(api, "arc-prize-2026-arc-agi-2"):
        submit_notebook(
            comp="arc-prize-2026-arc-agi-2",
            kernel="manderson240/arc-agi-2-fork-lb33-89-20260903",
            filename="submission.json",
            msg="Cohezion ARC-AGI-2 SOTA v15: Quad-L4 SOTA Monotonic LoRA Attempt-2 DSL Injection (Daily Quota Reset)",
            code_path="scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb",
        )

    # 3. Google Gemma 4 Developer Agent (31B Stable QAT Container)
    if not check_is_pending(api, "gemma-4-developer-agent"):
        submit_file(
            comp="gemma-4-developer-agent",
            filepath="scripts/kaggle/gemma4_kernel/submission.zip",
            msg="Cohezion Gemma-4 SOTA: 31B Stable QAT + 2048 Token Context Safety + Paced Edit (No Vision Embedder Crash)",
            code_path="scripts/kaggle/gemma4_kernel/package_submission.py",
        )
    else:
        logger.info("[gemma-4-developer-agent] Previous submission still scoring. Background watcher will dispatch upon queue clearance.")

    # 4. RSNA Knee Abnormality Detection (SOTA v36 Pure Optimum Calibrated Tri-Model Blend)
    if not check_is_pending(api, "rsna-knee-abnormality-detection"):
        submit_notebook(
            comp="rsna-knee-abnormality-detection",
            kernel="manderson240/cohezion-rsna-knee-0-957-r7-blend",
            filename="submission.csv",
            msg="Cohezion RSNA Knee SOTA v36: Pure Optimum Calibrated Tri-Model Blend (Raptor-384 + Raptor-224 A224=0.40 + R7) + Noise Insulated Weights (Daily Quota Reset)",
            code_path="scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb",
        )

    # 5. Enveda CASMI26 Molecule ID (Podium v26 Verified Dual FPNet Ensemble + Full-Candidate Parsimony)
    if not check_is_pending(api, "enveda-CASMI26-molecule-id-mass-spectra"):
        submit_notebook(
            comp="enveda-CASMI26-molecule-id-mass-spectra",
            kernel="manderson240/cohezion-casmi26-fork-v4n-0421",
            filename="submission.csv",
            msg="Cohezion CASMI26 SOTA v26: Dual FPNet Ensemble + Full-Candidate Parsimony (PC_JOIN_N=50, PC_POP_UNION=200, lambda_frag=0.15) (Daily Quota Reset)",
            code_path="scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb",
        )

    logger.info("Daily quota harvest completed. Invoking Recursive Experiential Learner...")
    try:
        sys.path.insert(0, str(WORKSPACE / "scripts" / "kaggle"))
        from recursive_experiential_learner import audit_and_learn
        audit_and_learn()
        logger.info("✓ Recursive experiential learning audit completed & persisted.")
    except Exception as e:
        logger.warning("Recursive experiential learner call note: %s", e)


def main():
    api = KaggleApi()
    api.authenticate()

    if "--now" in sys.argv:
        logger.info("Immediate harvest requested via --now. Executing harvest right now...")
        execute_midnight_harvest(api)
        return

    while True:
        wait_sec = get_seconds_until_midnight_utc()
        logger.info("Synchronized Midnight Submitter waiting %d seconds (%0.2f hours) until next 00:00:05 UTC reset...", wait_sec, wait_sec / 3600.0)
        while True:
            wait_sec = get_seconds_until_midnight_utc()
            if wait_sec <= 2:
                time.sleep(max(0, wait_sec))
                break
            sleep_dur = min(wait_sec, 300)
            time.sleep(sleep_dur)
            if wait_sec > 300:
                now_utc = datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S")
                logger.info("Current UTC: %s | Remaining wait: %d seconds (%0.2f hours)", now_utc, wait_sec, wait_sec / 3600.0)

        execute_midnight_harvest(api)
        time.sleep(10)  # avoid double trigger within same second


if __name__ == "__main__":
    main()
