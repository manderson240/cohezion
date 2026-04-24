# ruff: noqa: B904  # raise pattern in HTTP/API handlers — explicit user-facing errors
"""LLM Executor for autonomous compound benchmarking.

Uses Ollama cloud models to execute benchmark tasks and evaluate
skill performance with real LLM judgments.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)


DEFAULT_CLOUD_MODEL = "qwen3.5:cloud"
DEFAULT_JUDGE_MODEL = "qwen3.5:cloud"
OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass
class LLMExecutionResult:
    """Result from LLM execution."""

    success: bool
    output: str
    coherence: float
    alignment: float
    latency_ms: float
    model: str
    error: str | None = None


class LLMExecutor:
    """Execute benchmark tasks via Ollama cloud models.

    Uses cloud models (qwen3.5:cloud, minimax-m2.7:cloud, etc.)
    for task execution and coherence evaluation.

    Parameters
    ----------
    model : str
        Cloud model to use (default: qwen3.5:cloud)
    judge_model : str
        Model to use for coherence judgment
    ollama_base_url : str
        Ollama API base URL
    timeout : float
        Request timeout in seconds

    Examples
    --------
    >>> executor = LLMExecutor(model="qwen3.5:cloud")
    >>> result = await executor.execute_task(
    ...     task="Write a factorial function",
    ...     skill="python_PRIME"
    ... )
    >>> print(f"Coherence: {result.coherence:.2f}")
    """

    def __init__(
        self,
        model: str = DEFAULT_CLOUD_MODEL,
        judge_model: str | None = None,
        ollama_base_url: str = OLLAMA_BASE_URL,
        timeout: float = 60.0,
    ) -> None:
        """Initialize LLM executor."""
        self.model = model
        self.judge_model = judge_model or model
        self.ollama_base_url = ollama_base_url
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def execute_task(
        self,
        task: str,
        skill: str,
        context: str | None = None,
    ) -> LLMExecutionResult:
        """Execute a benchmark task via LLM.

        Parameters
        ----------
        task : str
            Task description to execute
        skill : str
            Skill name being benchmarked
        context : str, optional
            Additional context for execution

        Returns
        -------
        LLMExecutionResult
            Execution result with coherence score
        """
        start_time = time.monotonic()

        try:
            execution_prompt = self._build_execution_prompt(task, skill, context)
            response = await self._generate(execution_prompt, self.model)

            coherence_prompt = self._build_coherence_prompt(task, response, skill)
            coherence_response = await self._generate(coherence_prompt, self.judge_model)
            coherence = self._parse_coherence(coherence_response)

            latency_ms = (time.monotonic() - start_time) * 1000

            return LLMExecutionResult(
                success=True,
                output=response,
                coherence=coherence,
                alignment=0.7,
                latency_ms=latency_ms,
                model=self.model,
            )

        except Exception as e:
            logger.warning("LLM execution failed: %s", e)
            latency_ms = (time.monotonic() - start_time) * 1000
            return LLMExecutionResult(
                success=False,
                output="",
                coherence=0.0,
                alignment=0.0,
                latency_ms=latency_ms,
                model=self.model,
                error=str(e),
            )

    async def execute_batch(
        self,
        tasks: list[dict[str, str]],
    ) -> list[LLMExecutionResult]:
        """Execute multiple tasks in parallel.

        Parameters
        ----------
        tasks : list[dict[str, str]]
            List of task dicts with 'task' and 'skill' keys

        Returns
        -------
        list[LLMExecutionResult]
            Results for each task
        """
        results = await asyncio.gather(
            *[self.execute_task(t["task"], t["skill"]) for t in tasks],
            return_exceptions=True,
        )

        processed = []
        for _i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(
                    LLMExecutionResult(
                        success=False,
                        output="",
                        coherence=0.0,
                        alignment=0.0,
                        latency_ms=0.0,
                        model=self.model,
                        error=str(result),
                    )
                )
            else:
                processed.append(result)

        return processed

    async def _generate(
        self,
        prompt: str,
        model: str,
        system: str | None = None,
        max_retries: int = 3,
    ) -> str:
        """Generate response from Ollama model with retry.

        Parameters
        ----------
        prompt : str
            Input prompt
        model : str
            Model name
        system : str, optional
            System prompt
        max_retries : int
            Maximum retry attempts

        Returns
        -------
        str
            Model response
        """
        url = f"{self.ollama_base_url}/api/generate"

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7},
        }

        if system:
            payload["system"] = system

        last_error = None
        for attempt in range(max_retries):
            try:
                response = await self._client.post(url, json=payload, timeout=30.0)
                if response.status_code != 200:
                    logger.warning(
                        "Ollama returned %d on attempt %d", response.status_code, attempt + 1
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    response.raise_for_status()

                data = response.json()
                return data.get("response", "")

            except httpx.TimeoutException:
                last_error = f"Timeout calling {model}"
                logger.warning("Ollama timeout on attempt %d/%d", attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise RuntimeError(last_error)

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP error calling {model}: {e}"
                logger.warning(
                    "Ollama HTTP error on attempt %d/%d: %s", attempt + 1, max_retries, e
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise RuntimeError(last_error)

            except Exception as e:
                last_error = f"Error calling {model}: {e}"
                logger.warning("Ollama error on attempt %d/%d: %s", attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise RuntimeError(last_error)

        raise RuntimeError(last_error or f"Failed after {max_retries} attempts")

    def _build_execution_prompt(
        self,
        task: str,
        skill: str,
        context: str | None,
    ) -> str:
        """Build execution prompt for task.

        Parameters
        ----------
        task : str
            Task description
        skill : str
            Skill name
        context : str, optional
            Additional context

        Returns
        -------
        str
            Formatted prompt
        """
        return f"""You are a helpful assistant with expertise in {skill}.

Task: {task}

{context or ""}

Provide a clear, well-structured response that demonstrates the skill's principles."""

    def _build_coherence_prompt(
        self,
        task: str,
        response: str,
        skill: str,
    ) -> str:
        """Build coherence evaluation prompt.

        Parameters
        ----------
        task : str
            Original task
        response : str
            LLM response to evaluate
        skill : str
            Skill name

        Returns
        -------
        str
            Evaluation prompt
        """
        return f"""Evaluate the following response for coherence with the skill "{skill}".

Task: {task}

Response: {response}

Rate the coherence of this response on a scale of 0.0 to 1.0, where:
- 0.0 means the response is completely incoherent or irrelevant to the skill
- 0.5 means the response is partially coherent with some issues
- 1.0 means the response is highly coherent and demonstrates excellent skill application

Respond ONLY with a single number between 0.0 and 1.0 (example: 0.75)"""

    def _parse_coherence(self, coherence_response: str) -> float:
        """Parse coherence score from model response.

        Parameters
        ----------
        coherence_response : str
            Raw model response

        Returns
        -------
        float
            Coherence score 0.0 to 1.0
        """
        text = coherence_response.strip()

        numbers = re.findall(r"0?\.\d+|1\.0+", text)
        if numbers:
            score = float(numbers[0])
            return max(0.0, min(1.0, score))

        words_positive = ["high", "excellent", "good", "strong", "coherent"]
        words_negative = ["low", "poor", "weak", "incoherent", "bad"]

        text_lower = text.lower()
        if any(w in text_lower for w in words_positive):
            return 0.7
        elif any(w in text_lower for w in words_negative):
            return 0.3

        return 0.5

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> LLMExecutor:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Async context manager exit."""
        await self.close()
