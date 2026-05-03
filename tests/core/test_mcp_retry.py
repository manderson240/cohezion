"""Tests for MCP retry logic."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from cohezion.core.mcp_retry import retry_async, retry_sync


class TestRetryAsync:

    def test_successful_first_attempt_no_retry(self):
        calls = []

        async def fn():
            calls.append(1)
            return "ok"

        result = asyncio.run(retry_async(fn, max_retries=3))
        assert result == "ok"
        assert len(calls) == 1

    def test_retries_on_connection_error(self):
        attempts = []

        async def fn():
            attempts.append(len(attempts))
            if len(attempts) < 3:
                raise ConnectionError("down")
            return "ok"

        result = asyncio.run(retry_async(fn, max_retries=5, base_delay_s=0.01))
        assert result == "ok"
        assert len(attempts) == 3

    def test_raises_after_max_retries(self):
        async def always_fail():
            raise ConnectionError("always")

        with pytest.raises(ConnectionError):
            asyncio.run(retry_async(always_fail, max_retries=2, base_delay_s=0.01))

    def test_non_retryable_error_raised_immediately(self):
        attempts = []

        async def fn():
            attempts.append(1)
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            asyncio.run(retry_async(fn, max_retries=3, base_delay_s=0.01))

        assert len(attempts) == 1  # No retries


class TestRetrySync:

    def test_successful_first_attempt(self):
        def fn():
            return 42
        assert retry_sync(fn, max_retries=3) == 42

    def test_retries_on_connection_error(self):
        calls = [0]

        def fn():
            calls[0] += 1
            if calls[0] < 3:
                raise ConnectionError("transient")
            return "ok"

        result = retry_sync(fn, max_retries=5, base_delay_s=0.001)
        assert result == "ok"
        assert calls[0] == 3

    def test_raises_after_max_retries(self):
        def always_fail():
            raise ConnectionError("always")

        with pytest.raises(ConnectionError):
            retry_sync(always_fail, max_retries=2, base_delay_s=0.001)

