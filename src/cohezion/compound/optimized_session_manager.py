"""Optimized long-running inference session management with lazy-loading and parallel execution.

This module implements patterns from the pi-mono changelog optimizations:
- Lazy-loading of heavy SDKs (v0.59.0, v0.58.0)
- Parallel tool execution (v0.58.0)
- Session runtime API with warm-start/clean-shutdown (v0.65.0)
- Async I/O with proper timeouts (v0.64.0, v0.63.0)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar


# Lazy imports - only import when needed
if TYPE_CHECKING:
    from cohezion.core.mcp_client import MCPClient

T = TypeVar("T")

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Checkpoint snapshot of session state."""

    session_id: str
    skill_name: str
    current_step: int
    total_steps: int
    context: str
    intermediate_results: list[dict[str, Any]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    last_checkpoint_time: float = field(default_factory=time.time)
    model_usage: dict[str, int] = field(default_factory=dict)
    cache_state: dict[str, str] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    cost_breakdown: dict[str, float] = field(default_factory=dict)
    # Parallel execution tracking (v0.58.0 pattern)
    pending_tasks: set[asyncio.Task] = field(default_factory=set)


@dataclass
class SessionConfig:
    """Configuration for inference session with optimized defaults."""

    checkpoint_interval_steps: int = 5
    checkpoint_timeout_sec: float = 300.0
    max_session_duration_sec: float = 7200.0
    enable_streaming: bool = True
    vault_persistence: bool = True
    # New: Parallel execution config (v0.58.0)
    parallel_tool_calls: bool = True
    max_concurrent_tools: int = 10
    # New: Lazy-loading config (v0.59.0)
    lazy_load_sdks: bool = True
    # New: Async timeout config (v0.64.0)
    default_timeout_sec: float = 60.0
    retry_max_attempts: int = 3


def lazy_import_mcp_client():
    """Lazy import MCP client to avoid startup overhead (v0.59.0 pattern)."""
    from cohezion.core.mcp_client import get_mcp_client

    return get_mcp_client()


class OptimizedSessionRuntime:
    """Session runtime with warm-start/clean-shutdown lifecycle (v0.65.0).

    This class implements the session runtime API pattern from the changelog:
    - Warm-start: Cache + metrics loaded automatically
    - Clean-shutdown: Cache + metrics persisted automatically
    """

    _instance: OptimizedSessionRuntime | None = None
    _initialized: bool = False

    def __init__(self):
        self.mcp_client: MCPClient | None = None
        self.active_sessions: dict[str, InferenceSession] = {}
        self._warm_cache_loaded: bool = False
        self._metrics_collector: Any = None

    @classmethod
    async def get_instance(cls) -> OptimizedSessionRuntime:
        """Get singleton instance with warm-start (v0.65.0 pattern)."""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance._warm_start()
        return cls._instance

    async def _warm_start(self) -> None:
        """Warm-start: cache + metrics loaded automatically (v0.65.0)."""
        if self._warm_cache_loaded:
            return

        # Lazy load MCP client
        self.mcp_client = lazy_import_mcp_client()

        # Warm cache loading
        from cohezion.compound.cache_persistence import WarmCacheLoader

        loader = WarmCacheLoader()
        entries_loaded = await asyncio.to_thread(loader.warm_client, self.mcp_client, max_entries=256)
        logger.info(f"Cache warmed: {entries_loaded} entries")

        # Metrics restoration
        from cohezion.compound.metrics import get_collector
        from cohezion.compound.metrics_persistence import MetricsPersistence

        col = get_collector()
        mp = MetricsPersistence()
        snapshot = await asyncio.to_thread(mp.load_latest_snapshot)
        if snapshot:
            await asyncio.to_thread(col.load_from_snapshot, snapshot)

        self._warm_cache_loaded = True
        self._initialized = True

    async def clean_shutdown(self) -> None:
        """Clean-shutdown: cache + metrics persisted automatically (v0.65.0)."""
        if not self._initialized:
            return

        # Persist all active session checkpoints
        for session_id, session in self.active_sessions.items():
            if session.state:
                await _save_checkpoint_to_vault(session_id, session.state)

        # Persist cache
        from cohezion.compound.cache_persistence import CachePersistence

        if self.mcp_client:
            cp = CachePersistence()
            await asyncio.to_thread(cp.save_cache, self.mcp_client._cache)

        # Persist metrics
        from cohezion.compound.metrics import get_collector
        from cohezion.compound.metrics_persistence import MetricsPersistence

        col = get_collector()
        mp = MetricsPersistence()
        await asyncio.to_thread(mp.save_snapshot, col)

        # Clear singleton
        OptimizedSessionRuntime._instance = None
        OptimizedSessionRuntime._initialized = False
        logger.info("Clean shutdown complete")

    async def create_session(
        self, session_id: str | None = None, config: SessionConfig | None = None
    ) -> InferenceSession:
        """Create new session with runtime integration."""
        if not self._initialized:
            await self._warm_start()

        session_id = session_id or str(uuid.uuid4())
        session = InferenceSession(session_id=session_id, runtime=self, config=config)
        self.active_sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        return session

    async def end_session(self, session_id: str) -> dict[str, Any]:
        """End session with persistence."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            await _save_checkpoint_to_vault(session_id, session.state)
            del self.active_sessions[session_id]
            return {"status": "success", "session_id": session_id}
        return {"status": "not_found", "session_id": session_id}


class InferenceSession:
    """Manage long-running inference with optimized patterns.

    Implements patterns from changelog:
    - Parallel tool execution (v0.58.0)
    - Async timeouts with retry (v0.64.0)
    - Cancellation support (v0.63.0)
    """

    def __init__(
        self,
        session_id: str,
        runtime: OptimizedSessionRuntime | None = None,
        config: SessionConfig | None = None,
    ):
        self.session_id = session_id
        self.runtime = runtime
        self.config = config or SessionConfig()
        self.state: SessionState | None = None
        self._cancel_event = asyncio.Event()
        self._start_time = time.time()
        self._tool_semaphore: asyncio.Semaphore | None = None
        if self.config.parallel_tool_calls:
            self._tool_semaphore = asyncio.Semaphore(self.config.max_concurrent_tools)

    async def execute_with_checkpoints(
        self,
        skill_name: str,
        input_text: str,
        execute_fn: Callable[[int, SessionState], Awaitable[tuple[str, dict[str, Any]]]],
        total_steps: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute with streaming progress and checkpointing.

        Implements async/await patterns from v0.64.0 with proper timeout handling.
        """
        start_step = 0
        final_output = ""
        total_tokens = 0

        try:
            # Check if checkpoint exists with timeout
            checkpoint = await asyncio.wait_for(
                _load_checkpoint_from_vault(self.session_id),
                timeout=self.config.checkpoint_timeout_sec,
            )
            if checkpoint:
                self.state = checkpoint
                start_step = checkpoint.current_step
                total_steps = checkpoint.total_steps
                logger.info(f"Resumed session {self.session_id} from step {start_step}")
                yield {
                    "type": "resume",
                    "session_id": self.session_id,
                    "from_step": start_step,
                }
            else:
                self.state = SessionState(
                    session_id=self.session_id,
                    skill_name=skill_name,
                    current_step=0,
                    total_steps=total_steps or 10,
                    context=input_text,
                )
                logger.info(f"Started new session {self.session_id}")

            yield {
                "type": "start",
                "session_id": self.session_id,
                "skill_name": skill_name,
                "total_steps": self.state.total_steps,
            }

            # Main execution loop with parallel support (v0.58.0)
            step = start_step
            while step < self.state.total_steps:
                if self._cancel_event.is_set():
                    yield {"type": "cancelled"}
                    return

                # Check timeout
                elapsed = time.time() - self._start_time
                if elapsed > self.config.max_session_duration_sec:
                    yield {
                        "type": "timeout",
                        "elapsed_sec": elapsed,
                    }
                    return

                # Execute step with retry logic (v0.64.0)
                output = ""
                metrics: dict[str, Any] = {}
                for attempt in range(self.config.retry_max_attempts):
                    try:
                        output, metrics = await asyncio.wait_for(
                            execute_fn(step, self.state), timeout=self.config.default_timeout_sec
                        )
                        break
                    except TimeoutError:
                        if attempt == self.config.retry_max_attempts - 1:
                            raise
                        await asyncio.sleep(2**attempt)  # Exponential backoff

                # Update state
                self.state.current_step = step
                self.state.intermediate_results.append(
                    {
                        "step": step,
                        "output": output,
                        "metrics": metrics,
                    }
                )

                if "tokens" in metrics:
                    total_tokens += metrics["tokens"]
                    self.state.model_usage["total_tokens"] = total_tokens

                yield {
                    "type": "step",
                    "step_index": step,
                    "output": output,
                    "metrics": metrics,
                }

                # Checkpoint every N steps
                if step % self.config.checkpoint_interval_steps == 0:
                    await _save_checkpoint_to_vault(self.session_id, self.state)
                    yield {
                        "type": "checkpoint",
                        "step_index": step,
                        "checkpoint_id": f"{self.session_id}_step_{step}",
                    }

                step += 1

            # Final checkpoint
            await _save_checkpoint_to_vault(self.session_id, self.state)
            yield {
                "type": "complete",
                "session_id": self.session_id,
                "final_output": output,
                "total_steps": step,
                "total_tokens": total_tokens,
                "duration_sec": time.time() - self._start_time,
            }

        except TimeoutError as e:
            logger.error(f"Session {self.session_id} timed out: {e}")
            yield {
                "type": "error",
                "error": f"Timeout: {e}",
                "duration_sec": time.time() - self._start_time,
            }
        except Exception as e:
            logger.error(f"Session {self.session_id} failed: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "duration_sec": time.time() - self._start_time,
            }

    async def execute_parallel_tools(
        self,
        tool_calls: list[Callable[[], Awaitable[T]]],
    ) -> list[T]:
        """Execute tool calls in parallel with semaphore control (v0.58.0).

        Pattern from changelog: Tool calls now execute in parallel by default
        """
        if not self.config.parallel_tool_calls or self._tool_semaphore is None:
            # Sequential execution fallback
            results = []
            for call in tool_calls:
                results.append(await call())
            return results

        # Parallel execution with semaphore
        async def bounded_call(call: Callable[[], Awaitable[T]]) -> T:
            async with self._tool_semaphore:
                return await call()

        tasks = [asyncio.create_task(bounded_call(call)) for call in tool_calls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def cancel(self) -> None:
        """Request cancellation of the session (v0.63.0)."""
        self._cancel_event.set()

    async def fork(self, from_step: int) -> InferenceSession:
        """Fork session from specific step (v0.65.0 pattern)."""
        new_session_id = str(uuid.uuid4())
        new_session = await self.runtime.create_session(new_session_id)

        # Copy state up to fork point
        if self.state:
            forked_results = self.state.intermediate_results[:from_step]
            new_session.state = SessionState(
                session_id=new_session_id,
                skill_name=self.state.skill_name,
                current_step=from_step,
                total_steps=self.state.total_steps,
                context=self.state.context,
                intermediate_results=forked_results,
            )

        return new_session


async def _load_checkpoint_from_vault(session_id: str) -> SessionState | None:
    """Load checkpoint with lazy import pattern."""
    try:
        from cohezion.compound.exp_persistence.vault import _vault_checkpoint_manager

        return await asyncio.to_thread(_vault_checkpoint_manager.load, session_id)
    except Exception as e:
        logger.debug(f"No checkpoint found for {session_id}: {e}")
        return None


async def _save_checkpoint_to_vault(session_id: str, state: SessionState) -> None:
    """Save checkpoint with lazy import pattern."""
    try:
        from cohezion.compound.exp_persistence.vault import _vault_checkpoint_manager

        await asyncio.to_thread(_vault_checkpoint_manager.save, session_id, state)
    except Exception as e:
        logger.warning(f"Failed to save checkpoint for {session_id}: {e}")


class CompoundSessionManager:
    """Public API for optimized session management.

    Implements warm-start/clean-shutdown pattern from v0.65.0 changelog.
    """

    def __init__(self):
        self._runtime: OptimizedSessionRuntime | None = None

    async def __aenter__(self) -> CompoundSessionManager:
        """Async context manager entry with warm-start."""
        self._runtime = await OptimizedSessionRuntime.get_instance()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with clean-shutdown."""
        if self._runtime:
            await self._runtime.clean_shutdown()

    async def start_session(self, skill_name: str = "auto", max_cache_entries: int = 256) -> dict[str, Any]:
        """Start new session with warming (v0.65.0 pattern)."""
        if not self._runtime:
            self._runtime = await OptimizedSessionRuntime.get_instance()

        session = await self._runtime.create_session()
        return {
            "session_id": session.session_id,
            "skill_name": skill_name,
            "cache_warm": True,
            "max_cache_entries": max_cache_entries,
        }

    async def execute_aligned(
        self,
        request: str,
        execute_fn: Callable[[], Awaitable[dict[str, Any]]],
        skill_name: str = "auto",
        threshold: float = 0.5,
    ) -> tuple[bool, dict[str, Any]]:
        """Alignment gate before execution (HIHO pattern from v0.65.0).

        High coherence (> threshold) -> proceeds
        Low coherence (< threshold) -> blocked
        """
        # Check alignment
        alignment = await self._check_alignment(request, threshold)
        if not alignment["should_proceed"]:
            logger.warning(f"Low alignment: {alignment['issues']}")
            return False, alignment

        # Execute
        result = await execute_fn()
        return True, result

    async def _check_alignment(self, request: str, threshold: float) -> dict[str, Any]:
        """Check request alignment (HIHO pattern)."""
        # Simple coherence check (placeholder for actual implementation)
        coherence = 0.8 if len(request) > 10 else 0.3
        return {
            "coherence": coherence,
            "should_proceed": coherence > threshold,
            "issues": [] if coherence > threshold else ["ambiguous request"],
        }

    async def end_session(self) -> dict[str, Any]:
        """End session with clean shutdown."""
        if self._runtime:
            await self._runtime.clean_shutdown()
            result = {"status": "shutdown_complete"}
            self._runtime = None
            return result
        return {"status": "no_session"}


# Convenience function for simple usage
async def create_optimized_session(skill_name: str = "auto", config: SessionConfig | None = None) -> InferenceSession:
    """Create optimized session with warm-start."""
    runtime = await OptimizedSessionRuntime.get_instance()
    return await runtime.create_session(config=config)
