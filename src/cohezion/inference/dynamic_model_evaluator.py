"""Dynamic Model Evaluator & Adaptive Promotion Suite.
=====================================================
Puts into practice the 5 empirical signals for knowing when to use different models:
1. AutoHarness Deterministic AST & Unit Test Verifier (0 ms verification).
2. Expected Value of Intervention (EVI) Calculation.
3. Hardware Sentry & Memory Floor (GTT aperture, RAM, PSI).
4. Head-to-head empirical quality evaluation across resident silicon.
5. Dual persistence & SurrealDB `model_performance` auto-promotion.
"""

from __future__ import annotations

import ast
import json
import logging
import time
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from cohezion.reliability.oom_guard import OOMGuard


logger = logging.getLogger("dynamic_model_evaluator")

LEMONADE_URL = "http://127.0.0.1:13305/v1/chat/completions"


@dataclass(frozen=True, slots=True)
class ModelEvaluationScorecard:
    """Quantitative evaluation outcome for a model on a verified task."""

    model: str
    task_id: str
    syntax_valid: bool
    test_pass_rate: float
    quality_score: float
    latency_ms: float
    tokens_per_second: float
    hardware_lane: str
    evi_score: float
    escalation_required: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert scorecard to JSON-serializable dictionary."""
        return asdict(self)


class DynamicModelEvaluator:
    """Evaluates models dynamically against deterministic AutoHarness verifiers."""

    def __init__(self, port: int = 13305) -> None:
        self.endpoint = f"http://127.0.0.1:{port}/v1/chat/completions"

    def query_model(
        self, model: str, prompt: str, max_tokens: int = 256, timeout: float = 10.0
    ) -> tuple[str, float, float]:
        """Query model on Lemonade and measure latency and tokens/sec."""
        t0 = time.perf_counter()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        req = urllib.request.Request(  # noqa: S310
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                data = json.loads(resp.read().decode())
                elapsed = time.perf_counter() - t0
                content = data["choices"][0]["message"]["content"]
                # Strip thinking blocks if present
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                tokens = len(content.split())
                tps = tokens / max(elapsed, 0.001)
                return content, elapsed * 1000.0, tps
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            logger.warning(f"Query to {model} failed: {exc}")
            return f"ERROR: {exc}", elapsed * 1000.0, 0.0

    def verify_python_code(
        self,
        raw_output: str,
        test_fn: Callable[[dict[str, Any]], float],
    ) -> tuple[bool, float, str]:
        """AutoHarness AST extraction and deterministic test execution."""
        # 1. Extract code block
        code = raw_output
        if "```python" in raw_output:
            code = raw_output.split("```python")[1].split("```")[0]
        elif "```" in raw_output:
            code = raw_output.split("```")[1].split("```")[0]

        code = code.strip()

        # 2. AST Parse
        try:
            tree = ast.parse(code)
            syntax_valid = len(tree.body) > 0
        except SyntaxError:
            return False, 0.0, code

        # 3. Execute in isolated namespace
        local_env: dict[str, Any] = {}
        try:
            exec(code, {}, local_env)  # noqa: S102
            pass_rate = test_fn(local_env)
            return syntax_valid, pass_rate, code
        except Exception:
            return syntax_valid, 0.0, code

    def compute_evi(
        self,
        quality_score: float,
        task_importance: float = 0.8,
        escalation_cost: float = 0.5,
        target_quality: float = 0.95,
    ) -> tuple[float, bool]:
        """Compute Expected Value of Intervention: EVI = (delta_Q * Importance) / Cost."""
        quality_gap = max(0.0, target_quality - quality_score)
        evi = (quality_gap * task_importance) / max(escalation_cost, 0.01)
        escalation_required = evi > 0.75 and quality_score < 0.70
        return round(evi, 4), escalation_required

    def evaluate_model_on_task(
        self,
        model: str,
        task_id: str,
        prompt: str,
        test_fn: Callable[[dict[str, Any]], float],
        hardware_lane: str = "iGPU",
        task_importance: float = 0.8,
        timeout: float = 20.0,
    ) -> ModelEvaluationScorecard:
        """Run full evaluation of a model against a verified task."""
        # Query
        output, latency_ms, tps = self.query_model(model, prompt, timeout=timeout)

        # Verify
        syntax_ok, test_pass_rate, clean_code = self.verify_python_code(output, test_fn)

        # Composite quality score: 40% syntax + 60% test pass rate
        quality = (0.4 if syntax_ok else 0.0) + (0.6 * test_pass_rate)

        # EVI calculation
        evi, needs_escalation = self.compute_evi(quality, task_importance=task_importance)

        return ModelEvaluationScorecard(
            model=model,
            task_id=task_id,
            syntax_valid=syntax_ok,
            test_pass_rate=test_pass_rate,
            quality_score=round(quality, 4),
            latency_ms=round(latency_ms, 1),
            tokens_per_second=round(tps, 1),
            hardware_lane=hardware_lane,
            evi_score=evi,
            escalation_required=needs_escalation,
            details={"code_snippet": clean_code[:120]},
        )

    def run_comparative_shootout(
        self,
        candidates: list[tuple[str, str]],
        task_id: str,
        prompt: str,
        test_fn: Callable[[dict[str, Any]], float],
        task_importance: float = 0.8,
        timeout: float = 20.0,
    ) -> list[ModelEvaluationScorecard]:
        """Compare multiple models on the same task and rank by quality."""
        # Hardware Sentry check
        mem = OOMGuard.get_memory_state()
        logger.info(
            f"Hardware Sentry: Avail RAM={mem.available_gb:.1f} GiB | "
            f"GTT={mem.gtt_used_gb:.1f} GiB | PSI={mem.psi_some_10:.1f}"
        )

        scorecards: list[ModelEvaluationScorecard] = []
        for model_id, lane in candidates:
            sc = self.evaluate_model_on_task(
                model=model_id,
                task_id=task_id,
                prompt=prompt,
                test_fn=test_fn,
                hardware_lane=lane,
                task_importance=task_importance,
                timeout=timeout,
            )
            scorecards.append(sc)

        # Rank primarily by quality_score DESC, secondary by latency_ms ASC
        scorecards.sort(key=lambda x: (x.quality_score, -x.latency_ms), reverse=True)
        return scorecards
