"""Tests for platform resource manager — ResourceClient and ResourceDaemon."""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.platform.resource_manager import (
    OOMRiskError,
    PlatformMemoryState,
    ResourceClient,
    ResourceDaemon,
    TrainingLock,
)


# ---------------------------------------------------------------------------
# PlatformMemoryState
# ---------------------------------------------------------------------------


class TestPlatformMemoryState:
    def test_available_gb_basic(self) -> None:
        state = PlatformMemoryState(
            total_gb=128.0,
            ollama_used_gb=20.0,
            system_reserved_gb=8.0,
            training_reserved_gb=10.0,
            safety_buffer_gb=10.0,
        )
        assert state.available_gb == pytest.approx(80.0)

    def test_available_gb_defaults(self) -> None:
        state = PlatformMemoryState()
        # 128 - 0 - 8 - 0 - 10 = 110
        assert state.available_gb == pytest.approx(110.0)

    def test_available_gb_with_training_reserved(self) -> None:
        state = PlatformMemoryState(training_reserved_gb=40.0)
        assert state.available_gb == pytest.approx(70.0)

    def test_loaded_models_defaults_empty(self) -> None:
        state = PlatformMemoryState()
        assert state.loaded_models == []


# ---------------------------------------------------------------------------
# TrainingLock
# ---------------------------------------------------------------------------


class TestTrainingLock:
    def test_expiry_set_correctly(self) -> None:
        now = time.time()
        ttl = ResourceDaemon.TRAINING_LOCK_TTL_S
        lock = TrainingLock(
            lock_id="test-lock",
            session_id="session-1",
            model="deepcoder:14b",
            reserved_gb=20.0,
            acquired_at=now,
            expires_at=now + ttl,
        )
        assert lock.expires_at == pytest.approx(now + ttl, abs=1)

    def test_is_expired_false_when_fresh(self) -> None:
        now = time.time()
        lock = TrainingLock(
            lock_id="l",
            session_id="s",
            model="m",
            reserved_gb=1.0,
            acquired_at=now,
            expires_at=now + 3600,
        )
        assert not lock.is_expired()

    def test_is_expired_true_when_past(self) -> None:
        past = time.time() - 1
        lock = TrainingLock(
            lock_id="l",
            session_id="s",
            model="m",
            reserved_gb=1.0,
            acquired_at=past - 100,
            expires_at=past,
        )
        assert lock.is_expired()

    def test_is_expired_false_when_expires_at_zero(self) -> None:
        lock = TrainingLock(
            lock_id="l",
            session_id="s",
            model="m",
            reserved_gb=1.0,
            expires_at=0.0,
        )
        assert not lock.is_expired()


# ---------------------------------------------------------------------------
# ResourceClient — daemon not running (fallback path)
# ---------------------------------------------------------------------------


class TestResourceClientFallback:
    """ResourceClient should degrade gracefully when daemon is offline."""

    def _make_client_no_daemon(self) -> ResourceClient:
        client = ResourceClient()
        client.is_daemon_running = MagicMock(return_value=False)
        return client

    @pytest.mark.asyncio
    async def test_check_memory_falls_back_to_ollama(self) -> None:
        client = self._make_client_no_daemon()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "phi4-mini", "size": 10 * 1024**3},
            ]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            state = await client.check_memory()

        assert state.ollama_used_gb == pytest.approx(10.0, rel=0.01)
        assert "phi4-mini" in state.loaded_models

    @pytest.mark.asyncio
    async def test_check_memory_returns_default_on_ollama_failure(self) -> None:
        client = self._make_client_no_daemon()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(side_effect=Exception("conn refused"))
            state = await client.check_memory()
        # Should return a default PlatformMemoryState without raising
        assert isinstance(state, PlatformMemoryState)

    @pytest.mark.asyncio
    async def test_acquire_lock_raises_oom_risk_when_insufficient(self) -> None:
        client = self._make_client_no_daemon()
        # Simulate only 5 GiB available
        small_state = PlatformMemoryState(
            total_gb=128.0,
            ollama_used_gb=105.0,
            system_reserved_gb=8.0,
            training_reserved_gb=0.0,
            safety_buffer_gb=10.0,
        )
        client._poll_ollama_locally = AsyncMock(return_value=small_state)

        with pytest.raises(OOMRiskError):
            await client.acquire_training_lock(model="bigmodel", required_gb=10.0)

    @pytest.mark.asyncio
    async def test_acquire_lock_returns_lock_when_sufficient(self) -> None:
        client = self._make_client_no_daemon()
        generous_state = PlatformMemoryState(
            total_gb=128.0,
            ollama_used_gb=10.0,
            system_reserved_gb=8.0,
            training_reserved_gb=0.0,
            safety_buffer_gb=10.0,
        )
        client._poll_ollama_locally = AsyncMock(return_value=generous_state)

        lock = await client.acquire_training_lock(model="deepcoder:14b", required_gb=20.0)
        assert lock is not None
        assert lock.model == "deepcoder:14b"
        assert lock.reserved_gb == 20.0
        assert lock.expires_at > lock.acquired_at

    @pytest.mark.asyncio
    async def test_release_lock_no_daemon_is_noop(self) -> None:
        client = self._make_client_no_daemon()
        # Should not raise
        await client.release_training_lock("some-lock-id")

    @pytest.mark.asyncio
    async def test_can_load_model_true_when_enough_memory(self) -> None:
        client = self._make_client_no_daemon()
        state = PlatformMemoryState(ollama_used_gb=0.0)
        client.check_memory = AsyncMock(return_value=state)
        assert await client.can_load_model("phi4-mini", 5.0) is True

    @pytest.mark.asyncio
    async def test_can_load_model_false_when_tight(self) -> None:
        client = self._make_client_no_daemon()
        # Only 5 GiB available; model needs 5 * 1.2 = 6 GiB
        state = PlatformMemoryState(
            total_gb=128.0,
            ollama_used_gb=105.0,
            system_reserved_gb=8.0,
            safety_buffer_gb=10.0,
        )
        client.check_memory = AsyncMock(return_value=state)
        assert await client.can_load_model("bigmodel", 5.0) is False


