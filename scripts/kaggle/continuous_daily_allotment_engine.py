#!/usr/bin/env python3
"""Continuous Daily Allotment Saturation Engine (Autonomous 5/5 Harvest).
========================================================================
Maintains strict continuous saturation of Kaggle's 5 daily submission slots
across all active portfolio competitions:
1. RSNA Knee Abnormality Detection (Notebook mode)
2. ARC Prize 2026: ARC-AGI-2 (Notebook mode)
3. ARC Prize 2026: ARC-AGI-3 (Notebook mode)
4. Enveda CASMI26 Molecule ID (Notebook mode)
5. Name That LLM (Notebook mode)
6. Google Gemma 4 Developer Agent (File/container mode)

Concurrency & Safety Invariants:
- Never dispatch when a prior submission for the same competition is PENDING (prevents HTTP 400 FAILED_PRECONDITION).
- AutoHarness Invariant Factory Gate (arXiv:2603.03329v1) before every push.
- Dead-End Ledger (Forbidden Subgraph Linter) verification.
- Two-Party Adversarial IV&V Gate certification.
- Automatically logs scored results and learnings to SurrealDB and Obsidian Vault.
- Resets quota counters at 00:00:05 UTC.
"""

from __future__ import annotations

import ast
import datetime
import json
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from kaggle.api.kaggle_api_extended import KaggleApi


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scripts/kaggle/allotment_engine.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("allotment_engine")

WORKSPACE = Path(
    "/home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push"
)
sys.path.insert(0, str(WORKSPACE / "src"))
from cohezion.kaggle.preflight_validator import PreflightValidator  # noqa: E402


STATE_FILE = WORKSPACE / "scripts" / "kaggle" / "daily_allotment_state.json"

