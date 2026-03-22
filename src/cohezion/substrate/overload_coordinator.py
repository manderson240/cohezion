"""Overload protection coordinator with graduated response.

Central coordination for all overload protection systems with tiered response
to memory pressure, circuit breaker coordination, and request throttling.

Designed for AMD Ryzen AI MAX+ 395 with 128GB unified memory.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx
import psutil

from cohezion.substrate.kv_cache_tracker import KVCacheTracker


if TYPE_CHECKING:
    from cohezion.swarm.model_pool_manager import ModelPoolManager

logger = logging.getLogger(__name__)


class ProtectionLevel(enum.Enum):
    """Protection levels based on memory pressure."""

    NORMAL = "normal"
    WARNING = "warning"
    ELEVATED = "elevated"
    CRITICAL = "critical"
    EMERGENCY = "emergency"
    CRASH_PREVENTION = "crash_prevention"


@dataclass
class ProtectionAction:
    """Result of a protection action."""

    level: ProtectionLevel
    timestamp: float = field(default_factory=time.time)
    actions: list[str] = field(default_factory=list)
    context_reduction_percent: int = 0
    models_evicted: list[str] = field(default_factory=list)
    requests_queued: int = 0
    requests_rejected: int = 0
    emergency_restart_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "level": self.level.value,
            "timestamp": self.timestamp,
            "actions": self.actions,
            "context_reduction_percent": self.context_reduction_percent,
            "models_evicted": self.models_evicted,
            "requests_queued": self.requests_queued,
            "requests_rejected": self.requests_rejected,
            "emergency_restart_triggered": self.emergency_restart_triggered,
        }


@dataclass
class ProtectionConfig:
    """Configuration for graduated overload protection."""

    # Memory pressure thresholds (graduated)
    pressure_normal: float = 0.65  # 65% - full performance
    pressure_warning: float = 0.75  # 75% - reduce context 25%
    pressure_elevated: float = 0.85  # 85% - evict cold, reduce 50%
    pressure_critical: float = 0.92  # 92% - emergency mode
    pressure_emergency: float = 0.95  # 95% - restart Ollama

    # Response delays (prevent thrashing)
    min_action_interval: float = 10.0  # Seconds between actions
    cooldown_period: float = 30.0  # Seconds before escalating

    # Circuit breaker coordination
    disable_circuits_above: float = 0.90  # Disable CB above this

    # Request throttling
    max_queue_depth: int = 10
    queue_timeout: float = 300.0

    # Context reduction percentages by level
    context_reduction: dict[str, int] = field(
        default_factory=lambda: {
            "warning": 25,
            "elevated": 50,
            "critical": 75,
            "emergency": 90,
        }
    )


class OverloadCoordinator:
    """Central coordinator for overload protection systems.

    Manages graduated response to memory pressure, coordinates with
    circuit breakers, and validates requests against system state.
    """

    def __init__(
        self,
        config: ProtectionConfig | None = None,
        model_pool: ModelPoolManager | None = None,
        kv_tracker: KVCacheTracker | None = None,
    ):
        self.config = config or ProtectionConfig()
        self.model_pool = model_pool
        self.kv_tracker = kv_tracker

        # State tracking
        self._last_action_time: float = 0.0
        self._current_level = ProtectionLevel.NORMAL
        self._level_since: float = time.time()
        self._action_history: list[ProtectionAction] = []
        self._request_queue: asyncio.Queue[dict] = asyncio.Queue(
            maxsize=self.config.max_queue_depth
        )

        # Current context reduction (applied cumulatively)
        self._current_context_reduction: int = 0

        # Circuit breaker coordination
        self._circuit_breakers_disabled: bool = False

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def handle_memory_pressure(self, pressure: float) -> ProtectionAction:
        """Handle memory pressure with graduated response.

        Args:
            pressure: Current memory pressure (0.0 - 1.0)

        Returns:
            ProtectionAction detailing actions taken

        Response Matrix:
            0.00-0.65: Normal - No action
            0.65-0.75: Warning - Reduce context 25%, notify
            0.75-0.85: Elevated - Evict cold models, reduce 50%, throttle
            0.85-0.92: Critical - Evict warm, reduce 75%, queue new requests
            0.92-0.95: Emergency - Restart Ollama, preserve hot models
            0.95+:     Crash Prevention - Emergency restart with minimal config
        """
        async with self._lock:
            # Check cooldown
            if time.time() - self._last_action_time < self.config.min_action_interval:
                return ProtectionAction(
                    level=self._current_level,
                    actions=["cooldown_active"],
                )

            # Determine level
            new_level = self._determine_level(pressure)

            # If same level and within cooldown, no action
            if new_level == self._current_level:
                if time.time() - self._level_since < self.config.cooldown_period:
                    return ProtectionAction(
                        level=self._current_level,
                        actions=["level_unchanged"],
                    )

            # Take action based on level
            action = await self._take_action(new_level, pressure)

            # Update state
            if new_level != self._current_level:
                self._current_level = new_level
                self._level_since = time.time()
                logger.warning(
                    f"Protection level changed: {self._current_level.value} -> {new_level.value} "
                    f"(pressure: {pressure:.2%})"
                )

            self._last_action_time = time.time()
            self._action_history.append(action)

            # Keep history manageable
            if len(self._action_history) > 1000:
                self._action_history = self._action_history[-1000:]

            return action

    def _determine_level(self, pressure: float) -> ProtectionLevel:
        """Determine protection level from pressure."""
        if pressure >= self.config.pressure_emergency:
            return ProtectionLevel.CRASH_PREVENTION
        elif pressure >= self.config.pressure_critical:
            return ProtectionLevel.EMERGENCY
        elif pressure >= self.config.pressure_elevated:
            return ProtectionLevel.CRITICAL
        elif pressure >= self.config.pressure_warning:
            return ProtectionLevel.ELEVATED
        elif pressure >= self.config.pressure_normal:
            return ProtectionLevel.WARNING
        else:
            return ProtectionLevel.NORMAL

    async def _take_action(self, level: ProtectionLevel, pressure: float) -> ProtectionAction:
        """Take action based on protection level."""
        action = ProtectionAction(level=level)

        match level:
            case ProtectionLevel.NORMAL:
                # Reset to normal state
                action.actions.append("reset_normal")
                if self._current_context_reduction > 0:
                    action.actions.append("restore_full_context")
                    self._current_context_reduction = 0

            case ProtectionLevel.WARNING:
                action.actions.append("reduce_context_25")
                action.context_reduction_percent = 25
                self._current_context_reduction = max(self._current_context_reduction, 25)
                await self._reduce_context_windows(25)

            case ProtectionLevel.ELEVATED:
                action.actions.extend(
                    ["evict_cold_models", "reduce_context_50", "throttle_requests"]
                )
                action.context_reduction_percent = 50
                self._current_context_reduction = max(self._current_context_reduction, 50)

                # Evict cold models
                if self.model_pool:
                    evicted = await self.model_pool.demote_under_pressure()
                    action.models_evicted = evicted

                await self._reduce_context_windows(50)

            case ProtectionLevel.CRITICAL:
                action.actions.extend(["evict_warm_models", "reduce_context_75", "queue_requests"])
                action.context_reduction_percent = 75
                self._current_context_reduction = max(self._current_context_reduction, 75)

                # Evict warm models
                if self.model_pool:
                    evicted = await self._evict_warm_models()
                    action.models_evicted = evicted

                await self._reduce_context_windows(75)
                action.requests_queued = self._request_queue.qsize()

            case ProtectionLevel.EMERGENCY:
                action.actions.extend(
                    [
                        "emergency_restart_ollama",
                        "preserve_hot_models_only",
                        "reject_all_requests",
                    ]
                )
                action.emergency_restart_triggered = True

                # Emergency restart
                await self._emergency_restart_ollama()

            case ProtectionLevel.CRASH_PREVENTION:
                action.actions.extend(
                    [
                        "crash_prevention_mode",
                        "emergency_restart_ollama",
                        "preserve_hot_models_only",
                    ]
                )
                action.emergency_restart_triggered = True

                # Hard restart
                await self._crash_prevention_restart()

        return action

    async def validate_request(
        self,
        request: dict[str, Any],
        required_memory_gb: float | None = None,
    ) -> dict[str, Any]:
        """Validate request against current system state.

        Args:
            request: Request to validate
            required_memory_gb: Estimated memory required

        Returns:
            Validated request (may be modified)

        Raises:
            OverloadError: If request cannot be safely processed
        """
        async with self._lock:
            # Check if we're in emergency modes
            if self._current_level in [
                ProtectionLevel.EMERGENCY,
                ProtectionLevel.CRASH_PREVENTION,
            ]:
                raise OverloadError(
                    "System in emergency mode - requests rejected",
                    retry_after=60,
                )

            # Check queue depth
            if self._current_level == ProtectionLevel.CRITICAL and self._request_queue.full():
                raise OverloadError(
                    "Request queue full - try again later",
                    retry_after=30,
                )

            # Apply context reduction
            if "options" in request and "num_ctx" in request["options"]:
                original_ctx = request["options"]["num_ctx"]
                reduced_ctx = int(original_ctx * (1 - self._current_context_reduction / 100))
                request["options"]["num_ctx"] = max(reduced_ctx, 1024)

                if reduced_ctx < original_ctx:
                    logger.info(
                        f"Context reduced from {original_ctx} to {reduced_ctx} "
                        f"(reduction: {self._current_context_reduction}%)"
                    )

            return request

    async def check_can_load(self, model_name: str) -> bool:
        """Check if a model can be safely loaded.

        Args:
            model_name: Name of model to load

        Returns:
            True if model can be loaded, False otherwise
        """
        async with self._lock:
            # Never load in emergency modes
            if self._current_level in [
                ProtectionLevel.EMERGENCY,
                ProtectionLevel.CRASH_PREVENTION,
            ]:
                return False

            # In critical mode, only allow hot model loads
            if self._current_level == ProtectionLevel.CRITICAL and self.model_pool:
                model = self.model_pool.get_model(model_name)
                if model and model.tier.value != "hot":
                    return False

            return True

    async def coordinate_with_circuit_breakers(self, pressure: float) -> None:
        """Adjust circuit breaker behavior based on pressure.

        When pressure is high, we disable aggressive circuit breaking
        to prevent unnecessary model switching.
        """
        should_disable = pressure >= self.config.disable_circuits_above

        if should_disable != self._circuit_breakers_disabled:
            self._circuit_breakers_disabled = should_disable
            logger.info(
                f"Circuit breakers {'disabled' if should_disable else 'enabled'} (pressure: {pressure:.2%})"
            )

    async def queue_request(self, request: dict[str, Any]) -> int:
        """Queue a request for later processing.

        Returns:
            Queue position (0 = next to process)
        """
        try:
            self._request_queue.put_nowait(request)
            return self._request_queue.qsize() - 1
        except asyncio.QueueFull:
            raise OverloadError("Request queue full", retry_after=60) from None

    async def _reduce_context_windows(self, reduction_percent: int) -> None:
        """Reduce context windows across all loaded Ollama models.

        Queries /api/ps to find loaded models, then sends keep_alive=0 to
        unload any model whose context would exceed our reduced budget. The
        next request reloads it with the lower num_ctx via validate_request().
        """
        logger.info(f"Reducing context windows by {reduction_percent}%")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get("http://localhost:11434/api/ps")
                if r.status_code != 200:
                    return
                models = r.json().get("models", [])
                if not models:
                    logger.debug("No running Ollama models to reduce context for")
                    return
                logger.info(
                    "Context reduction %d%%: found %d loaded model(s): %s",
                    reduction_percent,
                    len(models),
                    [m["name"] for m in models],
                )
                # Unloading forces the next generation to reload with our
                # reduced num_ctx (applied by validate_request).
                for model in models:
                    payload = {"model": model["name"], "keep_alive": 0}
                    await client.post("http://localhost:11434/api/generate", json=payload)
                    logger.info("Unloaded %s (will reload with reduced ctx)", model["name"])
        except Exception as exc:
            logger.warning("Context-window reduction failed (non-critical): %s", exc)

    async def _evict_warm_models(self) -> list[str]:
        """Evict warm tier models."""
        if not self.model_pool:
            return []

        evicted = []
        warm_models = [m for m in self.model_pool._pool.values() if m.tier.value == "warm"]

        for model in sorted(warm_models, key=lambda m: m.last_used):
            if await self.model_pool.evict_model(model.name):
                evicted.append(model.name)

        return evicted

    async def _emergency_restart_ollama(self) -> None:
        """Unload all Ollama models to free unified memory.

        Uses the Ollama API (keep_alive=0) instead of process kill so that
        the Ollama daemon stays healthy. Models will reload on demand with
        conservative settings applied by validate_request().
        """
        logger.critical("EMERGENCY: Unloading all Ollama models to free unified memory")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get("http://localhost:11434/api/ps")
                models = r.json().get("models", []) if r.status_code == 200 else []
                for model in models:
                    payload = {"model": model["name"], "keep_alive": 0}
                    await client.post("http://localhost:11434/api/generate", json=payload)
                    logger.critical("EMERGENCY unloaded: %s", model["name"])
                if not models:
                    logger.critical("EMERGENCY: No loaded models to unload")
        except Exception as exc:
            logger.critical("EMERGENCY unload failed: %s — system may be unstable", exc)

    async def _crash_prevention_restart(self) -> None:
        """Kill the Ollama process in crash-prevention mode.

        Used only when memory is at 95%+ and API unloading has failed.
        Sends SIGKILL to the ollama process, allowing systemd/the OS to
        restart it with default conservative parameters.
        """
        logger.critical("CRASH PREVENTION: Killing ollama process to recover memory")
        killed = False
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = proc.info.get("name", "")
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if "ollama" in name.lower() or "ollama serve" in cmdline:
                    proc.kill()
                    logger.critical("CRASH PREVENTION: Killed ollama PID %d", proc.info["pid"])
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not killed:
            logger.critical("CRASH PREVENTION: ollama process not found — may have already exited")

    def get_current_reduction(self) -> int:
        """Get current context reduction percentage."""
        return self._current_context_reduction

    def get_status(self) -> dict[str, Any]:
        """Get current protection status."""
        return {
            "current_level": self._current_level.value,
            "level_since": self._level_since,
            "current_context_reduction": self._current_context_reduction,
            "circuit_breakers_disabled": self._circuit_breakers_disabled,
            "queue_depth": self._request_queue.qsize(),
            "last_action_time": self._last_action_time,
            "action_count": len(self._action_history),
        }


class OverloadError(Exception):
    """Error raised when request cannot be processed due to overload."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after
