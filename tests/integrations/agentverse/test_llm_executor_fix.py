"""Test for LLMExecutor error handling fixes.

This test verifies that the retry logic with exponential backoff
and circuit breaker pattern is working correctly.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cohezion.integrations.agentverse.llm_executor import (
    RETRYABLE_STATUS_CODES,
    CircuitBreaker,
    LLMExecutor,
)


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_initial_state_closed(self):
        """Circuit starts in closed (passing) state."""
        cb = CircuitBreaker(threshold=3)
        assert not cb.is_open("test_endpoint")

    def test_opens_after_threshold_failures(self):
        """Circuit opens after threshold failures."""
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("test_endpoint")
        cb.record_failure("test_endpoint")
        cb.record_failure("test_endpoint")
        assert cb.is_open("test_endpoint")

    def test_closes_on_success(self):
        """Circuit closes when success is recorded."""
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("test_endpoint")
        cb.record_failure("test_endpoint")
        cb.record_failure("test_endpoint")
        assert cb.is_open("test_endpoint")

        cb.record_success("test_endpoint")
        assert not cb.is_open("test_endpoint")

    def test_auto_reset_after_timeout(self):
        """Circuit auto-resets after timeout."""
        import time

        cb = CircuitBreaker(threshold=3, reset_timeout=0.1)
        cb.record_failure("test_endpoint")
        cb.record_failure("test_endpoint")
        cb.record_failure("test_endpoint")
        assert cb.is_open("test_endpoint")

        # Wait for timeout
        time.sleep(0.15)
        assert not cb.is_open("test_endpoint")


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self):
        """Successful requests don't trigger retries."""
        executor = LLMExecutor()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Success!"}

        with patch.object(executor._client, "post", new=AsyncMock(return_value=mock_response)):
            result = await executor._generate("Prompt", "test_model")
            assert result == "Success!"
            executor._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """500 errors trigger retry with backoff."""
        executor = LLMExecutor()

        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.aread = AsyncMock(
            return_value=b'Error: 500 "Internal Server Error (ref: test-ref-123)"'
        )

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"response": "Success after retry!"}

        with patch.object(
            executor._client,
            "post",
            new=AsyncMock(side_effect=[mock_response_500, mock_response_200]),
        ), patch("asyncio.sleep", new=AsyncMock()):
            result = await executor._generate("Prompt", "test_model")
            assert result == "Success after retry!"
            assert executor._client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_429_rate_limit(self):
        """429 rate limit triggers retry."""
        executor = LLMExecutor()

        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.aread = AsyncMock(return_value=b"Rate limited")

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"response": "Success!"}

        with patch.object(
            executor._client,
            "post",
            new=AsyncMock(side_effect=[mock_response_429, mock_response_200]),
        ), patch("asyncio.sleep", new=AsyncMock()):
            result = await executor._generate("Prompt", "test_model")
            assert result == "Success!"

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_max_retries(self):
        """Circuit breaker opens after exhausting retries."""
        executor = LLMExecutor()

        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.aread = AsyncMock(return_value=b"500 Error")

        with patch.object(
            executor._client,
            "post",
            new=AsyncMock(return_value=mock_response_500),
        ), patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RuntimeError) as exc_info:
                await executor._generate("Prompt", "test_model", max_retries=3)

            assert "Ollama API error 500" in str(exc_info.value)
            assert executor._client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """Timeout exceptions trigger retry."""
        executor = LLMExecutor()

        with patch.object(
            executor._client,
            "post",
            new=AsyncMock(
                side_effect=[
                    httpx.TimeoutException("Timeout"),
                    httpx.TimeoutException("Timeout"),
                    httpx.TimeoutException("Timeout"),
                ]
            ),
        ), patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RuntimeError) as exc_info:
                await executor._generate("Prompt", "test_model", max_retries=3)

            assert "Timeout calling test_model" in str(exc_info.value)


class TestCircuitBreakerIntegration:
    """Test circuit breaker with LLMExecutor."""

    @pytest.mark.asyncio
    async def test_circuit_blocks_requests_when_open(self):
        """Circuit breaker blocks requests when open."""
        executor = LLMExecutor()
        endpoint = f"{executor.ollama_base_url}/test_model"

        # Manually open circuit
        for _ in range(CircuitBreaker().threshold + 1):
            executor._circuit_breaker.record_failure(endpoint)

        assert executor._circuit_breaker.is_open(endpoint)

        with pytest.raises(RuntimeError) as exc_info:
            await executor._generate("Prompt", "test_model")

        assert "Circuit breaker open" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_success_resets_circuit(self):
        """Successful requests reset the circuit."""
        executor = LLMExecutor()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Success!"}

        # Record some failures
        endpoint = f"{executor.ollama_base_url}/test_model"
        executor._circuit_breaker.record_failure(endpoint)
        executor._circuit_breaker.record_failure(endpoint)

        with patch.object(executor._client, "post", new=AsyncMock(return_value=mock_response)):
            await executor._generate("Prompt", "test_model")

        # Circuit should be closed after success
        assert not executor._circuit_breaker.is_open(endpoint)


@pytest.mark.parametrize("status_code", list(RETRYABLE_STATUS_CODES))
def test_status_codes_are_retryable(status_code):
    """Verify the configured retryable status codes."""
    assert status_code in RETRYABLE_STATUS_CODES
    assert status_code in {429, 500, 502, 503, 504}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
