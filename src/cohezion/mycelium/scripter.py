import logging
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig


logger = logging.getLogger(__name__)


class ShadowScripter(BaseAgent):
    """
    Agent responsible for synthesizing regression tests for new code.
    """

    def __init__(self, model_name: str = "qwen3-coder", config: SwarmConfig | None = None, **kwargs):
        super().__init__(model_name, config, **kwargs)

    async def synthesize_test_suite(self, file_path: str, code_context: str) -> str:
        """
        Generates a pytest suite for the given code context.

        Args:
            file_path: The path to the file being tested.
            code_context: The source code or diff context.

        Returns:
            str: The generated test code.
        """
        prompt = f"""
        ACT AS AN EXPERT QA ENGINEER.
        Generate a comprehensive set of pytest unit tests for the following code in {file_path}:

        CODE CONTEXT:
        {code_context}

        REQUIREMENTS:
        1. Use pytest framework.
        2. Aim for 100% logic coverage.
        3. Include mock objects for external dependencies (SurrealDB, Obsidian, etc.) if necessary.
        4. Provide only the python code for the tests.
        """

        logger.info(f"ShadowScripter synthesizing tests for {file_path}...")
        test_code = await self._call_ollama(prompt)

        return test_code

    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """
        Implementation of the required BaseAgent process method.
        """
        file_path = kwargs.get("file_path", "unknown.py")
        code_context = kwargs.get("code_context", "")
        return await self.synthesize_test_suite(file_path, code_context)
