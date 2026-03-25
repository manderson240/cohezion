"""Platform resource arbiter for cross-session memory coordination."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from aiohttp import web


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ResourceUnavailableError(RuntimeError):
    """Raised when a requested resource cannot be acquired."""


class OOMRiskError(ResourceUnavailableError):
    """Raised when allocating memory would risk OOM on the host."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PlatformMemoryState:
    """Snapshot of host memory allocation across all sessions.

    Values are in GiB. Reflects the Ryzen AI MAX+ 395 with 128 GiB unified RAM.
    """

    total_gb: float = 128.0  # Ryzen AI MAX+ 395
    ollama_used_gb: float = 0.0
    system_reserved_gb: float = 8.0  # OS overhead
    training_reserved_gb: float = 0.0
    safety_buffer_gb: float = 10.0
    loaded_models: list[str] = field(default_factory=list)

    @property
    def available_gb(self) -> float:
        """GiB available for new allocations."""
        return (
            self.total_gb
            - self.ollama_used_gb
            - self.system_reserved_gb
            - self.training_reserved_gb
            - self.safety_buffer_gb
        )


@dataclass
class TrainingLock:
    """Exclusive reservation for a training workload."""

    lock_id: str
    session_id: str
    model: str
    reserved_gb: float
    acquired_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # Set by caller to acquired_at + TTL

    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at


# ---------------------------------------------------------------------------
# ResourceClient — used by callers to talk to the daemon (or fall back locally)
# ---------------------------------------------------------------------------


class ResourceClient:
    """Thin HTTP client that delegates resource decisions to ResourceDaemon.

    Falls back to a local Ollama poll when the daemon is not running so that
    callers remain functional in development without the daemon process.
    """

    DAEMON_URL = "http://localhost:8765"
    _OLLAMA_PS_URL = "http://localhost:11434/api/ps"

    def is_daemon_running(self) -> bool:
        """Return True if the daemon health endpoint responds."""
        import socket

        try:
            conn = socket.create_connection(("localhost", 8765), timeout=1)
            conn.close()
            return True
        except OSError:
            return False

    async def check_memory(self) -> PlatformMemoryState:
        """Return current memory state from daemon or local Ollama poll."""
        if self.is_daemon_running():
            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(
                        f"{self.DAEMON_URL}/memory", timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp,
                ):
                    data = await resp.json()
                    return PlatformMemoryState(
                        total_gb=data.get("total_gb", 128.0),
                        ollama_used_gb=data.get("ollama_used_gb", 0.0),
                        system_reserved_gb=data.get("system_reserved_gb", 8.0),
                        training_reserved_gb=data.get("training_reserved_gb", 0.0),
                        safety_buffer_gb=data.get("safety_buffer_gb", 10.0),
                        loaded_models=data.get("loaded_models", []),
                    )
            except aiohttp.ClientError as exc:
                logger.warning("Daemon unreachable, falling back to local poll: %s", exc)

        return await self._poll_ollama_locally()

    async def _poll_ollama_locally(self) -> PlatformMemoryState:
        """Poll Ollama /api/ps directly and build a best-effort memory state."""
        state = PlatformMemoryState()
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(self._OLLAMA_PS_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp,
            ):
                data = await resp.json()
                models = data.get("models", [])
                state.loaded_models = [m.get("name", "") for m in models]
                state.ollama_used_gb = sum(m.get("size", 0) / (1024**3) for m in models)
        except (aiohttp.ClientError, Exception) as exc:
            logger.debug("Could not reach Ollama: %s", exc)
        return state

    async def acquire_training_lock(
        self,
        model: str,
        required_gb: float,
        timeout_s: float = 30.0,
    ) -> TrainingLock | None:
        """Request an exclusive training lock, returning None if unavailable."""
        if self.is_daemon_running():
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": model,
                        "required_gb": required_gb,
                        "session_id": _current_session_id(),
                    }
                    async with session.post(
                        f"{self.DAEMON_URL}/locks",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=timeout_s),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            lock = TrainingLock(
                                lock_id=data["lock_id"],
                                session_id=data["session_id"],
                                model=data["model"],
                                reserved_gb=data["reserved_gb"],
                                acquired_at=data["acquired_at"],
                                expires_at=data["expires_at"],
                            )
                            return lock
                        return None
            except aiohttp.ClientError as exc:
                logger.warning("Daemon lock request failed, using local check: %s", exc)

        # Fallback: local memory check
        state = await self._poll_ollama_locally()
        if state.available_gb < required_gb * 1.2:
            raise OOMRiskError(
                f"Insufficient memory: need {required_gb * 1.2:.1f} GiB, "
                f"have {state.available_gb:.1f} GiB"
            )
        now = time.time()
        return TrainingLock(
            lock_id=str(uuid.uuid4()),
            session_id=_current_session_id(),
            model=model,
            reserved_gb=required_gb,
            acquired_at=now,
            expires_at=now + ResourceDaemon.TRAINING_LOCK_TTL_S,
        )

    async def release_training_lock(self, lock_id: str) -> None:
        """Release a previously acquired training lock."""
        if not self.is_daemon_running():
            logger.debug("Daemon not running; local lock %s released (no-op)", lock_id)
            return
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.delete(
                    f"{self.DAEMON_URL}/locks/{lock_id}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp,
            ):
                if resp.status not in (200, 204):
                    logger.warning("Lock release returned HTTP %s", resp.status)
        except aiohttp.ClientError as exc:
            logger.warning("Could not release lock %s: %s", lock_id, exc)

    async def can_load_model(self, model_name: str, size_gb: float) -> bool:
        """Return True if there is enough memory to load the model safely."""
        state = await self.check_memory()
        return state.available_gb > size_gb * 1.2

    async def register_session(self, session_id: str) -> None:
        """Notify the daemon that a new session is starting."""
        if not self.is_daemon_running():
            return
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.DAEMON_URL}/sessions",
                    json={"session_id": session_id},
                    timeout=aiohttp.ClientTimeout(total=5),
                )
        except aiohttp.ClientError as exc:
            logger.debug("Could not register session: %s", exc)