# ---------------------------------------------------------------------------
# ResourceClient — daemon running (HTTP path)
# ---------------------------------------------------------------------------


class TestResourceClientWithDaemon:
    def _make_client_with_daemon(self) -> ResourceClient:
        client = ResourceClient()
        client.is_daemon_running = MagicMock(return_value=True)
        return client

    def _make_mock_session(self, json_payload: dict, status: int = 200) -> MagicMock:
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=json_payload)
        mock_response.status = status
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        return mock_session

    @pytest.mark.asyncio
    async def test_check_memory_uses_daemon(self) -> None:
        client = self._make_client_with_daemon()
        payload = {
            "total_gb": 128.0,
            "ollama_used_gb": 30.0,
            "system_reserved_gb": 8.0,
            "training_reserved_gb": 5.0,
            "safety_buffer_gb": 10.0,
            "loaded_models": ["phi4-mini"],
        }
        mock_session = self._make_mock_session(payload)
        with patch("aiohttp.ClientSession", return_value=mock_session):
            state = await client.check_memory()

        assert state.ollama_used_gb == pytest.approx(30.0)
        assert "phi4-mini" in state.loaded_models

    @pytest.mark.asyncio
    async def test_acquire_lock_via_daemon(self) -> None:
        client = self._make_client_with_daemon()
        now = time.time()
        payload = {
            "lock_id": "abc-123",
            "session_id": "s1",
            "model": "deepcoder:14b",
            "reserved_gb": 20.0,
            "acquired_at": now,
            "expires_at": now + 7200,
        }
        mock_session = self._make_mock_session(payload, status=200)
        with patch("aiohttp.ClientSession", return_value=mock_session):
            lock = await client.acquire_training_lock("deepcoder:14b", 20.0)

        assert lock is not None
        assert lock.lock_id == "abc-123"

    @pytest.mark.asyncio
    async def test_acquire_lock_returns_none_on_503(self) -> None:
        client = self._make_client_with_daemon()
        mock_session = self._make_mock_session({"error": "insufficient_memory"}, status=503)
        with patch("aiohttp.ClientSession", return_value=mock_session):
            lock = await client.acquire_training_lock("huge-model", 100.0)

        assert lock is None


# ---------------------------------------------------------------------------
# ResourceDaemon internal logic
# ---------------------------------------------------------------------------


class TestResourceDaemon:
    @pytest.mark.asyncio
    async def test_grant_and_release_lock(self) -> None:
        daemon = ResourceDaemon()
        daemon._memory_state = PlatformMemoryState(
            total_gb=128.0,
            ollama_used_gb=10.0,
        )

        lock = await daemon.request_training_lock("session-1", "deepcoder:14b", 20.0)
        assert lock is not None
        assert lock.model == "deepcoder:14b"
        assert daemon._memory_state.training_reserved_gb == pytest.approx(20.0)

        await daemon.release_training_lock(lock.lock_id)
        assert daemon._memory_state.training_reserved_gb == pytest.approx(0.0)
        assert lock.lock_id not in daemon._locks

    @pytest.mark.asyncio
    async def test_lock_denied_when_insufficient_memory(self) -> None:
        daemon = ResourceDaemon()
        daemon._memory_state = PlatformMemoryState(
            total_gb=128.0,
            ollama_used_gb=115.0,  # Only 5 GiB available
        )

        lock = await daemon.request_training_lock("session-1", "bigmodel", 10.0)
        assert lock is None

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_locks(self) -> None:
        daemon = ResourceDaemon()
        daemon._memory_state = PlatformMemoryState()
        past = time.time() - 1
        expired_lock = TrainingLock(
            lock_id="expired",
            session_id="s",
            model="m",
            reserved_gb=5.0,
            acquired_at=past - 100,
            expires_at=past,
        )
        daemon._locks["expired"] = expired_lock
        daemon._memory_state.training_reserved_gb = 5.0

        await daemon.cleanup_dead_sessions()

        assert "expired" not in daemon._locks
        assert daemon._memory_state.training_reserved_gb == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_poll_ollama_state_returns_default_on_failure(self) -> None:
        daemon = ResourceDaemon()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Ollama not running")
            )
            state = await daemon.poll_ollama_state()
        assert isinstance(state, PlatformMemoryState)
        assert state.ollama_used_gb == 0.0