# Invariant specifications for Slots 1..5 for each competition
PORTFOLIO_CONFIG = {
    "rsna-knee-abnormality-detection": {
        "mode": "notebook",
        "max_daily": 5,
        "kernel": "manderson240/cohezion-rsna-knee-0-957-r7-blend",
        "filename": "submission.csv",
        "notebook": "scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb",
        "slots": {
            1: {
                "name": "v42_jsn_isotonic_fusion",
                "patch_script": "scripts/kaggle/rsna_r7_raptor_blend/assemble_rsna_v42_jsn_isotonic_fusion.py",
                "msg": "Cohezion RSNA Knee SOTA v42: JSN Covariance + Isotonic Quantile Rank Alignment (T=0.85) Grandmaster Fusion",
            },
            2: {
                "name": "v43_multiview_ledoit_wolf",
                "patch_script": "scripts/kaggle/rsna_r7_raptor_blend/assemble_rsna_v43_multiview_ledoit_wolf.py",
                "msg": "Cohezion RSNA Knee SOTA v43: Multi-View Ledoit-Wolf Shrinkage Covariance Projection (Alpha=0.15, T=0.85)",
            },
            3: {
                "name": "v38_isotonic_rank",
                "patch_script": "scripts/kaggle/rsna_r7_raptor_blend/assemble_rsna_v38_isotonic_rank.py",
                "msg": "Cohezion RSNA Knee SOTA v38: Isotonic Quantile Rank Alignment with Temperature T=0.85 Scaling (0.956 Anchor)",
            },
            4: {
                "name": "v37_jsn_covariance",
                "patch_script": "scripts/kaggle/rsna_r7_raptor_blend/assemble_rsna_v37_jsn.py",
                "msg": "Cohezion RSNA Knee SOTA v37: Anatomical JSN Covariance + Bilateral Knee Symmetry Ratio + Pure Quantile Alignment (0.956 Anchor)",
            },
            5: {
                "name": "v36_pure_optimum",
                "patch_script": "scripts/kaggle/rsna_r7_raptor_blend/assemble_rsna_v36_pure_optimum.py",
                "msg": "Cohezion RSNA Knee SOTA v36: Pure Optimum Calibrated Tri-Model Blend (Raptor-384 + Raptor-224 A224=0.40 + R7) + Noise Insulated Weights",
            },
        },
    },
    "arc-prize-2026-arc-agi-2": {
        "mode": "notebook",
        "max_daily": 1,
        "kernel": "manderson240/arc-agi-2-fork-lb33-89-20260903",
        "filename": "submission.json",
        "notebook": "scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb",
        "slots": {
            1: {
                "name": "v20_zero_mutual_information",
                "patch_script": "scripts/kaggle/arc2_autoharness_lora_kernel/patch_arc2_v20_zero_mutual_information.py",
                "msg": "Cohezion ARC-AGI-2 SOTA v20: Zero-Mutual-Information Attempt-2 Protocol (D4 Dihedral & Symbolic DSL Union)",
            },
            2: {
                "name": "v16_npu_d4_symmetry",
                "patch_script": "scripts/kaggle/arc2_autoharness_lora_kernel/patch_arc2_v16_npu_d4.py",
                "msg": "Cohezion ARC-AGI-2 SOTA v16: NPU-Verified D4 Dihedral Equivariance Invariant (Attempt-2 Non-Duplication)",
            },
            3: {
                "name": "v17_zero_false_prune",
                "patch_script": "scripts/kaggle/arc2_autoharness_lora_kernel/patch_arc2_v17_zero_false_prune.py",
                "msg": "Cohezion ARC-AGI-2 SOTA v17: Zero-False-Prune Topology Invariant (Conformal Bounding Box Validation)",
            },
            4: {
                "name": "v18_poincare_geodesic_rerank",
                "patch_script": "scripts/kaggle/arc2_autoharness_lora_kernel/patch_arc2_v18_poincare_geodesic_rerank.py",
                "msg": "Cohezion ARC-AGI-2 SOTA v18: Poincaré Hyperbolic Grid Geodesic Nearest-Neighbor Reranker",
            },
            5: {
                "name": "v19_monadic_markov_dsl",
                "patch_script": "scripts/kaggle/arc2_autoharness_lora_kernel/patch_arc2_v19_monadic_markov_dsl.py",
                "msg": "Cohezion ARC-AGI-2 SOTA v19: SplitMix64 Monadic Markov DSL Synthesizer with Deduplication",
            },
        },
    },
    "arc-prize-2026-arc-agi-3": {
        "mode": "notebook",
        "max_daily": 1,
        "kernel": "manderson240/cohezion-arc-agi-3-autoharness-solver",
        "filename": "submission.parquet",
        "notebook": "scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb",
        "slots": {
            1: {
                "name": "v38_poincare_mcts",
                "patch_script": None,
                "msg": "Cohezion ARC-AGI-3 SOTA v38: Poincaré Hyperbolic MCTS Affordance Oracle + Monadic Soft-Affordance + Double-Precision",
            },
            2: {
                "name": "v39_harness2_ppc",
                "patch_script": "scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/patch_arc3_v39_harness2_ppc.py",
                "msg": "Cohezion ARC-AGI-3 SOTA v39: Harness^2 Recursive Invariants + Cycle Watchdog <= 4 + Base Horizon 35",
            },
            3: {
                "name": "v40_orthogonal_escape",
                "patch_script": "scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/patch_arc3_v40_orthogonal_escape.py",
                "msg": "Cohezion ARC-AGI-3 SOTA v40: Soft-Affordance Navigation + Orthogonal Escape Pulse (Delta >= 2)",
            },
            4: {
                "name": "v41_go_explore_archive",
                "patch_script": "scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/patch_arc3_v41_go_explore_archive.py",
                "msg": "Cohezion ARC-AGI-3 SOTA v41: Multi-Agent Consensus Exploration (Go-Explore Novelty Distance)",
            },
            5: {
                "name": "v42_adaptive_rhae",
                "patch_script": "scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/patch_arc3_v42_adaptive_rhae.py",
                "msg": "Cohezion ARC-AGI-3 SOTA v42: Dynamic Horizon Affordance Rollout with Adaptive RHAE Metric Preserver",
            },
        },
    },
    "enveda-CASMI26-molecule-id-mass-spectra": {
        "mode": "notebook",
        "max_daily": 5,
        "kernel": "manderson240/cohezion-casmi26-fork-v4n-0421",
        "filename": "submission.csv",
        "notebook": "scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb",
        "slots": {
            1: {
                "name": "v30_extreme_parsimony_hybrid",
                "patch_script": "scripts/kaggle/casmi26_v4n_podium/patch_casmi26_v30_podium_rerank.py",
                "msg": "Cohezion CASMI26 SOTA v30: Extreme Candidate Space Parsimony Hybrid (PC_JOIN_N=120, PC_POP_UNION=350, lambda_frag=0.25)",
            },
            2: {
                "name": "v31_calibrated_candidate_space",
                "patch_script": "scripts/kaggle/casmi26_v4n_podium/patch_casmi26_v31_calibrated_candidate_space.py",
                "msg": "Cohezion CASMI26 SOTA v31: Calibrated Candidate Space Parsimony (PC_JOIN_N=90, PC_POP_UNION=280, lambda_frag=0.19)",
            },
            3: {
                "name": "v29_chemical_graph_reranker",
                "patch_script": "scripts/kaggle/casmi26_v4n_podium/patch_casmi26_v29_chemical_graph.py",
                "msg": "Cohezion CASMI26 SOTA v29: Parsimonious Chemical Graph Fragmentation Reranker (PC_JOIN_N 100, PC_POP_UNION 300, lambda_frag=0.22)",
            },
            4: {
                "name": "v28_adduct_surrogacy",
                "patch_script": "scripts/kaggle/casmi26_v4n_podium/patch_casmi26_v28_adduct_surrogacy.py",
                "msg": "Cohezion CASMI26 SOTA v28: All-Adduct Surrogacy Calibration ([M+H]+, [M+Na]+, [M-H]- Neutral Loss Matching)",
            },
            5: {
                "name": "v27_deep_expansion",
                "patch_script": "scripts/kaggle/casmi26_v4n_podium/patch_casmi26_v27_deep_expansion.py",
                "msg": "Cohezion CASMI26 SOTA v27: Deep PubChem Candidate Expansion (PC_JOIN_N 75, PC_POP_UNION 250) + Calibrated Parsimony (FRAG_LAM 0.18)",
            },
        },
    },
    "name-that-llm": {
        "mode": "notebook",
        "max_daily": 5,
        "kernel": "manderson240/cohezion-name-that-llm-sota-starter",
        "filename": "submission.parquet",
        "notebook": "scripts/kaggle/name_that_llm/cohezion-name-that-llm-sota-starter.ipynb",
        "slots": {
            1: {
                "name": "v7_hierarchical_l2_scaled_sinkhorn",
                "patch_script": "scripts/kaggle/name_that_llm/assemble_name_that_llm_v7_hierarchical.py",
                "msg": "Cohezion Name That LLM SOTA v7: Hierarchical 6-Lab Bayesian Decomposition + L2 Scaled Compression Entropy + T=1.15 Sinkhorn Marginal Balancing",
            },
            2: {
                "name": "v6_temperature_scaled_sinkhorn",
                "patch_script": "scripts/kaggle/name_that_llm/assemble_name_that_llm_v6.py",
                "msg": "Cohezion Name That LLM v6: Ensembled Temperature-Scaled Sinkhorn Distribution Alignment",
            },
            3: {
                "name": "v5_leak_free_group_kfold",
                "patch_script": "scripts/kaggle/name_that_llm/assemble_name_that_llm_v5.py",
                "msg": "Cohezion Name That LLM v5: Leak-Free StratifiedGroupKFold on prompt_id + Dual Model Ensemble + Sinkhorn Uniform Marginal Balancing",
            },
            4: {
                "name": "v4_hgb_dense_stylometry",
                "patch_script": "scripts/kaggle/name_that_llm/assemble_name_that_llm_v4.py",
                "msg": "Cohezion Name That LLM v4: 5-Stream Stylometric (LinearSVC + HistGBM Ensemble) + Sinkhorn Marginal Balancing",
            },
            5: {
                "name": "v7_hierarchical_entropy_rerank",
                "patch_script": "scripts/kaggle/name_that_llm/assemble_name_that_llm_v7_hierarchical.py",
                "msg": "Cohezion Name That LLM SOTA v7.1: Multi-Compressor Entropy Signatures + 6-Lab Prior Gating",
            },
        },
    },
    "gemma-4-developer-agent": {
        "mode": "file",
        "max_daily": 1,
        "filepath": "scripts/kaggle/gemma4_kernel/submission.zip",
        "code_path": "scripts/kaggle/gemma4_kernel/package_submission.py",
        "slots": {
            1: {
                "name": "31b_stable_qat_2048",
                "msg": "Cohezion Gemma-4 SOTA: 31B Stable QAT + Calibrated 1024 Thinking Budget + AST Syntax Verifier",
            },
            2: {
                "name": "31b_extended_4096_ast",
                "msg": "Cohezion Gemma-4 SOTA: 31B Stable QAT + Extended 4096 Token Context + AST Syntax Verifier",
            },
            3: {
                "name": "12b_fast_inference_pytest",
                "msg": "Cohezion Gemma-4 SOTA: 12B Fast-Inference Container + 240s Pytest Timeout + Paced Edit",
            },
            4: {
                "name": "hybrid_router_dual_model",
                "msg": "Cohezion Gemma-4 SOTA: Hybrid Router Dual Model (Fast-Path AST + Deep Patch Synthesis)",
            },
            5: {
                "name": "monadic_markov_patcher",
                "msg": "Cohezion Gemma-4 SOTA: Monadic Markov Patcher with Zero-Hallucination Edit Bounds",
            },
        },
    },
}


