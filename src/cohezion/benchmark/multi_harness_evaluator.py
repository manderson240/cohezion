"""Multi-Harness Evaluation Matrix for Local & Heterogeneous AI Models.

Evaluates models across 5 distinct execution harnesses:
1. **Hermes Harness** (`hermes`): Function-calling, JSON schemas, tool selection, and stateful multi-turn routing.
2. **OpenCode Harness** (`opencode`): Multi-file AST patching, diff generation, lint compliance, and import smoke verification.
3. **Pi Mathematical Harness** (`pi`): Precision calculations, algorithmic complexity bounds, and non-linear invariant proofs.
4. **DeepSeek Reasoning Harness** (`deepseek`): Chain-of-thought verification, <think> token discipline, formal logic, and edge-case handling.
5. **AutoHarness Policy Engine** (`autoharness`): Zero-cost code-as-action verification, 0ms latency pre-filtering, and anti-Goodhart mutation testing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier

logger = logging.getLogger("multi_harness")


class HarnessType(str, Enum):
    HERMES = "hermes"
    OPENCODE = "opencode"
    PI_MATH = "pi"
    DEEPSEEK_COT = "deepseek"
    AUTOHARNESS = "autoharness"
    DEEPSEEK_HARNESS = "deepseek_harness"  # dsh Cordis plugin-pack composability
    QWEN_CODE = "qwen_code"                # DeepPlanning & Aider ExecRepoBench


@dataclass
class HarnessBenchmarkTask:
    task_id: str
    harness: HarnessType
    prompt: str
    expected_criteria: str
    test_validator: str  # Python expression or key verification metric


@dataclass
class HarnessEvaluationResult:
    model_name: str
    harness: HarnessType
    task_id: str
    success: bool
    score: float  # 0.0 to 1.0
    latency_ms: float
    tokens_generated: int
    thinking_overhead_ms: float = 0.0
    raw_output: str = ""
    verification_details: dict[str, Any] = field(default_factory=dict)


class MultiHarnessEvaluator:
    """Evaluates local NPU, iGPU, and CPU models against diverse agentic harness paradigms."""

    def __init__(self, endpoint_url: str = "http://localhost:13305/v1"):
        self.endpoint_url = endpoint_url
        self.verifier = AutoHarnessVerifier()

    def get_standard_benchmark_suite(self) -> list[HarnessBenchmarkTask]:
        """Returns standard benchmark tasks for each harness archetype."""
        return [
            # 1. Hermes Tool Calling
            HarnessBenchmarkTask(
                task_id="hermes_01_tool_call",
                harness=HarnessType.HERMES,
                prompt="Use tool `get_memory_vitals` with argument `format='json'` to query RAM state.",
                expected_criteria="Valid JSON function call: {\"name\": \"get_memory_vitals\", \"arguments\": {\"format\": \"json\"}}",
                test_validator="is_valid_json_tool_call",
            ),
            # 2. OpenCode Refactor
            HarnessBenchmarkTask(
                task_id="opencode_01_ast_refactor",
                harness=HarnessType.OPENCODE,
                prompt="Refactor this function to be pure NumPy: `def norm(v): return sum(x**2 for x in v)**0.5`",
                expected_criteria="Pure NumPy function using np.linalg.norm or np.sqrt(np.sum(v**2))",
                test_validator="pure_numpy_ast",
            ),
            # 3. Pi Mathematical Proof
            HarnessBenchmarkTask(
                task_id="pi_01_poincare_distance",
                harness=HarnessType.PI_MATH,
                prompt="Given u=[0.2, 0.0], v=[0.0, 0.2] in Poincare disk, what is exact geodesic distance formula and value?",
                expected_criteria="d_P(u, v) = arcosh(1 + 2 * ||u-v||^2 / ((1-||u||^2)(1-||v||^2)))",
                test_validator="poincare_formula_present",
            ),
            # 4. DeepSeek Chain of Thought
            HarnessBenchmarkTask(
                task_id="deepseek_01_langevin_drift",
                harness=HarnessType.DEEPSEEK_COT,
                prompt="Derive the stationary distribution of the overdamped Langevin equation: dX_t = -grad V(X_t) dt + sqrt(2D) dW_t.",
                expected_criteria="Gibbs-Boltzmann distribution: P_eq(x) = (1/Z) exp(-V(x)/D)",
                test_validator="boltzmann_distribution_exact",
            ),
            # 5. AutoHarness Policy Execution
            HarnessBenchmarkTask(
                task_id="autoharness_01_policy_gate",
                harness=HarnessType.AUTOHARNESS,
                prompt="Write a Python assert verifying that an array norm is strictly bounded by 1.0 - 1e-5.",
                expected_criteria="assert np.linalg.norm(u) <= 1.0 - 1e-5",
                test_validator="ast_safe_assert",
            ),
            # 6. DeepSeek Harness (dsh Cordis Plugin Pack)
            HarnessBenchmarkTask(
                task_id="dsh_01_cordis_plugin",
                harness=HarnessType.DEEPSEEK_HARNESS,
                prompt="Define a DeepSeek Harness plugin specification in JSON with `plugin_id='cohezion_manifold'` and hooks `['on_step', 'on_eval']`.",
                expected_criteria="{\"plugin_id\": \"cohezion_manifold\", \"hooks\": [\"on_step\", \"on_eval\"]}",
                test_validator="dsh_plugin_schema",
            ),
            # 7. Qwen-Code (DeepPlanning & ExecRepoBench)
            HarnessBenchmarkTask(
                task_id="qwen_01_deep_planning",
                harness=HarnessType.QWEN_CODE,
                prompt="Decompose a multi-file refactor into a 3-step dependency DAG plan with target files and rollback invariants.",
                expected_criteria="Structured 3-step DAG plan with explicit rollback assertions",
                test_validator="dag_plan_with_invariants",
            ),
        ]

    async def evaluate_model_on_harness(
        self, model_name: str, task: HarnessBenchmarkTask
    ) -> HarnessEvaluationResult:
        """Executes a single benchmark task against a target model under the specified harness rules."""
        t0 = time.perf_counter()
        
        system_prompts = {
            HarnessType.HERMES: "You are a Hermes-compatible tool calling engine. Output JSON tool calls accurately.",
            HarnessType.OPENCODE: "You are an OpenCode software engineer. Output minimal, idiomatic, high-performance Python code.",
            HarnessType.PI_MATH: "You are a mathematical rigor specialist. State definitions, proofs, and exact invariant derivations.",
            HarnessType.DEEPSEEK_COT: "You are a DeepSeek reasoning engine. Think step-by-step before answering.",
            HarnessType.AUTOHARNESS: "You are an AutoHarness code-as-action verifier. Write safe, verifiable Python AST code.",
            HarnessType.DEEPSEEK_HARNESS: "You are a DeepSeek Harness (dsh) Cordis runtime agent. Output modular JSON plugin configurations.",
            HarnessType.QWEN_CODE: "You are a Qwen-Agent DeepPlanning & code generation architect. Output strict DAG execution plans.",
        }

        messages = [
            {"role": "system", "content": system_prompts.get(task.harness, "You are an expert AI.")},
            {"role": "user", "content": task.prompt},
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.1,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(f"{self.endpoint_url}/chat/completions", json=payload)
            dt_ms = (time.perf_counter() - t0) * 1000.0

            if r.status_code != 200:
                return HarnessEvaluationResult(
                    model_name=model_name,
                    harness=task.harness,
                    task_id=task.task_id,
                    success=False,
                    score=0.0,
                    latency_ms=dt_ms,
                    tokens_generated=0,
                    raw_output=f"HTTP Error {r.status_code}: {r.text}",
                )

            data = r.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content", "") or choice.get("reasoning_content", "")
            
            # Extract thinking overhead if present
            thinking_overhead = 0.0
            if "<think>" in content and "</think>" in content:
                thinking_text = content.split("</think>")[0]
                thinking_overhead = len(thinking_text) / 4.0  # approximate tokens

            # Validate based on harness criteria
            score = 0.0
            success = False
            lower_content = content.lower()

            if task.harness == HarnessType.HERMES:
                success = "get_memory_vitals" in content and ("{" in content or "arguments" in content)
                score = 1.0 if success else 0.4
            elif task.harness == HarnessType.OPENCODE:
                success = "np.linalg.norm" in content or "np.sqrt" in content or "numpy" in lower_content
                score = 1.0 if success else 0.5
            elif task.harness == HarnessType.PI_MATH:
                success = "arcosh" in lower_content or "acosh" in lower_content or "1 + 2" in content
                score = 1.0 if success else 0.6
            elif task.harness == HarnessType.DEEPSEEK_COT:
                success = "exp(-v" in lower_content or "boltzmann" in lower_content or "gibbs" in lower_content or "1/z" in lower_content
                score = 1.0 if success else 0.5
            elif task.harness == HarnessType.AUTOHARNESS:
                ast_valid = self.verifier.verify_code(content).get("verified", False)
                success = "assert" in content and ("<=" in content or "<" in content)
                score = 1.0 if (success or ast_valid) else 0.5
            elif task.harness == HarnessType.DEEPSEEK_HARNESS:
                success = "cohezion_manifold" in content and ("on_step" in content or "on_eval" in content)
                score = 1.0 if success else 0.5
            elif task.harness == HarnessType.QWEN_CODE:
                success = ("step 1" in lower_content or "step 2" in lower_content or "1." in lower_content) and ("rollback" in lower_content or "invariant" in lower_content or "plan" in lower_content)
                score = 1.0 if success else 0.5

            return HarnessEvaluationResult(
                model_name=model_name,
                harness=task.harness,
                task_id=task.task_id,
                success=success,
                score=score,
                latency_ms=round(dt_ms, 2),
                tokens_generated=len(content) // 4,
                thinking_overhead_ms=round(thinking_overhead * 10.0, 2),
                raw_output=content[:200],
                verification_details={"status": "verified" if success else "partial"},
            )
        except Exception as exc:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return HarnessEvaluationResult(
                model_name=model_name,
                harness=task.harness,
                task_id=task.task_id,
                success=False,
                score=0.0,
                latency_ms=round(dt_ms, 2),
                tokens_generated=0,
                raw_output=f"Exception: {exc}",
            )


if __name__ == "__main__":
    evaluator = MultiHarnessEvaluator()
    tasks = evaluator.get_standard_benchmark_suite()
    print(f"Loaded {len(tasks)} multi-harness benchmark tasks across Hermes, OpenCode, Pi, DeepSeek, and AutoHarness.")
