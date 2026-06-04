# urllib to localhost Lemonade — S310/S112 are false positives here
"""Reflection-based optimizer for Cohezion skill Variables.

Adapted from Autogenesis ReflectionOptimizer (Zhang et al., 2026).
Uses Lemonade (local Ollama/GPU) instead of cloud models to iterate on
PRIME skill sections using natural language feedback as text gradients.

Algorithm:
  1. Gather feedback (text gradients) about what the current skill does wrong
  2. Ask a local LLM to propose improved versions of trainable sections
  3. Verify the improvement satisfies the feedback criteria
  4. Commit if satisfied, otherwise iterate (up to max_steps)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from cohezion.evolution.variable import Variable


logger = logging.getLogger(__name__)

# Lemonade/Ollama endpoint — falls back to GPU tier
_LEMONADE_URLS = [
    "http://localhost:13307",  # Governance lane (Gemma-4-E4B)
    "http://localhost:13305",  # GPU tier
    "http://localhost:11434",  # Ollama fallback
]


@dataclass
class OptimizationResult:
    """Result of a single optimization step."""

    variable_name: str
    old_value: str
    new_value: str
    reasoning: str
    satisfied: bool
    step: int


class ReflectionOptimizer:
    """Iteratively improve skill Variables using LLM reflection.

    Implements the Autogenesis SEPL propose→assess→commit loop
    using local Lemonade inference (no cloud API required).

    Usage::

        opt = ReflectionOptimizer(model="gemma3:4b", max_steps=3)
        results = opt.optimize(
            variables=[skill_var],
            task="improve routing accuracy for code-generation prompts",
            feedback=["missed 'import X' patterns", "false-positive on prose 'class'"],
        )
    """

    def __init__(
        self,
        model: str = "gemma3:4b",
        max_steps: int = 3,
        min_improvement_threshold: float = 0.1,
    ) -> None:
        self.model = model
        self.max_steps = max_steps
        self.min_improvement_threshold = min_improvement_threshold
        self._client_url: str | None = None

    def _get_client_url(self) -> str | None:
        """Find an available Lemonade/Ollama endpoint."""
        if self._client_url:
            return self._client_url
        try:
            import urllib.request

            for url in _LEMONADE_URLS:
                try:
                    urllib.request.urlopen(f"{url}/api/tags", timeout=1)
                    self._client_url = url
                    return url
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _call_llm(self, prompt: str, url: str) -> str:
        """Call Ollama-compatible API and return the response text."""
        import json
        import urllib.request

        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 1024},
            }
        ).encode()

        req = urllib.request.Request(
            f"{url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["response"].strip()

    def _build_improve_prompt(self, var: Variable, task: str) -> str:
        feedback_text = var.get_gradient_text() or "(no specific feedback yet)"
        history_text = ""
        if var.history:
            last = var.history[-1]
            history_text = f"\nPrevious attempt reasoning: {last['reasoning']}"
        return f"""You are improving a section of an AI skill definition.

## Task
{task}

## Current section: {var.name}
{var.description}

Current content:
<current>
{var.value}
</current>

## Feedback (what to improve)
{feedback_text}
{history_text}

## Instructions
Rewrite the section to address the feedback. Be specific and concrete.
Output ONLY the improved content — no preamble, no explanation, no XML tags.
Keep the same format/structure as the original."""

    def _build_assess_prompt(self, var: Variable, new_value: str, task: str) -> str:
        feedback_text = var.get_gradient_text() or "(no specific feedback)"
        return f"""Assess whether this improved skill section adequately addresses the feedback.

## Task
{task}

## Feedback that needed to be addressed
{feedback_text}

## Original
{var.value}

## Proposed improvement
{new_value}

Does the improvement address the feedback? Answer with JSON only:
{{"satisfied": true/false, "reasoning": "one sentence"}}"""

    def optimize(
        self,
        variables: list[Variable],
        task: str,
        feedback: list[str] | None = None,
    ) -> list[OptimizationResult]:
        """Run the propose→assess→commit loop for each trainable variable.

        Args:
            variables: List of Variables to optimize (only require_grad=True are touched)
            task: What skill improvement we're attempting
            feedback: Additional feedback strings (added as gradients)

        Returns:
            List of OptimizationResult, one per variable per step
        """
        url = self._get_client_url()
        if not url:
            logger.warning("No Lemonade/Ollama endpoint available; skipping optimization")
            return []

        trainable = [v for v in variables if v.require_grad]
        if not trainable:
            logger.debug("No trainable variables; skipping optimization")
            return []

        # Inject external feedback as gradients
        if feedback:
            for var in trainable:
                for fb in feedback:
                    var.add_gradient(fb)

        results: list[OptimizationResult] = []

        for var in trainable:
            if not var.get_gradient_text():
                logger.debug("Variable %s has no gradients; skipping", var.name)
                continue

            for step in range(1, self.max_steps + 1):
                try:
                    # Propose
                    improve_prompt = self._build_improve_prompt(var, task)
                    new_value = self._call_llm(improve_prompt, url)

                    if not new_value or new_value == var.value:
                        logger.debug("Step %d: no change proposed for %s", step, var.name)
                        break

                    # Assess
                    assess_prompt = self._build_assess_prompt(var, new_value, task)
                    assess_raw = self._call_llm(assess_prompt, url)

                    satisfied = False
                    reasoning = assess_raw
                    try:
                        # Try to parse JSON assessment
                        assess_json = json.loads(assess_raw)
                        satisfied = bool(assess_json.get("satisfied", False))
                        reasoning = assess_json.get("reasoning", assess_raw)
                    except (json.JSONDecodeError, ValueError):
                        satisfied = "true" in assess_raw.lower()

                    # Commit
                    old_value = var.value
                    var.record_update(old_value, new_value, reasoning)
                    var.value = new_value

                    result = OptimizationResult(
                        variable_name=var.name,
                        old_value=old_value,
                        new_value=new_value,
                        reasoning=reasoning,
                        satisfied=satisfied,
                        step=step,
                    )
                    results.append(result)
                    logger.info(
                        "Step %d/%d for %s: satisfied=%s | %s",
                        step,
                        self.max_steps,
                        var.name,
                        satisfied,
                        reasoning[:80],
                    )

                    if satisfied:
                        break

                except Exception as e:
                    logger.warning("Optimization step %d failed for %s: %s", step, var.name, e)
                    break

        return results