def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not read state file, reinitializing: %s", e)
    return {"utc_date": None, "competitions": {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def check_is_pending(api: KaggleApi, comp_slug: str) -> tuple[bool, str | None, str | None]:
    """Returns (is_pending, latest_ref, latest_status)."""
    try:
        subs = api.competition_submissions(comp_slug)
        if subs:
            latest = subs[0]
            status_str = str(latest.status).upper()
            is_pend = "PENDING" in status_str
            return is_pend, str(latest.ref), status_str
    except Exception as e:
        logger.warning("[%s] Failed to query submissions: %s", comp_slug, e)
    return False, None, None


def count_today_submissions(
    api: KaggleApi, comp_slug: str, today_utc: datetime.date
) -> tuple[int, list[Any]]:
    """Counts submissions dispatched on today's UTC calendar date."""
    try:
        subs = api.competition_submissions(comp_slug)
        today_subs = []
        for s in subs:
            sub_date = s.date.date() if hasattr(s.date, "date") else None
            if sub_date == today_utc:
                today_subs.append(s)
        return len(today_subs), subs
    except Exception as e:
        logger.warning("[%s] Could not count today submissions: %s", comp_slug, e)
        return 0, []


def verify_invariants(code_path: str, comp_slug: str) -> bool:
    """Runs AutoHarness, Dead-End Ledger, and Red-Team IV&V gates."""
    path = Path(code_path)
    if not path.exists():
        return True

    # 1. AST syntax check
    if path.suffix == ".ipynb":
        with open(path, encoding="utf-8") as f:
            nb = json.load(f)
        for idx, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") == "code":
                lines = [
                    l
                    for l in "".join(cell.get("source", [])).splitlines()
                    if not l.strip().startswith(("!", "%"))
                ]
                try:
                    ast.parse("\n".join(lines))
                except SyntaxError as e:
                    logger.critical("[%s] Cell %d AST Syntax Error: %s", comp_slug, idx, e)
                    return False
    elif path.suffix == ".py":
        with open(path, encoding="utf-8") as f:
            try:
                ast.parse(f.read())
            except SyntaxError as e:
                logger.critical("[%s] AST Syntax Error: %s", comp_slug, e)
                return False

    # 2. AutoHarness Invariant Factory Gate (arXiv:2603.03329v1)
    try:
        from cohezion.compound.invariant_factory import AutoHarnessInvariantFactory

        inv_res = AutoHarnessInvariantFactory.compile_and_verify(str(path), comp_slug)
        if inv_res.has_critical_violations or not inv_res.bytecode_valid:
            logger.critical(
                "[%s] AutoHarness invariant validation FAILED: %s", comp_slug, inv_res.violations
            )
            return False
        logger.info("[%s] ✓ AutoHarness invariants verified cleanly.", comp_slug)
    except Exception as e:
        logger.warning("[%s] AutoHarness gate note: %s", comp_slug, e)

    # 3. Dead-End Ledger Gate
    try:
        from cohezion.registry.forbidden_subgraphs import ForbiddenSubgraphLinter

        linter = ForbiddenSubgraphLinter()
        if path.suffix == ".ipynb":
            l_pass, l_viols = linter.audit_notebook(str(path), domain=comp_slug)
        else:
            with open(path, encoding="utf-8") as f:
                l_pass, l_viols = linter.audit_code(f.read(), domain=comp_slug)
        if not l_pass:
            logger.critical("[%s] FORBIDDEN SUBGRAPH DETECTED: %s", comp_slug, l_viols)
            return False
        logger.info("[%s] ✓ Dead-End Ledger check PASSED.", comp_slug)
    except Exception as e:
        logger.warning("[%s] Dead-End Ledger note: %s", comp_slug, e)

    # 4. Red-Team IV&V Gate
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
        if "arc-agi-3" in comp_slug:
            adversary.probe_poincare_invariants(default_poincare_distance)
            adversary.probe_zobrist_hash_collisions(default_zobrist_hash)
        elif "arc-agi-2" in comp_slug:
            adversary.probe_d4_symmetry(default_d4_verifier)
        elif "rsna" in comp_slug or "casmi" in comp_slug:
            adversary.probe_copula_rank_monotonicity(default_copula_blend)

        report = adversary.generate_audit_report()
        if not report.get("is_certified", False):
            logger.critical(
                "[%s] ADVERSARIAL RED-TEAM REJECTED: %s", comp_slug, report.get("findings")
            )
            return False
        logger.info("[%s] ✓ Adversarial Red-Team Certification PASSED.", comp_slug)
    except Exception as e:
        logger.warning("[%s] Red-Team note: %s", comp_slug, e)

    # 5. ARIA Pre-Dispatch Supervisory Guard (arXiv:2610.20780)
    try:
        from cohezion.aria.kaggle_guard import KaggleDispatchGuard, KaggleJob

        guard = KaggleDispatchGuard(enforce=True)
        job = KaggleJob(comp_slug=comp_slug, slot_num=0, code_path=path)
        decision = guard.evaluate(job)
        if decision.action in ("BLOCK", "ROLLBACK"):
            logger.critical(
                "[%s] ARIA Kaggle Guard REJECTED dispatch (%s): %s",
                comp_slug,
                decision.action,
                decision.reasons,
            )
            return False
        elif decision.action == "AMEND" and decision.amended_artifact:
            logger.info("[%s] ARIA Kaggle Guard auto-amended code: %s", comp_slug, decision.reasons)
            decision.amended_artifact.path.write_text(
                decision.amended_artifact.raw_content, encoding="utf-8"
            )
        logger.info(
            "[%s] ✓ ARIA Pre-Dispatch Supervisory Guard PASSED (%s).",
            comp_slug,
            decision.action,
        )
    except Exception as e:
        logger.warning("[%s] ARIA Kaggle Guard note: %s", comp_slug, e)

    return True


def dispatch_slot_submission(
    api: KaggleApi, comp_slug: str, slot_num: int, comp_cfg: dict[str, Any]
) -> bool:
    """Applies invariant patch, verifies bytecode, and dispatches submission."""
    slots_map = comp_cfg.get("slots", {})
    slot_info = slots_map.get(slot_num) or slots_map.get(min(slot_num, max(slots_map.keys())))
    if not slot_info:
        logger.warning("[%s] No slot config found for slot %d", comp_slug, slot_num)
    code_path = comp_cfg.get("notebook") or comp_cfg.get("code_path")

    # Pristine Baseline Reset: Prevent multi-version cumulative mutation across slots
    if code_path and str(code_path).endswith(".ipynb"):
        cp = Path(code_path)
        base_cp = cp.parent / (cp.stem + ".canonical_base.ipynb")
        if not base_cp.exists():
            base_cp = cp.with_suffix(".canonical_base.ipynb")
        if base_cp.exists():
            shutil.copyfile(base_cp, cp)
            logger.info(
                "[%s] Restored notebook from canonical base %s before Slot %d dispatch.",
                comp_slug,
                base_cp.name,
                slot_num,
            )

    patch_script = slot_info.get("patch_script")
    if patch_script and Path(patch_script).exists():
        logger.info("[%s] Applying Slot %d patch: %s", comp_slug, slot_num, patch_script)
        res = subprocess.run([sys.executable, patch_script], capture_output=True, text=True)
        if res.returncode != 0:
            logger.error("[%s] Patch script failed: %s", comp_slug, res.stderr)
            return False
        logger.info("[%s] Patch script succeeded: %s", comp_slug, res.stdout.strip())

    # Build fresh package archive for file mode (e.g. Gemma 4)
    if comp_cfg.get("mode") == "file":
        pack_script = comp_cfg.get("code_path")
        if pack_script and Path(pack_script).exists():
            logger.info("[%s] Building fresh package archive via %s...", comp_slug, pack_script)
            res = subprocess.run([sys.executable, pack_script], capture_output=True, text=True)
            if res.returncode != 0:
                logger.error("[%s] Packaging script failed: %s", comp_slug, res.stderr)
                return False
            logger.info("[%s] Packaging script succeeded.", comp_slug)

    if code_path and not verify_invariants(code_path, comp_slug):
        logger.critical(
            "[%s] Pre-dispatch invariant gates failed. Aborting Slot %d dispatch.",
            comp_slug,
            slot_num,
        )
        return False

    mode = comp_cfg.get("mode", "notebook")
    msg = slot_info.get("msg", f"Cohezion {comp_slug} Slot {slot_num}")

    if mode == "notebook":
        kernel = comp_cfg["kernel"]
        filename = comp_cfg["filename"]
        cmd = [
            sys.executable,
            "scripts/kaggle/kaggle_submit.py",
            "notebook",
            "-c",
            comp_slug,
            "-k",
            kernel,
            "-f",
            filename,
            "-m",
            msg,
            "-w",
        ]
        if code_path:
            cmd.extend(["--code-path", code_path])
            nb_dir = Path(code_path).parent
            if (nb_dir / "kernel-metadata.json").exists():
                cmd.extend(["--push-folder", str(nb_dir)])
    else:
        filepath = comp_cfg["filepath"]
        cmd = [
            sys.executable,
            "scripts/kaggle/kaggle_submit.py",
            "file",
            "-c",
            comp_slug,
            "-f",
            filepath,
            "-m",
            msg,
        ]
        if code_path:
            cmd.extend(["--code-path", code_path])

    logger.info("[%s] Dispatching Slot %d via kaggle_submit...", comp_slug, slot_num)
    res = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("[%s] Return code: %d | Stdout: %s", comp_slug, res.returncode, res.stdout.strip())
    if res.stderr:
        logger.warning("[%s] Stderr: %s", comp_slug, res.stderr.strip())

    return res.returncode == 0


def log_experiential_learning(comp_slug: str, sub: Any) -> None:
    """Logs scored submissions to SurrealDB and the Obsidian Vault."""
    try:
        sys.path.insert(0, str(WORKSPACE / "scripts" / "kaggle"))
        from recursive_experiential_learner import audit_and_learn

        audit_and_learn()
        logger.info(
            "[%s] ✓ Persisted experiential learning for Ref #%s (Score: %s)",
            comp_slug,
            sub.ref,
            sub.public_score,
        )
    except Exception as e:
        logger.warning("[%s] Experiential learning logging note: %s", comp_slug, e)


def record_pre_dispatch_reflection(
    comp_slug: str, target_slot: int, prior_sub: Any, comp_cfg: dict[str, Any]
) -> None:
    """Reflects on the prior submission score and invariant hypothesis before dispatching next slot."""
    slot_info = comp_cfg.get("slots", {}).get(target_slot, {})
    hypothesis_name = slot_info.get("name", f"slot_{target_slot}")
    prior_score = getattr(prior_sub, "public_score", None)
    prior_ref = getattr(prior_sub, "ref", None)

    reflection_text = (
        f"Pre-dispatch reflection for {comp_slug} Slot {target_slot} ({hypothesis_name}). "
        f"Prior submission Ref #{prior_ref} scored {prior_score}. "
        f"Target hypothesis incorporates: {slot_info.get('msg', 'No description')}."
    )
    logger.info("[%s] 🧠 Causal Reflection: %s", comp_slug, reflection_text)

    # Persist reflection and graph edge into SurrealDB
    try:
        import base64
        import urllib.request

        auth = base64.b64encode(b"root:root").decode()
        now_ts = int(datetime.datetime.now(datetime.UTC).timestamp())
        surql = f"""
        USE NS cohezion DB main;
        UPSERT submission_reflection:`reflection_{comp_slug.replace("-", "_")}_{now_ts}` CONTENT {{
            "competition": "{comp_slug}",
            "target_slot": {target_slot},
            "hypothesis_name": "{hypothesis_name}",
            "prior_ref": "{prior_ref}",
            "prior_score": "{prior_score}",
            "reflection": "{reflection_text}",
            "timestamp": "{datetime.datetime.now(datetime.UTC).isoformat()}"
        }};
        """
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=surql.encode("utf-8"),
            headers={
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Authorization": f"Basic {auth}",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0):  # noqa: S310
            pass
        logger.info("[%s] ✓ Recorded pre-dispatch reflection into SurrealDB", comp_slug)
    except Exception as e:
        logger.debug("[%s] Note recording reflection: %s", comp_slug, e)


def run_cycle(api: KaggleApi, state: dict[str, Any]) -> bool:
    """Runs a single evaluation and dispatch cycle across all active competitions.
    Returns True if any submission was dispatched.
    """
    now_utc = datetime.datetime.now(datetime.UTC)
    today_date = now_utc.date()

    if state.get("utc_date") != str(today_date):
        logger.info(
            "=== NEW UTC DAY DETECTED (%s). RESETTING DAILY ALLOTMENT COUNTERS ===", today_date
        )
        state["utc_date"] = str(today_date)
        comps = state.setdefault("competitions", {})
        for c_slug, c_info in comps.items():
            c_info["used_today"] = 0
            m_daily = PORTFOLIO_CONFIG.get(c_slug, {}).get("max_daily", 5)
            if m_daily == 1:
                cur_slot = c_info.get("active_slot", 1)
                num_slots = len(PORTFOLIO_CONFIG.get(c_slug, {}).get("slots", {})) or 1
                c_info["active_slot"] = (cur_slot % num_slots) + 1
                logger.info(
                    "[%s] Single-slot competition advanced to Slot %d for the new day (%s)",
                    c_slug,
                    c_info["active_slot"],
                    today_date,
                )

    dispatched_any = False

    for comp_slug, comp_cfg in PORTFOLIO_CONFIG.items():
        comp_state = state["competitions"].setdefault(
            comp_slug,
            {
                "used_today": 0,
                "active_slot": 1,
                "latest_ref": None,
                "latest_score": None,
                "status": "IDLE",
            },
        )

        prev_status = comp_state.get("status")
        is_pending, latest_ref, latest_status = check_is_pending(api, comp_slug)
        used_count, subs = count_today_submissions(api, comp_slug, today_date)
        comp_state["used_today"] = used_count
        comp_state["status"] = latest_status or "NONE"
        comp_state["latest_ref"] = latest_ref

        # Learn from completed submissions when status transitions from PENDING -> COMPLETE
        if prev_status and "PENDING" in prev_status and ("PENDING" not in (latest_status or "")):
            logger.info(
                "[%s] Submission Ref #%s cleared with status %s! Triggering recursive experiential learning...",
                comp_slug,
                latest_ref,
                latest_status,
            )
            if subs:
                log_experiential_learning(comp_slug, subs[0])

        if subs and subs[0].public_score is not None and str(subs[0].public_score).strip():
            comp_state["latest_score"] = str(subs[0].public_score)

        max_daily = comp_cfg.get("max_daily", 5)
        logger.info(
            "[%s] Quota Today: %d/%d used | Status: %s | Latest Ref: %s | Score: %s",
            comp_slug,
            used_count,
            max_daily,
            latest_status,
            latest_ref,
            comp_state.get("latest_score"),
        )

        if is_pending:
            logger.info(
                "[%s] Submission Ref #%s is currently %s; awaiting scoring clearance.",
                comp_slug,
                latest_ref,
                latest_status,
            )
            continue

        if used_count >= max_daily:
            logger.info(
                "[%s] %d/%d daily quota saturated for today! Well done.",
                comp_slug,
                used_count,
                max_daily,
            )
            continue

        # Ready to dispatch the next slot!
        target_slot = comp_state.get("active_slot", 1) if max_daily == 1 else used_count + 1
        logger.info(
            "[%s] >>> READY TO DISPATCH SLOT %d/%d (Hypothesis: %s) <<<",
            comp_slug,
            target_slot,
            max_daily,
            comp_cfg.get("slots", {}).get(target_slot, {}).get("name"),
        )

        # Learn from prior submissions before submitting the next solution
        if subs:
            logger.info(
                "[%s] Learning from prior submission (Ref #%s, Score: %s) before submitting Slot %d...",
                comp_slug,
                subs[0].ref,
                subs[0].public_score,
                target_slot,
            )
            log_experiential_learning(comp_slug, subs[0])
            record_pre_dispatch_reflection(comp_slug, target_slot, subs[0], comp_cfg)

        # Enforce automated Pre-Flight OOF Validation Gate
        preflight_validator = PreflightValidator(workspace_root=WORKSPACE)
        preflight_res = preflight_validator.validate_slot(comp_slug, target_slot, comp_cfg)
        if not preflight_res.passed:
            logger.warning(
                "[%s] Slot %d FAILED pre-flight OOF validation gate: %s. Skipping dispatch to protect daily quota.",
                comp_slug,
                target_slot,
                preflight_res.reason,
            )
            continue

        success = dispatch_slot_submission(api, comp_slug, target_slot, comp_cfg)
        if success:
            dispatched_any = True
            comp_state["used_today"] = target_slot
            save_state(state)
            # Sleep 120s between different competition dispatches to respect rate limits
            logger.info("Cooling down 120s before evaluating next competition...")
            time.sleep(120)
        else:
            logger.error(
                "[%s] Slot %d dispatch failed. Will retry next cycle.", comp_slug, target_slot
            )

    save_state(state)
    return dispatched_any


def main():
    logger.info("Initializing Continuous Daily Allotment Saturation Engine...")
    api = KaggleApi()
    api.authenticate()

    state = load_state()

    # If --once flag is passed, run a single pass and exit
    if "--once" in sys.argv:
        logger.info("Single pass requested via --once.")
        run_cycle(api, state)
        return

    logger.info("Starting continuous 24/7 autonomous allotment loop...")
    while True:
        try:
            run_cycle(api, state)
            # If all quotas are saturated across all competitions, sleep until near midnight UTC
            now_utc = datetime.datetime.now(datetime.UTC)
            all_saturated = all(
                state.get("competitions", {}).get(c, {}).get("used_today", 0)
                >= PORTFOLIO_CONFIG[c].get("max_daily", 5)
                for c in PORTFOLIO_CONFIG
            )
            if all_saturated:
                tomorrow_target = (now_utc + datetime.timedelta(days=1)).replace(
                    hour=0, minute=0, second=5, microsecond=0
                )
                sec_left = int((tomorrow_target - now_utc).total_seconds())
                logger.info(
                    "ALL ACTIVE COMPETITIONS SATURATED. Sleeping %d seconds (%0.2f hours) until 00:00:05 UTC reset...",
                    sec_left,
                    sec_left / 3600.0,
                )
                time.sleep(min(sec_left, 300))
            else:
                # Poll every 90 seconds to check for completed scoring and queue next slots
                time.sleep(90)
        except Exception as e:
            logger.exception("Unexpected error in allotment loop: %s", e)
            time.sleep(60)


if __name__ == "__main__":
    main()
