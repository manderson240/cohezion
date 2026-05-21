"""
AutoHarness: automatically synthesizes a code harness (or policy)
using iterative code refinement given feedback from an environment.
Based on Lou et al., "AutoHarness: improving LLM agents by automatically synthesizing a code harness"
"""

import logging
import re
from collections.abc import Callable


logger = logging.getLogger(__name__)

_CODE_RE = re.compile(r"```python\n(.*?)\n```", re.DOTALL)

_VERIFIER_SYSTEM = (
    "You are an expert Python developer specializing in constraint verification. "
    "Return ONLY executable Python code inside ```python ... ``` blocks. "
    "No explanations, no test code, no example usage."
)

_POLICY_SYSTEM = (
    "You are an expert Python developer specializing in deterministic decision policies. "
    "Return ONLY executable Python code inside ```python ... ``` blocks. "
    "No explanations, no test code, no example usage."
)


def _extract_code(response_text: str) -> str:
    match = _CODE_RE.search(response_text)
    if match:
        return match.group(1)
    if "def " in response_text:
        return response_text
    return response_text


def _response_text(response: object) -> str:
    if hasattr(response, "output"):
        return response.output  # type: ignore[union-attr]
    if hasattr(response, "text"):
        return response.text  # type: ignore[union-attr]
    return str(response)


class AutoHarnessSynthesizer:
    def __init__(self, llm_executor, max_iterations: int = 5, initial_candidates: int = 1):
        """
        Args:
            llm_executor: An instance of an LLM executor implementing either
                          ``execute_task(task, skill)`` (sequential path) or
                          ``batch_execute(requests)`` (parallel fast path).
            max_iterations: Maximum sequential refinement loops after initial pass.
            initial_candidates: How many independent first-pass candidates to
                generate in parallel before falling through to sequential refinement.
                Values > 1 require the executor to support ``batch_execute``.
                Uses HybridExecutor.batch_execute → Anthropic Batches API when
                provider=anthropic, asyncio.gather otherwise.
        """
        self.llm = llm_executor
        self.max_iterations = max_iterations
        self.initial_candidates = initial_candidates
        self._supports_batch = hasattr(llm_executor, "batch_execute")

    async def _batch_initial(
        self,
        prompt: str,
        system: str,
        n: int,
        dummy_env: Callable[[str], tuple[bool, str]],
    ) -> tuple[str | None, str]:
        """Generate n independent candidates in parallel; return first success.

        Returns (successful_code, last_code_seen). successful_code is None if
        all candidates failed — caller falls through to sequential refinement.
        """
        requests = [
            {
                "custom_id": f"candidate_{i}",
                "prompt": prompt,
                "system": system,
                "max_tokens": 1024,
                "temperature": 0.8,  # diversity across candidates
            }
            for i in range(n)
        ]
        try:
            results = await self.llm.batch_execute(requests)
        except Exception as exc:
            logger.warning("[AutoHarness] batch_execute failed, falling back: %s", exc)
            return None, ""

        last_code = ""
        for res in results:
            text = res.output if hasattr(res, "output") else res.get("output", "")
            code = _extract_code(text)
            last_code = code
            success, _ = dummy_env(code)
            if success:
                cache_read = (
                    getattr(res, "cache_read_tokens", None)
                    if not isinstance(res, dict)
                    else res.get("cache_read_tokens", 0)
                ) or 0
                logger.info(
                    "[AutoHarness] Parallel candidate succeeded (cache_read=%d tokens)", cache_read
                )
                return code, code

        return None, last_code

    async def synthesize_verifier(
        self, environment_desc: str, dummy_env: Callable[[str], tuple[bool, str]]
    ) -> str:
        """Synthesize ``def verify_action(state, action) -> bool:``.

        When initial_candidates > 1 and the executor supports batch_execute,
        fires that many independent first-pass attempts in parallel (via
        HybridExecutor.batch_execute → Anthropic Batches API). The first
        successful candidate is returned immediately, skipping all sequential
        refinement. Falls through to sequential refinement if all parallel
        attempts fail or if batch_execute is unavailable.
        """
        initial_prompt = (
            f"Based on the following environment description, "
            f"write a Python function `def verify_action(state, action) -> bool:` "
            f"that returns True if the action is valid in the given state, False otherwise.\n\n"
            f"Environment:\n{environment_desc}"
        )

        code = ""

        # ── Parallel fast path ──────────────────────────────────────────────
        if self.initial_candidates > 1 and self._supports_batch:
            logger.info(
                "[AutoHarness] Launching %d parallel verifier candidates via batch_execute",
                self.initial_candidates,
            )
            winner, code = await self._batch_initial(
                initial_prompt, _VERIFIER_SYSTEM, self.initial_candidates, dummy_env
            )
            if winner is not None:
                return winner

        # ── Sequential refinement ────────────────────────────────────────────
        prompt = initial_prompt
        for i in range(self.max_iterations):
            logger.info("[AutoHarness] Verifier iteration %d/%d", i + 1, self.max_iterations)
            try:
                response = await self.llm.execute_task(task=prompt, skill="coding_PRIME")
                code = _extract_code(_response_text(response))
                success, feedback = dummy_env(code)
                if success:
                    logger.info("[AutoHarness] Verifier synthesis successful.")
                    return code
                prompt = (
                    f"The previous code failed:\n{feedback}\n\n"
                    f"Refine `def verify_action(state, action) -> bool:`. "
                    f"Return ONLY python code inside ```python ... ``` blocks."
                )
            except Exception as e:
                logger.error("[AutoHarness] LLM execution failed: %s", e)
                prompt = f"Previous attempt raised: {e}. Try again. Return ONLY python code."

        logger.warning("[AutoHarness] Reached max iterations without success.")
        return code

    async def synthesize_policy(
        self, environment_desc: str, dummy_env: Callable[[str], tuple[bool, str]]
    ) -> str:
        """Synthesize ``def predict_action(state) -> action:``.

        Same parallel fast path as synthesize_verifier when initial_candidates > 1.
        """
        initial_prompt = (
            f"Write a full deterministic policy function `def predict_action(state):` "
            f"for the environment.\n\nEnvironment:\n{environment_desc}"
        )

        code = ""

        # ── Parallel fast path ──────────────────────────────────────────────
        if self.initial_candidates > 1 and self._supports_batch:
            logger.info(
                "[AutoHarness] Launching %d parallel policy candidates via batch_execute",
                self.initial_candidates,
            )
            winner, code = await self._batch_initial(
                initial_prompt, _POLICY_SYSTEM, self.initial_candidates, dummy_env
            )
            if winner is not None:
                return winner

        # ── Sequential refinement ────────────────────────────────────────────
        prompt = initial_prompt
        for i in range(self.max_iterations):
            logger.info("[AutoHarness] Policy iteration %d/%d", i + 1, self.max_iterations)
            try:
                response = await self.llm.execute_task(task=prompt, skill="coding_PRIME")
                text = _response_text(response)
                code = _extract_code(text)
                success, feedback = dummy_env(code)
                if success:
                    logger.info("[AutoHarness] Policy synthesis successful.")
                    return code
                prompt = (
                    f"The previous policy failed:\n{feedback}\n\n"
                    f"Refine `def predict_action(state):`. "
                    f"Return ONLY python code inside ```python ... ``` blocks."
                )
            except Exception as e:
                logger.error("[AutoHarness] LLM execution failed: %s", e)
                prompt = f"Previous attempt raised: {e}. Try again. Return ONLY python code."

        logger.warning("[AutoHarness] Reached max iterations without success.")
        return code
