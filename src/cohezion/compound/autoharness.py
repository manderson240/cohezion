"""
AutoHarness: automatically synthesizes a code harness (or policy)
using iterative code refinement given feedback from an environment.
Based on Lou et al., "AutoHarness: improving LLM agents by automatically synthesizing a code harness"
"""

import logging
import re
from collections.abc import Callable


logger = logging.getLogger(__name__)


class AutoHarnessSynthesizer:
    def __init__(self, llm_executor, max_iterations: int = 5):
        """
        Args:
            llm_executor: An instance of an LLM executor (e.g., LLMExecutor or similar)
                          that implements `execute_task(task: str, skill: str)`.
            max_iterations: Maximum number of refinement loops.
        """
        self.llm = llm_executor
        self.max_iterations = max_iterations

    async def synthesize_verifier(
        self, environment_desc: str, dummy_env: Callable[[str], tuple[bool, str]]
    ) -> str:
        """
        Synthesizes a python function `def verify_action(state, action) -> bool:`
        that correctly identifies valid moves/actions in the environment.

        Args:
            environment_desc: Text description of the environment rules.
            dummy_env: A callable `dummy_env(code_str) -> (bool, str)` that tests the code
                       and returns (success, error_feedback).
        """
        prompt = f"""You are an expert Python developer.
Based on the following environment description, write a Python function `def verify_action(state, action) -> bool:`
that returns True if the action is valid in the given state, and False otherwise.
Return ONLY the python code inside ```python ... ``` blocks. Do not include any test code or example usage.

Environment:
{environment_desc}
"""
        code = ""
        for i in range(self.max_iterations):
            logger.info(
                f"[AutoHarness] Iteration {i + 1}/{self.max_iterations} for verifier synthesis."
            )

            try:
                response = await self.llm.execute_task(task=prompt, skill="coding_PRIME")

                # Robust extraction from various response types
                if hasattr(response, "output"):
                    response_text = response.output
                elif hasattr(response, "text"):
                    response_text = response.text
                elif isinstance(response, str):
                    response_text = response
                else:
                    response_text = str(response)

                # Extract python code block
                match = re.search(r"```python\n(.*?)\n```", response_text, re.DOTALL)
                code = match.group(1) if match else response_text
                # Fallback: if no code blocks but looks like pure code
                if not match and "def " in code:
                    pass  # use as is

                # Test against the environment
                success, feedback = dummy_env(code)
                if success:
                    logger.info("[AutoHarness] Synthesis successful.")
                    return code

                # Iterative refinement prompt
                prompt = f"""The previous code failed with the following feedback:
{feedback}

Please refine the `def verify_action(state, action) -> bool:` function to fix these errors.
Return ONLY the python code inside ```python ... ``` blocks.
"""
            except Exception as e:
                logger.error(f"[AutoHarness] LLM execution failed: {e}")
                prompt = f"The previous attempt failed due to an execution error: {e}. Please try again. Return ONLY python code."

        logger.warning("[AutoHarness] Reached maximum iterations without complete success.")
        return code

    async def synthesize_policy(
        self, environment_desc: str, dummy_env: Callable[[str], tuple[bool, str]]
    ) -> str:
        """
        Synthesizes a full code-policy `def predict_action(state) -> action:`
        (Harness-as-policy) that eliminates the need for LLM at decision time.
        """
        prompt = f"""You are an expert Python developer.
Write a full deterministic policy function `def predict_action(state):` for the environment.
Return ONLY the python code inside ```python ... ``` blocks.

Environment:
{environment_desc}
"""
        code = ""
        for i in range(self.max_iterations):
            logger.info(
                f"[AutoHarness] Iteration {i + 1}/{self.max_iterations} for policy synthesis."
            )

            try:
                response = await self.llm.execute_task(task=prompt, skill="coding_PRIME")

                if hasattr(response, "text"):
                    response_text = response.text
                elif isinstance(response, str):
                    response_text = response
                else:
                    response_text = str(response)

                match = re.search(r"```python\n(.*?)\n```", response_text, re.DOTALL)
                code = match.group(1) if match else response_text

                success, feedback = dummy_env(code)
                if success:
                    logger.info("[AutoHarness] Policy Synthesis successful.")
                    return code

                prompt = f"""The previous policy code failed with the following feedback:
{feedback}

Please refine the `def predict_action(state):` function.
Return ONLY the python code inside ```python ... ``` blocks.
"""
            except Exception as e:
                logger.error(f"[AutoHarness] LLM execution failed: {e}")
                prompt = f"The previous attempt failed due to an execution error: {e}. Please try again. Return ONLY python code."

        logger.warning("[AutoHarness] Reached maximum iterations without complete success.")
        return code