# ---------------------------------------------------------------------------
# ResourceDaemon — long-running process that arbitrates locks across sessions
# ---------------------------------------------------------------------------


class ResourceDaemon:
    """HTTP server that provides cross-session resource arbitration.

    Run via: python -m cohezion.platform.resource_manager
    """

    PORT = 8765
    POLL_INTERVAL_S = 30
    TRAINING_LOCK_TTL_S = 7200  # 2 hours

    _OLLAMA_PS_URL = "http://localhost:11434/api/ps"

    def __init__(self) -> None:
        self._memory_state = PlatformMemoryState()
        self._locks: dict[str, TrainingLock] = {}
        self._sessions: set[str] = set()
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Ollama polling
    # ------------------------------------------------------------------

    async def poll_ollama_state(self) -> PlatformMemoryState:
        """Fetch /api/ps from Ollama and return a PlatformMemoryState."""
        state = PlatformMemoryState()
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(self._OLLAMA_PS_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp,
            ):
                data = await resp.json()
                models = data.get("models", [])
                state.loaded_models = [m.get("name", "") for m in models]
                state.ollama_used_gb = sum(m.get("size", 0) / (1024**3) for m in models)
                # training_reserved_gb is computed from active locks
                async with self._lock:
                    state.training_reserved_gb = sum(
                        lk.reserved_gb for lk in self._locks.values() if not lk.is_expired()
                    )
        except (aiohttp.ClientError, Exception) as exc:
            logger.debug("Ollama poll failed: %s", exc)
        return state

    async def get_available_memory_gb(self) -> float:
        """Return currently available GiB."""
        state = await self.poll_ollama_state()
        return state.available_gb

    # ------------------------------------------------------------------
    # Lock management
    # ------------------------------------------------------------------

    async def request_training_lock(
        self,
        session_id: str,
        model: str,
        required_gb: float,
    ) -> TrainingLock | None:
        """Grant a training lock if sufficient memory is available."""
        async with self._lock:
            await self.cleanup_dead_sessions()
            available = self._memory_state.available_gb
            if available < required_gb * 1.2:
                logger.warning(
                    "Lock denied for %s/%s: need %.1f GiB, available %.1f GiB",
                    session_id,
                    model,
                    required_gb * 1.2,
                    available,
                )
                return None

            now = time.time()
            lock = TrainingLock(
                lock_id=str(uuid.uuid4()),
                session_id=session_id,
                model=model,
                reserved_gb=required_gb,
                acquired_at=now,
                expires_at=now + self.TRAINING_LOCK_TTL_S,
            )
            self._locks[lock.lock_id] = lock
            self._memory_state.training_reserved_gb += required_gb
            logger.info("Granted lock %s for %s (%.1f GiB)", lock.lock_id, model, required_gb)
            return lock

    async def release_training_lock(self, lock_id: str) -> None:
        """Remove a lock and free the reserved memory."""
        async with self._lock:
            lock = self._locks.pop(lock_id, None)
            if lock:
                self._memory_state.training_reserved_gb = max(
                    0.0, self._memory_state.training_reserved_gb - lock.reserved_gb
                )
                logger.info("Released lock %s", lock_id)

    async def cleanup_dead_sessions(self) -> None:
        """Remove expired locks (called while holding self._lock)."""
        expired = [lid for lid, lk in self._locks.items() if lk.is_expired()]
        for lid in expired:
            lock = self._locks.pop(lid)
            self._memory_state.training_reserved_gb = max(
                0.0, self._memory_state.training_reserved_gb - lock.reserved_gb
            )
            logger.info("Expired lock %s for session %s", lid, lock.session_id)

    # ------------------------------------------------------------------
    # aiohttp request handlers
    # ------------------------------------------------------------------

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def _handle_get_memory(self, request: web.Request) -> web.Response:
        state = await self.poll_ollama_state()
        async with self._lock:
            self._memory_state = state
        return web.json_response(
            {
                "total_gb": state.total_gb,
                "ollama_used_gb": state.ollama_used_gb,
                "system_reserved_gb": state.system_reserved_gb,
                "training_reserved_gb": state.training_reserved_gb,
                "safety_buffer_gb": state.safety_buffer_gb,
                "loaded_models": state.loaded_models,
                "available_gb": state.available_gb,
            }
        )

    async def _handle_post_lock(self, request: web.Request) -> web.Response:
        body: dict[str, Any] = await request.json()
        session_id = body.get("session_id", "unknown")
        model = body.get("model", "")
        required_gb = float(body.get("required_gb", 0))

        lock = await self.request_training_lock(session_id, model, required_gb)
        if lock is None:
            return web.json_response({"error": "insufficient_memory"}, status=503)
        return web.json_response(
            {
                "lock_id": lock.lock_id,
                "session_id": lock.session_id,
                "model": lock.model,
                "reserved_gb": lock.reserved_gb,
                "acquired_at": lock.acquired_at,
                "expires_at": lock.expires_at,
            }
        )

    async def _handle_delete_lock(self, request: web.Request) -> web.Response:
        lock_id = request.match_info["lock_id"]
        await self.release_training_lock(lock_id)
        return web.Response(status=204)

    async def _handle_post_session(self, request: web.Request) -> web.Response:
        body: dict[str, Any] = await request.json()
        session_id = body.get("session_id", "")
        if session_id:
            self._sessions.add(session_id)
            logger.info("Registered session %s", session_id)
        return web.json_response({"ok": True})

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self.POLL_INTERVAL_S)
            try:
                state = await self.poll_ollama_state()
                async with self._lock:
                    self._memory_state = state
                    await self.cleanup_dead_sessions()
            except Exception as exc:
                logger.warning("Poll loop error: %s", exc)

    async def start(self) -> None:
        """Run the aiohttp server and background poll loop."""
        app = web.Application()
        app.router.add_get("/health", self._handle_health)
        app.router.add_get("/memory", self._handle_get_memory)
        app.router.add_post("/locks", self._handle_post_lock)
        app.router.add_delete("/locks/{lock_id}", self._handle_delete_lock)
        app.router.add_post("/sessions", self._handle_post_session)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", self.PORT)
        await site.start()
        logger.info("ResourceDaemon listening on port %d", self.PORT)

        # Initial poll
        state = await self.poll_ollama_state()
        async with self._lock:
            self._memory_state = state

        await self._poll_loop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_session_id() -> str:
    """Return a stable session identifier for the current process."""
    import os

    return os.environ.get("COHEZION_SESSION_ID", f"pid-{os.getpid()}")


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    daemon = ResourceDaemon()
    asyncio.run(daemon.start())
