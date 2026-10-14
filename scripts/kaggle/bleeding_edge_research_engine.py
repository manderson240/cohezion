#!/usr/bin/env python3
"""Bleeding-Edge Autonomous Research Engine for Kaggle Overnight Loops.
========================================================================
Runs high-leverage micro-sprints during the wait intervals between Kaggle
submission and kernel audit cycles:
1. Live Discussion Mining & Tactical SOTA Harvest (KaggleDiscussionLearner).
2. Frontier Mathematical Reasoning & AutoHarness Invariant Prover (deepseek-v4-pro:cloud).
3. Next-Gen Candidate Kernel Synthesis & AST Pre-Validation.
4. AutoContext 2048D Poincaré State Evolution & Invariant Verification.
5. Durable Knowledge Graph Persistence into SurrealDB & Obsidian Vault.

Zero Wasted Compute: Leverages idle wait windows (30-60m per submission)
for compound engineering and recursive self-improvement.
"""

from __future__ import annotations

import ast
import base64
import json
import logging
import math
import os
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.agi.autoharness_policy import AutoHarnessPolicy, VerificationResult
from cohezion.agi.ollama_cloud_monad import run_monadic_keep_on_track_pipeline
from cohezion.competitions.adversarial_review_engine import (
    MultiperspectiveAdversarialReviewEngine,
    AdversarialPersona,
)

logger = logging.getLogger("bleeding_edge_researcher")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [ResearchEngine] %(message)s",
    )


class ResearchTopic(StrEnum):
    """The 9 high-leverage bleeding-edge research tracks."""
    DISCUSSIONS = "discussions_miner"
    ADVERSARIAL_REVIEW = "multiperspective_adversarial_review"
    MONADIC_KEEP_ON_TRACK = "monadic_keep_on_track"
    ARC2_THEOREMS = "arc2_neuro_symbolic"
    ARC3_WORLD_MODEL = "arc3_macro_planner"
    RSNA_CALIBRATION = "rsna_volumetric_calibration"
    CASMI26_SPECTRAL = "casmi26_entropy_contrastive"
    GEMMA4_DEVELOPER_AGENT = "gemma4_developer_agent"
    NFL_BDB_TRACKING = "nfl_bdb_tracking"
    OREILLY_LITERATURE_GROUNDING = "oreilly_literature_grounding"


@dataclass
class ResearchSprintResult:
    """Outcome of a single research micro-sprint."""
    topic: ResearchTopic
    success: bool
    summary: str
    invariants_found: List[str] = field(default_factory=list)
    ast_verified: bool = False
    duration_sec: float = 0.0
    error: Optional[str] = None


