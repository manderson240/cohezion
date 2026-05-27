# raise pattern in HTTP/API handlers — explicit user-facing errors
"""LLM Executor for autonomous compound benchmarking.

Uses Ollama cloud models to execute benchmark tasks and evaluate
skill performance with real LLM judgments.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)


DEFAULT_CLOUD_MODEL = "qwen3.5:cloud"
DEFAULT_JUDGE_MODEL = "qwen3.5:cloud"
OLLAMA_BASE_URL = "http://localhost:11434"

# Retry configuration with exponential backoff and jitter
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 60.0
RETRY_BACKOFF_FACTOR = 2.0
RETRY_JITTER_MAX = 2.0

# HTTP status codes that warrant retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = 10  # More tolerant
CIRCUIT_BREAKER_RESET_TIMEOUT_S = 120.0  # Longer recovery


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


class CircuitBreaker:
    """Simple circuit breaker for transient failures.

    Opens after threshold failures, preventing cascading failures.
    Automatically resets after timeout.
    """

    def __init__(
        self,
        threshold: int = CIRCUIT_BREAKER_THRESHOLD,
        reset_timeout: float = CIRCUIT_BREAKER_RESET_TIMEOUT_S,
    ) -> None:
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failure_count: dict[str, int] = {}
        self.last_failure_time: dict[str, float] = {}
        self.open_circuits: set[str] = set()

    def record_failure(self, endpoint: str) -> None:
        """Record a failure for an endpoint."""
        now = time.monotonic()
        self.failure_count[endpoint] = self.failure_count.get(endpoint, 0) + 1
        self.last_failure_time[endpoint] = now

        if self.failure_count[endpoint] >= self.threshold:
            self.open_circuits.add(endpoint)
            logger.warning(f"Circuit breaker OPEN for {endpoint} after {self.threshold} failures")

    def record_success(self, endpoint: str) -> None:
        """Record a success for an endpoint."""
        if endpoint in self.open_circuits:
            self.open_circuits.discard(endpoint)
            self.failure_count[endpoint] = 0
            logger.info(f"Circuit breaker CLOSED for {endpoint}")

    def is_open(self, endpoint: str) -> bool:
        """Check if circuit is open (failing)."""
        if endpoint not in self.open_circuits:
            return False

        # Check if we should reset
        last_fail = self.last_failure_time.get(endpoint, 0)
        if time.monotonic() - last_fail > self.reset_timeout:
            self.open_circuits.discard(endpoint)
            self.failure_count[endpoint] = 0
            logger.info(f"Circuit breaker RESET for {endpoint}")
            return False

        return True


class LLMExecutor:
    """Execute benchmark tasks via Ollama cloud models.

    Uses cloud models (qwen3.5:cloud, minimax-m2.7:cloud, etc.)
    for task execution and coherence evaluation.

    Includes circuit breaker and exponential backoff with jitter
    for resilience against transient cloud failures.

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
        self._circuit_breaker = CircuitBreaker()

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

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * factor^attempt
        delay = RETRY_BASE_DELAY * (RETRY_BACKOFF_FACTOR**attempt)
        # Cap at max delay
        delay = min(delay, RETRY_MAX_DELAY)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, RETRY_JITTER_MAX)
        return delay + jitter

    async def _generate(
        self,
        prompt: str,
        model: str,
        system: str | None = None,
        max_retries: int = 3,
    ) -> str:
        """Generate response from Ollama model with retry.

        Uses exponential backoff with jitter and circuit breaker pattern
        to handle transient cloud failures gracefully.

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

        Raises
        ------
        RuntimeError
            If all retries exhausted or circuit breaker is open
        """
        url = f"{self.ollama_base_url}/api/generate"
        endpoint = f"{self.ollama_base_url}/{model}"

        # Check circuit breaker first
        if self._circuit_breaker.is_open(endpoint):
            raise RuntimeError(f"Circuit breaker open for {endpoint}. Too many recent failures.")

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
                response = await self._client.post(url, json=payload, timeout=120.0)

                if response.status_code == 200:
                    # Success - record and return
                    self._circuit_breaker.record_success(endpoint)
                    data = response.json()
                    return data.get("response", "")

                # Handle non-200 status codes
                error_text = await response.aread()
                error_text_str = (
                    error_text.decode("utf-8", errors="replace")
                    if isinstance(error_text, bytes)
                    else error_text
                )
                error_ref_match = re.search(r"ref:\s*([a-f0-9-]+)", error_text_str)
                error_ref = f" (ref: {error_ref_match.group(1)})" if error_ref_match else ""

                is_retryable = response.status_code in RETRYABLE_STATUS_CODES

                if not is_retryable or attempt == max_retries - 1:
                    # Non-retryable or last attempt failed
                    self._circuit_breaker.record_failure(endpoint)
                    raise RuntimeError(
                        f"Ollama API error {response.status_code}{error_ref}: {error_text[:200]}"
                    )

                # Retryable error - log and retry with backoff
                delay = self._calculate_retry_delay(attempt)
                logger.warning(
                    "Ollama returned %d%s on attempt %d/%d, retrying in %.1fs",
                    response.status_code,
                    error_ref,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                self._circuit_breaker.record_failure(endpoint)
                await asyncio.sleep(delay)

            except httpx.TimeoutException:
                delay = self._calculate_retry_delay(attempt)
                last_error = f"Timeout calling {model}"
                logger.warning(
                    "Ollama timeout on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    delay,
                )
                self._circuit_breaker.record_failure(endpoint)
                if attempt == max_retries - 1:
                    raise RuntimeError(last_error) from None
                await asyncio.sleep(delay)

            except httpx.HTTPStatusError as e:
                delay = self._calculate_retry_delay(attempt)
                last_error = f"HTTP error calling {model}: {e}"
                logger.warning(
                    "Ollama HTTP error on attempt %d/%d: %s, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    e,
                    delay,
                )
                self._circuit_breaker.record_failure(endpoint)
                if attempt == max_retries - 1:
                    raise RuntimeError(last_error) from None
                await asyncio.sleep(delay)

            except Exception as e:
                # Non-retryable unexpected error
                self._circuit_breaker.record_failure(endpoint)
                raise RuntimeError(f"Unexpected error calling {model}: {e}") from e

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
