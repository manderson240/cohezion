"""Stateless Language Agents (SLA) for Kaggle Competition Optimization.
====================================================================
Reference: arXiv:2610.07625 (FAIR at Meta, UT Austin, Georgia Tech).

Applies the SLA paradigm ("Stateful Search in Harness, Stateless LLMs")
across active Kaggle competitions:
1. RSNA Knee Abnormality Detection (Macro ROC-AUC optimization across 12 pathologies)
2. ARC-AGI-2 & ARC-AGI-3 (Affordance DSL & Zobrist hash invariants)
3. Enveda CASMI26 (Adduct deconvolution, GBDT ranking, isotope envelope parsimony)

Key Guarantees:
- Zero History Replay: Single-turn LLM calls prevent context rot and 99.4% token bloat.
- Failure Disambiguation: INCONCLUSIVE_FAILURE vs MEASURED_NON_IMPROVEMENT.
- Local Candidate Retention (k=3) with Global Reset on direction changes.
- Automated Two-Party IV&V verification on candidate promotion.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from cohezion.compound.stateless_language_agent import (
    AdvisorAssignment,
    CandidateOutcome,
    EvidenceSummarizer,
    EvidenceSummary,
    ResearchCandidate,
    SLAHarness,
    StatelessAdvisor,
    StatelessWorker,
)

logger = logging.getLogger(__name__)


@dataclass
class KaggleOptimizationConfig:
    """Configuration for a competition-specific SLA optimization loop."""

    competition_slug: str
    metric_name: str
    baseline_score: float
    initial_code_path: Path
    initial_directions: List[Dict[str, str]]
    worker_models: Dict[str, str] = field(default_factory=lambda: {
        "worker_0": "glm-5.3:cloud",
        "worker_1": "kimi-k2.7-code:cloud",
    })
    advisor_model: str = "deepseek-v4-pro:cloud"
    local_retention_k: int = 3
    higher_is_better: bool = True
    ollama_url: str = "http://localhost:11434/api/generate"


class StatelessKaggleOptimizer:
    """Manages long-horizon automated research over Kaggle competition kernels."""

    def __init__(self, config: KaggleOptimizationConfig) -> None:
        self.config = config
        self.initial_code = config.initial_code_path.read_text(encoding="utf-8") if config.initial_code_path.exists() else ""
        self.harness: Optional[SLAHarness] = None

    def _create_ollama_caller(self, model: str) -> Callable[[str], Awaitable[str]]:
        """Creates a single-turn stateless async caller for an Ollama model."""
        async def _call(prompt: str) -> str:
            loop = asyncio.get_running_loop()

            def _sync_post():
                payload = json.dumps({
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 2048,
                    },
                }).encode("utf-8")
                req = urllib.request.Request(
                    self.config.ollama_url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                try:
                    with urllib.request.urlopen(req, timeout=60.0) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        return res.get("response", "")
                except Exception as exc:
                    logger.warning("Ollama call failed for %s: %s", model, exc)
                    return ""

            return await loop.run_in_executor(None, _sync_post)

        return _call

    def build_harness(
        self,
        evaluator_fn: Callable[[str], Awaitable[Tuple[float, str, bool]]],
        mock_advisor: Optional[Callable[[str], Awaitable[str]]] = None,
        mock_workers: Optional[Dict[str, Callable[[str], Awaitable[str]]]] = None,
    ) -> SLAHarness:
        """Instantiates the SLAHarness wired to Ollama Cloud models."""
        advisor_caller = mock_advisor or self._create_ollama_caller(self.config.advisor_model)
        worker_callers = mock_workers or {
            w_id: self._create_ollama_caller(model)
            for w_id, model in self.config.worker_models.items()
        }

        self.harness = SLAHarness(
            initial_code=self.initial_code,
            task_description=f"Kaggle Competition: {self.config.competition_slug} | Target Metric: {self.config.metric_name}",
            initial_directions=self.config.initial_directions,
            evaluator_fn=evaluator_fn,
            worker_ids=list(self.config.worker_models.keys()),
            local_retention_k=self.config.local_retention_k,
            higher_is_better=self.config.higher_is_better,
            advisor_caller=advisor_caller,
            worker_callers=worker_callers,
        )
        return self.harness

    async def run_iterations(self, epochs: int = 1) -> List[Dict[str, Any]]:
        """Executes n search epochs with failure disambiguation & global best updates."""
        if not self.harness:
            raise RuntimeError("Harness must be initialized before running iterations.")

        if not self.harness.candidates:
            await self.harness.initialize()

        history = []
        for _ in range(epochs):
            res = await self.harness.run_epoch()
            history.append(res)
            logger.info(
                "[%s Epoch %d] Best Score: %.4f (Tokens: Adv=%d, Workers=%d)",
                self.config.competition_slug,
                res["epoch"],
                res["global_best_score"],
                self.harness.total_advisor_tokens,
                self.harness.total_worker_tokens,
            )

        return history


def get_default_rsna_knee_sla_config() -> KaggleOptimizationConfig:
    """Pre-configured SLA optimization config for RSNA Knee Abnormality Detection."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    code_path = repo_root / "scripts/kaggle/rsna_speedy_raptors/patch_rsna_v30_pathology_temperature.py"

    directions = [
        {
            "direction_id": "dir_pref_temperature",
            "hypothesis": "Pre-fusion classwise temperature scaling shifts latent copula mixtures for rare tear classes.",
        },
        {
            "direction_id": "dir_pathology_weights",
            "hypothesis": "Radiological imaging plane alignment: High-res local bone features favor CNN; volumetric fluid favors ViT.",
        },
        {
            "direction_id": "dir_copula_shrinkage",
            "hypothesis": "Ledoit-Wolf shrinkage delta in 12x12 clinical prior graph regularizes small-sample noise on 58 gold knees.",
        },
        {
            "direction_id": "dir_r7_tri_arm_blend",
            "hypothesis": "Injecting R7 ConvNeXt-small 4-fold bundle with multi-scale Raptor (384 + 224) breaks 0.957 barrier.",
        },
    ]

    return KaggleOptimizationConfig(
        competition_slug="rsna-knee-abnormality-detection",
        metric_name="Macro ROC-AUC (12 classes)",
        baseline_score=0.943,
        initial_code_path=code_path,
        initial_directions=directions,
        worker_models={
            "worker_0": "glm-5.3:cloud",
            "worker_1": "kimi-k2.7-code:cloud",
        },
        advisor_model="deepseek-v4-pro:cloud",
        local_retention_k=3,
        higher_is_better=True,
    )
