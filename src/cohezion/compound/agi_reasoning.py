"""
AGI Reasoning Framework (2026 SOTA).
Implements Policy Synthesis (AutoHarness) and Topological Routing for cognitive tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from cohezion.compound.autoharness import AutoHarnessSynthesizer
from cohezion.compound.symbolic_executor import SymbolicExecutor
from cohezion.flume.embedding_provider import AsyncOllamaEmbeddingProvider
from cohezion.flume.tda_detector import TDADetector
from cohezion.reliability.viscoelastic import ViscoelasticController


logger = logging.getLogger(__name__)


class ReasoningModel(Protocol):
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str: ...


@dataclass
class AGINode:
    id: str
    content: str
    parent_id: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AGIEvaluator:
    def __init__(self, model: ReasoningModel):
        self.model = model
        self.executor = SymbolicExecutor()
        self.tda = TDADetector()
        self.embedder = AsyncOllamaEmbeddingProvider()
        self.viscous = ViscoelasticController(relaxation_tau=10.0)

        class ExecutorShim:
            def __init__(self, model):
                self.model = model

            async def execute_task(self, task, skill=None):
                res = await self.model.generate(task)

                class Resp:
                    def __init__(self, text):
                        self.text = text

                return Resp(res)

        self.harness = AutoHarnessSynthesizer(llm_executor=ExecutorShim(self.model))

    async def evaluate_task(self, task_description: str, track: str) -> str:
        """
        Evaluates a cognitive task using SOTA 2026 strategies.
        track: 'learning', 'metacognition', 'attention', 'executive_function', 'social'
        """
        logger.info("Evaluating AGI Task (Track: %s): %s", track, task_description[:50])

        # 1. Resource Dilation
        v_adj = self.viscous.calculate_dilation_adjustment(cpu=30, ram=30, vram=30, active_calls=1)

        # 2. Strategy Selection
        if track in ["learning", "executive_function"]:
            # Use AutoHarness to synthesize a deterministic policy/harness
            return await self._solve_via_policy_synthesis(task_description)
        else:
            # Use TDA-Gated Reasoning
            return await self._solve_via_tda_reasoning(task_description)

    async def _solve_via_policy_synthesis(self, description: str) -> str:
        """Synthesizes a Python policy to solve the task deterministically."""
        logger.info("AGI: Initiating Policy Synthesis (AutoHarness)")

        env_desc = f"Task: {description}"

        def dummy_env(code):
            try:
                exec(code, {"np": np})
                if "predict_action" not in code:
                    return False, "Function predict_action not found."
                return True, "Code compiled."
            except Exception as e:
                return False, str(e)

        policy_code = await self.harness.synthesize_policy(env_desc, dummy_env)

        # Execute the policy
        exec_res = self.executor.execute(f"{policy_code}\nresult = predict_action({{}})")

        if exec_res["success"]:
            return f"Policy Result: {exec_res['results'].get('result')}"
        else:
            return f"Policy Failed: {exec_res.get('error')}. Falling back to reasoning."

    async def _solve_via_tda_reasoning(self, description: str) -> str:
        """Solves via reasoning but monitors for circular hallucinations."""
        # Multi-turn reasoning loop
        current_context = description
        trajectory = []

        for step in range(3):
            resp = await self.model.generate(
                f"Current Context: {current_context}\nNext Reasoning Step:"
            )

            # Embed and Check TDA
            emb = await self.embedder.embed(resp)
            trajectory.append(emb)

            if self.tda.detect_circular_logic(trajectory):
                logger.error("AGI TDA: Circular logic detected. Injecting entropy.")
                resp = await self.model.generate(
                    f"Context: {current_context}\nYour previous thought was circular. Try a different approach."
                )

            current_context = f"{current_context}\n{resp}"

        final_resp = await self.model.generate(f"Context: {current_context}\nFinal Answer:")
        return final_resp