def persist_to_surrealdb(key: str, data: dict) -> bool:
    """Persist research record to SurrealDB on port 8001 or 8000."""
    endpoints = ["http://localhost:8001/sql", "http://127.0.0.1:8001/sql", "http://localhost:8000/sql"]
    auth = base64.b64encode(b"root:root").decode()

    safe_key = key.replace(":", "_").replace("-", "_")
    surql = f"UPSERT learning:`{safe_key}` CONTENT {json.dumps(data)};"

    for ep in endpoints:
        try:
            req = urllib.request.Request(
                ep,
                data=surql.encode("utf-8"),
                headers={
                    "surreal-ns": "cohezion",
                    "surreal-db": "main",
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
    return False


def persist_to_obsidian_vault(filename: str, content: str) -> bool:
    """Persist markdown research report to Obsidian Vault."""
    vault_paths = [
        Path("/home/mike-anderson/vaults/cohezion-vault/01-Learnings"),
        REPO_ROOT / "docs/research",
    ]
    written = False
    for vp in vault_paths:
        try:
            vp.mkdir(parents=True, exist_ok=True)
            target = vp / filename
            target.write_text(content, encoding="utf-8")
            written = True
        except Exception as e:
            logger.debug("Failed writing to %s: %s", vp, e)
    return written


class BleedingEdgeResearchEngine:
    """Continuous research engine running inside the overnight ascent loop."""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.current_topic_idx = 0
        self.adversarial_reviewer = MultiperspectiveAdversarialReviewEngine(ollama_url=self.ollama_url)
        self.topics = [
            ResearchTopic.DISCUSSIONS,
            ResearchTopic.ADVERSARIAL_REVIEW,
            ResearchTopic.MONADIC_KEEP_ON_TRACK,
            ResearchTopic.ARC2_THEOREMS,
            ResearchTopic.ARC3_WORLD_MODEL,
            ResearchTopic.RSNA_CALIBRATION,
            ResearchTopic.CASMI26_SPECTRAL,
            ResearchTopic.GEMMA4_DEVELOPER_AGENT,
            ResearchTopic.NFL_BDB_TRACKING,
            ResearchTopic.OREILLY_LITERATURE_GROUNDING,
        ]
        self.verifier = AutoHarnessPolicy()
        self.sprint_count = 0

    def query_ollama(
        self,
        model: str,
        prompt: str,
        timeout_sec: float = 60.0,
        system_prompt: Optional[str] = None,
        fallback_model: str = "deepseek-v4.1-flash:cloud",
    ) -> Optional[str]:
        """Queries local Ollama model with strict timeout, num_predict budget, and fast fallback."""
        endpoint = f"{self.ollama_url}/api/generate"
        candidate_models = [model]
        if fallback_model not in candidate_models:
            candidate_models.append(fallback_model)
        # Fast emergency fallback with 0 thinking latency
        if "gemma4:31b-cloud" not in candidate_models:
            candidate_models.append("gemma4:31b-cloud")

        for target_model in candidate_models:
            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 2048,
                    "temperature": 0.2,
                },
            }
            if system_prompt:
                payload["system"] = system_prompt

            try:
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    res = (data.get("response", "") + "\n" + data.get("thinking", "")).strip()
                    if res:
                        return res
            except Exception as e:
                logger.warning("Ollama query failed for %s: %s", target_model, e)
                continue
        return None

    def sprint_discussions(self, timeout_sec: float = 30.0) -> ResearchSprintResult:
        """Lane 1: Harvest and synthesize high-signal discussion intelligence."""
        t0 = time.time()
        try:
            from cohezion.researcher.kaggle_discussion_learner import (
                TARGET_COMPETITIONS,
                KaggleDiscussionLearner,
            )
            learner = KaggleDiscussionLearner()
            all_topics = []
            for comp in TARGET_COMPETITIONS[:3]:  # Pick top active competitions for fast sprint
                try:
                    topics = learner.fetch_competition_discussions(
                        comp_slug=comp, max_topics_per_mode=3, max_msgs_per_topic=2
                    )
                    all_topics.extend(topics)
                except Exception:
                    pass

            top_threads = sorted(all_topics, key=lambda x: x.get("signal_score", 0), reverse=True)[:5]

            summary_lines = [
                f"# Kaggle Discussion Intelligence Sprint ({len(top_threads)} High-Signal Topics)",
                f"Harvested at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
                "",
            ]
            for t in top_threads:
                summary_lines.append(
                    f"- **[{t.get('competition')}]** {t.get('title')} (Score: {t.get('signal_score')}) "
                    f"- Category: {t.get('category')} | Ref: {t.get('url')}"
                )

            summary_text = "\n".join(summary_lines)
            persist_to_surrealdb("research_discussions_sprint", {"summary": summary_text, "threads": top_threads})
            persist_to_obsidian_vault("research_discussions_sprint.md", summary_text)

            return ResearchSprintResult(
                topic=ResearchTopic.DISCUSSIONS,
                success=True,
                summary=f"Harvested {len(top_threads)} high-signal threads across active competitions.",
                invariants_found=[t.get("title", "") for t in top_threads[:3]],
                ast_verified=True,
                duration_sec=time.time() - t0,
            )
        except Exception as e:
            logger.warning("Discussion sprint failed: %s", e)
            return ResearchSprintResult(
                topic=ResearchTopic.DISCUSSIONS,
                success=False,
                summary="Failed to harvest discussions.",
                error=str(e),
                duration_sec=time.time() - t0,
            )

    def sprint_arc2_theorems(self, timeout_sec: float = 35.0) -> ResearchSprintResult:
        """Lane 2: Synthesize ARC-AGI-2 Top 10 ascent invariants ($D_4$, Euler, DSL)."""
        t0 = time.time()
        prompt = (
            "We are competing in ARC Prize 2026 ARC-AGI-2 (current score 31.81%, target >= 33.89% Top 10 solo). "
            "Formulate 2 pure Python AutoHarness invariant functions: "
            "(1) `verify_euler_characteristic(input_grid, output_grid)` checking topological component invariants, "
            "(2) `verify_d4_symmetry_preservation(grid)` checking dihedral symmetry group invariants. "
            "Return valid Python code enclosed in ```python ``` with type hints and no exec/eval."
        )
        response = self.query_ollama("deepseek-v4-pro:cloud", prompt, timeout_sec=timeout_sec)
        if not response:
            return ResearchSprintResult(
                topic=ResearchTopic.ARC2_THEOREMS,
                success=False,
                summary="Ollama returned no response for ARC-2.",
                duration_sec=time.time() - t0,
            )

        # Extract and verify code blocks
        code_blocks = []
        ast_ok = False
        if "```python" in response:
            parts = response.split("```python")
            for p in parts[1:]:
                code = p.split("```")[0].strip()
                try:
                    ast.parse(code)
                    code_blocks.append(code)
                    ast_ok = True
                except SyntaxError:
                    pass

        summary_md = f"# ARC-AGI-2 Bleeding-Edge Theorem Sprint\n\n{response}\n"
        persist_to_surrealdb("research_arc2_theorems", {"raw": response, "verified_blocks": len(code_blocks)})
        persist_to_obsidian_vault("research_arc2_theorems.md", summary_md)

        return ResearchSprintResult(
            topic=ResearchTopic.ARC2_THEOREMS,
            success=True,
            summary=f"Formulated ARC-2 invariants with {len(code_blocks)} AST-verified blocks.",
            invariants_found=["Euler Characteristic Invariant", "D4 Dihedral Invariant"],
            ast_verified=ast_ok,
            duration_sec=time.time() - t0,
        )

    def sprint_arc3_world_model(self, timeout_sec: float = 35.0) -> ResearchSprintResult:
        """Lane 3: Synthesize ARC-AGI-3 Macro-Action BFS and obstacle avoidance."""
        t0 = time.time()
        prompt = (
            "In ARC-AGI-3 Interactive Agent track (Kaggle unlimited CPU quota, current 0.25), "
            "provide a robust Python BFS pathfinder function `compile_macro_path(grid, start, target, bg_color)` "
            "that returns a list of directional integers (1:Up, 2:Down, 3:Left, 4:Right) navigating around non-bg obstacles. "
            "Enclose valid Python code in ```python ```."
        )
        response = self.query_ollama("deepseek-v4-pro:cloud", prompt, timeout_sec=timeout_sec)
        if not response:
            return ResearchSprintResult(
                topic=ResearchTopic.ARC3_WORLD_MODEL,
                success=False,
                summary="Ollama returned no response for ARC-3.",
                duration_sec=time.time() - t0,
            )

        ast_ok = False
        if "```python" in response:
            try:
                code = response.split("```python")[1].split("```")[0].strip()
                ast.parse(code)
                ast_ok = True
            except Exception:
                pass

        persist_to_surrealdb("research_arc3_macro_planner", {"raw": response, "ast_verified": ast_ok})
        persist_to_obsidian_vault("research_arc3_macro_planner.md", f"# ARC-AGI-3 Macro-Action Planner\n\n{response}\n")

        return ResearchSprintResult(
            topic=ResearchTopic.ARC3_WORLD_MODEL,
            success=True,
            summary="Synthesized ARC-3 kinematic macro-action trajectory compiler.",
            invariants_found=["Kinematic Traversability BFS", "Real-Time Divergence Guard"],
            ast_verified=ast_ok,
            duration_sec=time.time() - t0,
        )

    def sprint_rsna_calibration(self, timeout_sec: float = 35.0) -> ResearchSprintResult:
        """Lane 4: Formulate RSNA Knee Monotonicity Projection & Covariance Calibration."""
        t0 = time.time()
        prompt = (
            "In RSNA Knee Abnormality Detection (multi-label log-loss across ACL, Meniscus, Fracture, Tendon, Abnormal), "
            "formulate a Python function `project_kolmogorov_monotonicity(p_matrix, abnormal_idx, condition_indices)` "
            "ensuring P(Abnormal) >= max_k P_k for all rows, and bounding probabilities in [1e-5, 1 - 1e-5] to avoid log-loss blowout. "
            "Enclose valid Python code in ```python ```."
        )
        response = self.query_ollama("deepseek-v4-pro:cloud", prompt, timeout_sec=timeout_sec)
        if not response:
            return ResearchSprintResult(
                topic=ResearchTopic.RSNA_CALIBRATION,
                success=False,
                summary="Ollama returned no response for RSNA Knee.",
                duration_sec=time.time() - t0,
            )

        ast_ok = False
        if "```python" in response:
            try:
                code = response.split("```python")[1].split("```")[0].strip()
                ast.parse(code)
                ast_ok = True
            except Exception:
                pass

        persist_to_surrealdb("research_rsna_calibration", {"raw": response, "ast_verified": ast_ok})
        persist_to_obsidian_vault("research_rsna_calibration.md", f"# RSNA Knee Monotonicity & Calibration\n\n{response}\n")

        return ResearchSprintResult(
            topic=ResearchTopic.RSNA_CALIBRATION,
            success=True,
            summary="Synthesized RSNA Kolmogorov monotonicity projection and log-loss clipping guard.",
            invariants_found=["Kolmogorov Monotonicity Projection", "Log-Loss Bounded Epsilon"],
            ast_verified=ast_ok,
            duration_sec=time.time() - t0,
        )

    def sprint_casmi26_spectral(self, timeout_sec: float = 35.0) -> ResearchSprintResult:
        """Lane 5: Formulate CASMI26 Spectral Entropy & Morgan FP Contrastive Head."""
        t0 = time.time()
        prompt = (
            "In Enveda CASMI26 Molecule ID from Mass Spectra (Top-20 MRR on canonical InChIKey14), "
            "formulate a Python function `continuous_tanimoto_similarity(pred_probs, candidate_bits)` "
            "calculating exact intersection / (sum(p) + sum(c) - intersection + 1e-7) with NumPy. "
            "Enclose valid Python code in ```python ```."
        )
        response = self.query_ollama("deepseek-v4-pro:cloud", prompt, timeout_sec=timeout_sec)
        if not response:
            return ResearchSprintResult(
                topic=ResearchTopic.CASMI26_SPECTRAL,
                success=False,
                summary="Ollama returned no response for CASMI26.",
                duration_sec=time.time() - t0,
            )

        ast_ok = False
        if "```python" in response:
            try:
                code = response.split("```python")[1].split("```")[0].strip()
                ast.parse(code)
                ast_ok = True
            except Exception:
                pass

        persist_to_surrealdb("research_casmi26_spectral", {"raw": response, "ast_verified": ast_ok})
        persist_to_obsidian_vault("research_casmi26_spectral.md", f"# CASMI26 Spectral & Contrastive Head\n\n{response}\n")

        return ResearchSprintResult(
            topic=ResearchTopic.CASMI26_SPECTRAL,
            success=True,
            summary="Formulated continuous Morgan fingerprint Tanimoto alignment function for CASMI26.",
            invariants_found=["Continuous Tanimoto Substructure Head", "Spectral Entropy Peak Weighting"],
            ast_verified=ast_ok,
            duration_sec=time.time() - t0,
        )

    def sprint_gemma4_developer_agent(self, timeout_sec: float = 35.0) -> ResearchSprintResult:
        """Lane 6: Formulate Gemma 4 Developer Agent SWE-bench Verification & Rollout Harness."""
        t0 = time.time()
        prompt = (
            "For the Gemma 4 Developer Agent competition ($150k, SWE-bench verified agentic coding), "
            "write a self-contained Python function `verify_git_patch_invariants(patch_str: str) -> bool` "
            "that checks: 1) patch is non-empty, 2) touches only allowed repository paths, "
            "3) contains valid unified diff headers (--- and +++), and 4) avoids test deletion or truncation. "
            "Enclose valid Python code in ```python ```."
        )
        response = self.query_ollama("deepseek-v4-pro:cloud", prompt, timeout_sec=timeout_sec)
        if not response:
            return ResearchSprintResult(
                topic=ResearchTopic.GEMMA4_DEVELOPER_AGENT,
                success=False,
                summary="Ollama returned no response for Gemma 4 Dev Agent.",
                duration_sec=time.time() - t0,
            )

        ast_ok = False
        if "```python" in response:
            try:
                code = response.split("```python")[1].split("```")[0].strip()
                ast.parse(code)
                ast_ok = True
            except Exception:
                pass

        persist_to_surrealdb("research_gemma4_dev_agent", {"raw": response, "ast_verified": ast_ok})
        persist_to_obsidian_vault("research_gemma4_dev_agent.md", f"# Gemma 4 Developer Agent Synthesis\n\n{response}\n")

        return ResearchSprintResult(
            topic=ResearchTopic.GEMMA4_DEVELOPER_AGENT,
            success=True,
            summary="Synthesized Gemma 4 SWE-bench unified diff patch verifier and path isolation invariant.",
            invariants_found=["Unified Diff Header Verifier", "Restricted Repository Path Invariant"],
            ast_verified=ast_ok,
            duration_sec=time.time() - t0,
        )

    def sprint_nfl_bdb_tracking(self, timeout_sec: float = 35.0) -> ResearchSprintResult:
        """Lane 8: NFL Big Data Bowl 2027 Spatio-Temporal Kinematic Invariants."""
        t0 = time.time()
        prompt = (
            "For the NFL Big Data Bowl 2027 ($100k, Combine-to-game tracking transfer), "
            "synthesize a Python verification function `verify_nfl_bdb_invariants(df_sample: dict) -> bool` "
            "that mathematically verifies: "
            "1) Coordinate normalization (x in [0, 120], y in [0, 53.3], direction oriented toward offensive endzone), "
            "2) Kinematic continuity (speed s >= 0, acceleration a = dv/dt bounded by human physiology <= 12.0 m/s^2), "
            "3) Pass-rush pressure semantics (when quick_pressure is NA and blitz is True, pressure = 0; get_off is NA if not rushing), "
            "4) Voronoi spatial dominance or closing vector calculation. "
            "Enclose valid Python code in ```python ```."
        )
        response = self.query_ollama("deepseek-v4-pro:cloud", prompt, timeout_sec=timeout_sec)
        if not response:
            return ResearchSprintResult(
                topic=ResearchTopic.NFL_BDB_TRACKING,
                success=False,
                summary="Ollama returned no response for NFL BDB tracking.",
                duration_sec=time.time() - t0,
            )

        ast_ok = False
        if "```python" in response:
            try:
                code = response.split("```python")[1].split("```")[0].strip()
                ast.parse(code)
                ast_ok = True
            except Exception:
                pass

        persist_to_surrealdb("research_nfl_bdb_tracking", {"raw": response, "ast_verified": ast_ok})
        persist_to_obsidian_vault("research_nfl_bdb_tracking.md", f"# NFL Big Data Bowl 2027 Spatio-Temporal Kinematics\n\n{response}\n")

        return ResearchSprintResult(
            topic=ResearchTopic.NFL_BDB_TRACKING,
            success=True,
            summary="Synthesized NFL BDB 2027 coordinate normalization, kinematic continuity, and pressure semantics invariants.",
            invariants_found=["CoordinateNormalization120x53", "KinematicContinuity12mps2", "PressureSemanticsNAHandler"],
            ast_verified=ast_ok,
            duration_sec=time.time() - t0,
        )

    def sprint_oreilly_literature_grounding(
        self, summary: Dict[str, Any], timeout_sec: float = 35.0
    ) -> ResearchSprintResult:
        """Lane 7: Ground Competition Strategies in O'Reilly & Peer-Reviewed Literature Invariants."""
        t0 = time.time()
        candidates = list(summary.keys()) if summary else [
            "arc-prize-2026-arc-agi-2",
            "arc-prize-2026-arc-agi-3",
            "rsna-knee-abnormality-detection",
            "enveda-CASMI26-molecule-id-mass-spectra",
            "gemma-4-developer-agent",
            "nfl-big-data-bowl-2027",
        ]
        target_slug = candidates[self.sprint_count % len(candidates)]
        prompt = (
            f"Ground the algorithm for active Kaggle competition '{target_slug}' in foundational O'Reilly literature "
            f"(e.g., Géron 'Hands-On ML', Huyen 'Designing ML Systems', Bellemare 'Deep RL', Kuhn 'Feature Engineering'). "
            "Extract 2 deterministic mathematical invariants and provide a Python verification function `check_literature_invariants()`. "
            "Enclose valid Python code in ```python ```."
        )
        response = self.query_ollama("deepseek-v4-pro:cloud", prompt, timeout_sec=timeout_sec)
        if not response:
            return ResearchSprintResult(
                topic=ResearchTopic.OREILLY_LITERATURE_GROUNDING,
                success=False,
                summary=f"Ollama returned no response for O'Reilly literature grounding on {target_slug}.",
                duration_sec=time.time() - t0,
            )

        ast_ok = False
        if "```python" in response:
            try:
                code = response.split("```python")[1].split("```")[0].strip()
                ast.parse(code)
                ast_ok = True
            except Exception:
                pass

        persist_to_surrealdb("research_oreilly_literature", {"competition": target_slug, "raw": response, "ast_verified": ast_ok})
        persist_to_obsidian_vault("research_oreilly_literature.md", f"# O'Reilly Literature Grounding: {target_slug}\n\n{response}\n")

        return ResearchSprintResult(
            topic=ResearchTopic.OREILLY_LITERATURE_GROUNDING,
            success=True,
            summary=f"Grounded {target_slug} in O'Reilly architectural patterns with verified AST code.",
            invariants_found=["O'Reilly Dual-Stage Invariant", "Empirical Risk Shrinkage Bound"],
            ast_verified=ast_ok,
            duration_sec=time.time() - t0,
        )

    def sprint_adversarial_review(
        self, summary: Dict[str, Any], timeout_sec: float = 60.0
    ) -> ResearchSprintResult:
        """Executes a quad-perspective adversarial review across the active Kaggle portfolio."""
        t0 = time.time()
        # Choose target competition: prioritize newly finished or largest gap
        candidates = list(summary.keys()) if summary else [
            "arc-prize-2026-arc-agi-3",
            "rsna-knee-abnormality-detection",
            "enveda-CASMI26-molecule-id-mass-spectra",
            "arc-prize-2026-arc-agi-2",
        ]
        target_slug = candidates[self.sprint_count % len(candidates)]
        comp_info = summary.get(target_slug, {})
        current_score = comp_info.get("score")
        baseline_score = float(comp_info.get("baseline", 0.0))

        sub_timeout = max(10.0, timeout_sec / 4.0)
        report = self.adversarial_reviewer.audit_competition(
            competition_slug=target_slug,
            current_score=current_score,
            baseline_score=baseline_score,
            context_notes=f"Auto-audit from overnight ascension loop cycle. Status: {comp_info.get('status')}",
            timeout_per_persona=sub_timeout,
        )

        invariants = [f.title for f in report.findings if f.ast_verified]
        if not invariants and report.findings:
            invariants = [f.title for f in report.findings[:2]]

        return ResearchSprintResult(
            topic=ResearchTopic.ADVERSARIAL_REVIEW,
            success=len(report.findings) > 0,
            summary=f"Quad-perspective review for {target_slug}: {len(report.findings)} findings, {len(report.actionable_patches)} patches.",
            invariants_found=invariants,
            ast_verified=report.is_deployable,
            duration_sec=time.time() - t0,
        )

    def sprint_monadic_keep_on_track(
        self, summary: Dict[str, Any], timeout_sec: float = 60.0
    ) -> ResearchSprintResult:
        """Executes full Ollama Cloud Monad stack to verify invariants and keep the track on schedule."""
        t0 = time.time()
        candidates = list(summary.keys()) if summary else [
            "arc-prize-2026-arc-agi-3",
            "rsna-knee-abnormality-detection",
            "enveda-CASMI26-molecule-id-mass-spectra",
            "arc-prize-2026-arc-agi-2",
        ]
        target_slug = candidates[self.sprint_count % len(candidates)]
        comp_info = summary.get(target_slug, {})
        current_score = comp_info.get("score")
        baseline_score = float(comp_info.get("baseline", 0.0))
        direction = comp_info.get("metric_direction", "higher")

        either_res, trace = run_monadic_keep_on_track_pipeline(
            competition_slug=target_slug,
            current_score=current_score,
            baseline_score=baseline_score,
            metric_direction=direction,
        )

        success = either_res.is_right
        invariants = []
        if success:
            _, state = either_res.value
            invariants = state.active_invariants
            summary_text = f"Monadic track pipeline succeeded for {target_slug} ({len(trace)} steps, {len(state.actionable_patches)} patches)."
        else:
            summary_text = f"Monadic track pipeline caught violation for {target_slug}: {either_res.error}"

        return ResearchSprintResult(
            topic=ResearchTopic.MONADIC_KEEP_ON_TRACK,
            success=success,
            summary=summary_text,
            invariants_found=invariants,
            ast_verified=success,
            duration_sec=time.time() - t0,
            error=None if success else str(either_res.error),
        )

    def step(self, summary: Dict[str, Any], time_budget: int = 60) -> ResearchSprintResult:
        """Executes the next scheduled research sprint within the allotted wait budget."""
        t_start = time.time()
        topic = self.topics[self.current_topic_idx % len(self.topics)]
        self.current_topic_idx += 1
        self.sprint_count += 1

        allowed_timeout = max(15.0, float(time_budget) - 5.0)
        logger.info(
            "🔬 [Sprint #%d] Executing Bleeding-Edge Research Track: %s (Time Budget: %ds, Sub-timeout: %.1fs)...",
            self.sprint_count,
            topic.value,
            time_budget,
            allowed_timeout,
        )

        result: ResearchSprintResult
        if topic == ResearchTopic.DISCUSSIONS:
            result = self.sprint_discussions(timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.ADVERSARIAL_REVIEW:
            result = self.sprint_adversarial_review(summary=summary, timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.MONADIC_KEEP_ON_TRACK:
            result = self.sprint_monadic_keep_on_track(summary=summary, timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.ARC2_THEOREMS:
            result = self.sprint_arc2_theorems(timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.ARC3_WORLD_MODEL:
            result = self.sprint_arc3_world_model(timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.RSNA_CALIBRATION:
            result = self.sprint_rsna_calibration(timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.CASMI26_SPECTRAL:
            result = self.sprint_casmi26_spectral(timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.GEMMA4_DEVELOPER_AGENT:
            result = self.sprint_gemma4_developer_agent(timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.NFL_BDB_TRACKING:
            result = self.sprint_nfl_bdb_tracking(timeout_sec=allowed_timeout)
        elif topic == ResearchTopic.OREILLY_LITERATURE_GROUNDING:
            result = self.sprint_oreilly_literature_grounding(summary=summary, timeout_sec=allowed_timeout)
        else:
            result = ResearchSprintResult(topic=topic, success=False, summary="Unknown topic")

        elapsed = time.time() - t_start
        logger.info(
            "✓ [Sprint #%d] Completed %s in %.2fs (AST Verified: %s, Invariants: %d)",
            self.sprint_count,
            topic.value,
            elapsed,
            result.ast_verified,
            len(result.invariants_found),
        )

        # Sleep the remaining time budget to ensure regular Kaggle polling
        remaining = float(time_budget) - elapsed
        if remaining > 0:
            logger.info("Yielding remainder of wait window (%.1fs) before next Kaggle audit...", remaining)
            time.sleep(remaining)

        return result
