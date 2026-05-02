"""Long-running inference session management with checkpointing.

Features:
- Multi-hour inference with automatic checkpointing
- Graceful resumption from checkpoint on failure
- Streaming progress via SSE events
- Graceful cancellation with timeout enforcement
- Vault-backed persistence (JSONL fallback)
- Compound session lifecycle (warm-start / clean-shutdown)
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from cohezion.core.mcp_client import get_mcp_client


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
    # Cost tracking (new in cost optimization initiative)
    total_cost_usd: float = 0.0
    cost_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class SessionConfig:
    """Configuration for inference session."""

    checkpoint_interval_steps: int = 5
    checkpoint_timeout_sec: float = 300.0
    max_session_duration_sec: float = 7200.0
    enable_streaming: bool = True
    vault_persistence: bool = True


class InferenceSession:
    """Manage long-running inference with checkpointing.

    Lifecycle:
        1. create_session() - Create new session with ID
        2. execute_with_checkpoints() - Stream progress events
        3. Checkpoint every N steps or M seconds
        4. On resume, load checkpoint and continue
        5. On complete, cleanup checkpoints
    """

    def __init__(
        self,
        session_id: str,
        config: SessionConfig | None = None,
    ):
        """Initialize session.

        Args:
            session_id: Unique session identifier
            config: Session configuration
        """
        self.session_id = session_id
        self.config = config or SessionConfig()
        self.state: SessionState | None = None
        self._cancel_event = asyncio.Event()
        self._start_time = time.time()

    async def execute_with_checkpoints(
        self,
        skill_name: str,
        input_text: str,
        execute_fn,
        total_steps: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute with streaming progress and checkpointing.

        Yields events:
            - {"type": "start", "session_id": str, "total_steps": int}
            - {"type": "resume", "from_step": int}
            - {"type": "step", "step_index": int, "output": str, "tokens": int}
            - {"type": "checkpoint", "step_index": int}
            - {"type": "complete", "final_output": str, "total_tokens": int}
            - {"type": "error", "error": str}
            - {"type": "cancelled"}
            - {"type": "timeout", "elapsed_sec": float}

        Args:
            skill_name: Name of skill being executed
            input_text: Input to skill
            execute_fn: Async function that takes (step_index, state) and returns (output, metrics)
            total_steps: Estimated total steps (if known)

        Yields:
            Event dictionaries for streaming
        """
        start_step = 0
        final_output = ""
        total_tokens = 0

        try:
            # Check if checkpoint exists
            checkpoint = await _vault_checkpoint_manager.load(self.session_id)
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
                # New session
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

            # Execute steps
            step_idx = start_step
            while step_idx < (self.state.total_steps):
                # Check for timeout
                elapsed = time.time() - self._start_time
                if elapsed > self.config.max_session_duration_sec:
                    yield {
                        "type": "timeout",
                        "elapsed_sec": elapsed,
                    }
                    break

                # Check for cancellation
                if self._cancel_event.is_set():
                    yield {"type": "cancelled"}
                    break

                # Execute step
                try:
                    output, metrics = await execute_fn(step_idx, self.state)
                    tokens = metrics.get("tokens", 0)
                    total_tokens += tokens

                    self.state.current_step = step_idx
                    self.state.intermediate_results.append(
                        {
                            "step": step_idx,
                            "output": output,
                            "tokens": tokens,
                            "timestamp": time.time(),
                        }
                    )

                    # Update model usage
                    model = metrics.get("model", "unknown")
                    self.state.model_usage[model] = self.state.model_usage.get(model, 0) + tokens

                    final_output = output

                    yield {
                        "type": "step",
                        "step_index": step_idx,
                        "output": output[:500],  # Truncate for streaming
                        "tokens": tokens,
                        "total_tokens": total_tokens,
                    }

                    # Checkpoint if needed
                    if (step_idx + 1) % self.config.checkpoint_interval_steps == 0:
                        should_checkpoint = (
                            time.time() - self.state.last_checkpoint_time > self.config.checkpoint_timeout_sec
                        )
                        if should_checkpoint:
                            await _vault_checkpoint_manager.save(self.state)
                            self.state.last_checkpoint_time = time.time()
                            yield {
                                "type": "checkpoint",
                                "step_index": step_idx,
                                "session_id": self.session_id,
                            }

                    step_idx += 1

                except Exception as e:
                    logger.exception(f"Step {step_idx} failed")
                    yield {
                        "type": "error",
                        "step_index": step_idx,
                        "error": str(e),
                    }
                    break

            # Final checkpoint
            if self.state:
                await _vault_checkpoint_manager.save(self.state)

            # Completion
            yield {
                "type": "complete",
                "session_id": self.session_id,
                "final_output": final_output,
                "total_tokens": total_tokens,
                "total_steps": step_idx,
            }

            # Cleanup
            await _vault_checkpoint_manager.delete(self.session_id)

        except Exception as e:
            logger.exception("Session execution failed")
            yield {
                "type": "error",
                "error": f"Session failed: {e!s}",
            }

    def cancel(self) -> None:
        """Request graceful cancellation."""
        self._cancel_event.set()
        logger.info(f"Cancellation requested for session {self.session_id}")

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_event.is_set()


class VaultCheckpointManager:
    """Persist session checkpoints to vault or local JSONL."""

    def __init__(self, local_checkpoint_dir: str = "data/checkpoints"):
        """Initialize checkpoint manager.

        Args:
            local_checkpoint_dir: Directory for local JSONL fallback
        """
        self.local_checkpoint_dir = Path(local_checkpoint_dir)
        self.local_checkpoint_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, state: SessionState) -> bool:
        """Save checkpoint to vault (primary) or JSONL (fallback).

        Args:
            state: Session state to save

        Returns:
            True if saved successfully
        """
        try:
            # Try vault first
            mcp = get_mcp_client()
            path = f"checkpoints/{state.session_id}.json"
            mcp.vault_write(path, json.dumps(asdict(state), indent=2))
            logger.debug(f"Checkpoint saved to Vault: {path}")
            return True
        except Exception as e:
            logger.debug(f"Vault save failed, using JSONL fallback: {e}")

        # Fallback to local JSONL
        try:
            checkpoint_file = self.local_checkpoint_dir / f"{state.session_id}.json"
            with open(checkpoint_file, "w") as f:
                json.dump(asdict(state), f, indent=2)
            logger.debug(f"Checkpoint saved to {checkpoint_file}")
            return True
        except Exception:
            logger.exception("Checkpoint save failed")
            return False

    async def load(self, session_id: str) -> SessionState | None:
        """Load checkpoint from vault or JSONL.

        Args:
            session_id: Session ID to load

        Returns:
            SessionState if found, None otherwise
        """
        # Try vault first
        try:
            mcp = get_mcp_client()
            path = f"checkpoints/{session_id}.json"
            content = mcp.vault_read(path)
            data = json.loads(content)
            state = SessionState(**data)
            logger.debug(f"Checkpoint loaded from Vault: {path}")
            return state
        except Exception as e:
            logger.debug(f"Vault load failed: {e}")

        # Fallback to local JSONL
        try:
            checkpoint_file = self.local_checkpoint_dir / f"{session_id}.json"
            if checkpoint_file.exists():
                with open(checkpoint_file) as f:
                    data = json.load(f)
                state = SessionState(**data)
                logger.debug(f"Checkpoint loaded from {checkpoint_file}")
                return state
        except Exception:
            logger.exception("Checkpoint load failed")

        return None

    async def delete(self, session_id: str) -> bool:
        """Clean up checkpoint after successful completion.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully (from either vault or local)
        """
        vault_deleted = False
        local_deleted = False

        # Try vault first
        try:
            mcp = get_mcp_client()
            path = f"checkpoints/{session_id}.json"
            mcp.vault_delete(path)
            logger.debug(f"Checkpoint deleted from Vault: {path}")
            vault_deleted = True
        except Exception as e:
            logger.debug(f"Vault delete failed: {e}")

        # Clean local file
        try:
            checkpoint_file = self.local_checkpoint_dir / f"{session_id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                logger.debug(f"Checkpoint deleted: {checkpoint_file}")
                local_deleted = True
        except Exception:
            logger.exception("Checkpoint delete failed")

        # Return True if deleted from either location
        return vault_deleted or local_deleted


# Global checkpoint manager
_vault_checkpoint_manager = VaultCheckpointManager()


# Session registry
_sessions: dict[str, InferenceSession] = {}


def create_session(session_id: str | None = None, config: SessionConfig | None = None) -> InferenceSession:
    """Create and register new session.

    Args:
        session_id: Unique session ID (generated if not provided)
        config: Session configuration

    Returns:
        InferenceSession ready for execution
    """
    if not session_id:
        session_id = f"session_{int(time.time())}_{id(object())}"

    session = InferenceSession(session_id, config)
    _sessions[session_id] = session
    logger.info(f"Created session {session_id}")
    return session


def get_session(session_id: str) -> InferenceSession | None:
    """Get active session.

    Args:
        session_id: Session ID

    Returns:
        InferenceSession if active, None otherwise
    """
    return _sessions.get(session_id)


def list_sessions() -> list[str]:
    """Get list of active session IDs."""
    return list(_sessions.keys())


def close_session(session_id: str) -> bool:
    """Close and unregister session.

    Args:
        session_id: Session ID

    Returns:
        True if closed successfully
    """
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info(f"Closed session {session_id}")
        return True
    return False


# ---------------------------------------------------------------------------
# Compound session lifecycle (warm-start / clean-shutdown)
# ---------------------------------------------------------------------------


class AlignmentResult(BaseModel):
    """Result of alignment check before execution."""

    coherence: float = 0.0
    intent_match: float = 0.0
    constraint_satisfaction: float = 0.0
    should_proceed: bool = True
    issues: list[str] = []
    recommendations: list[str] = []


class SessionSummary(BaseModel):
    """Summary of a compound session."""

    session_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    cache_entries_loaded: int = 0
    cache_entries_saved: int = 0
    metrics_restored: bool = False
    metrics_saved: bool = False
    total_executions: int = 0
    total_tokens: int = 0


class CompoundSessionManager:
    """Manage compound session lifecycle: warm start and clean shutdown."""

    def __init__(self) -> None:
        self._session_id: str = ""
        self._start_time: float = 0.0
        self._cache_loaded: int = 0
        self._metrics_restored: bool = False

    def start_session(self, max_cache_entries: int = 256) -> SessionSummary:
        """Start a new compound session: warm cache and load metrics."""
        self._session_id = f"session_{uuid.uuid4().hex[:8]}"
        self._start_time = time.time()

        # Warm cache
        from cohezion.compound.cache_persistence import WarmCacheLoader

        try:
            from cohezion.swarm.compound_client import get_compound_client

            client = get_compound_client()
            loader = WarmCacheLoader()
            self._cache_loaded = loader.warm_client(client, max_cache_entries)
        except Exception:
            logger.debug("Cache warm failed (non-critical)")
            self._cache_loaded = 0

        # Restore metrics
        from cohezion.compound.metrics_persistence import MetricsPersistence

        try:
            from cohezion.compound.metrics import get_collector

            collector = get_collector()
            mp = MetricsPersistence()
            snapshot = mp.load_latest_snapshot()
            if snapshot:
                collector.load_from_snapshot(snapshot)
                self._metrics_restored = True
        except Exception:
            logger.debug("Metrics restore failed (non-critical)")

        return SessionSummary(
            session_id=self._session_id,
            start_time=self._start_time,
            cache_entries_loaded=self._cache_loaded,
            metrics_restored=self._metrics_restored,
        )

    def end_session(self) -> SessionSummary:
        """End session: persist cache and metrics."""
        from cohezion.compound.cache_persistence import CachePersistence

        cache_saved = 0
        try:
            from cohezion.swarm.compound_client import get_compound_client

            client = get_compound_client()
            cp = CachePersistence()
            cache_saved = cp.save_cache(client._cache)
        except Exception:
            logger.debug("Cache save failed (non-critical)")

        # Save metrics
        from cohezion.compound.metrics_persistence import MetricsPersistence

        metrics_saved = False
        total_executions = 0
        total_tokens = 0
        try:
            from cohezion.compound.metrics import get_collector

            collector = get_collector()
            mp = MetricsPersistence()
            mp.save_snapshot(collector)
            metrics_saved = True
            total_executions = collector.total_executions
            total_tokens = collector.total_tokens()
        except Exception:
            logger.debug("Metrics save failed (non-critical)")

        return SessionSummary(
            session_id=self._session_id,
            start_time=self._start_time,
            end_time=time.time(),
            cache_entries_loaded=self._cache_loaded,
            cache_entries_saved=cache_saved,
            metrics_restored=self._metrics_restored,
            metrics_saved=metrics_saved,
            total_executions=total_executions,
            total_tokens=total_tokens,
        )

    async def __aenter__(self) -> "CompoundSessionManager":
        """Start session on async context entry."""
        self.start_session()
        return self

    async def __aexit__(self, *exc: object) -> None:
        """End session on async context exit."""
        self.end_session()

    def get_current_session(self) -> SessionSummary | None:
        """Return current session info, or None if no active session."""
        if not self._session_id:
            return None
        return SessionSummary(
            session_id=self._session_id,
            start_time=self._start_time,
            cache_entries_loaded=self._cache_loaded,
            metrics_restored=self._metrics_restored,
        )

    def check_alignment(
        self,
        request: str,
        skills: list[str] | None = None,
        context: dict[str, Any] | None = None,
        threshold: float = 0.5,
    ) -> AlignmentResult:
        """Check request alignment before execution.

        Implements the HIHO stability gate: requests with coherence below
        the threshold should be decomposed or escalated rather than executed.

        Parameters
        ----------
        request : str
            Raw request text to analyze
        skills : list[str] | None
            Available skills for skill matching (optional)
        context : dict[str, Any] | None
            Additional context (project, prior decisions, etc.)
        threshold : float
            Minimum coherence to proceed (default 0.5 = HIHO)

        Returns
        -------
        AlignmentResult
            Coherence score, issues, and proceed recommendation
        """
        from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzerFactory

        try:
            mcp_client = get_mcp_client()
            analyzer = RequestAlignmentAnalyzerFactory.create(mcp_client)
            parsed = analyzer.parse_request(request)

            intent_conf = parsed.intent_confidence
            constraint_sat = 1.0 - (len(parsed.constraints) * 0.1) if parsed.constraints else 1.0
            criteria_sat = 1.0 - (len(parsed.criteria) * 0.1) if parsed.criteria else 1.0

            coherence = 0.4 * intent_conf + 0.3 * constraint_sat + 0.3 * criteria_sat

            issues = []
            recommendations = []

            if parsed.intent_confidence < 0.3:
                issues.append(f"Low intent confidence: {parsed.intent_confidence:.2f}")
                recommendations.append("Clarify request intent")

            if len(parsed.constraints) > 3:
                issues.append(f"Many constraints ({len(parsed.constraints)})")
                recommendations.append("Consider decomposing request")

            should_proceed = coherence >= threshold

            if not should_proceed:
                issues.append(f"Coherence {coherence:.2f} below threshold {threshold}")
                recommendations.append("Decompose request or escalate")

            return AlignmentResult(
                coherence=coherence,
                intent_match=intent_conf,
                constraint_satisfaction=constraint_sat,
                should_proceed=should_proceed,
                issues=issues,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.warning("Alignment check failed (non-blocking): %s", e)
            return AlignmentResult(
                coherence=1.0,
                intent_match=1.0,
                constraint_satisfaction=1.0,
                should_proceed=True,
                issues=[],
                recommendations=[],
            )

    async def execute_aligned(
        self,
        request: str,
        execute_fn,
        skill_name: str = "auto",
        operation_type: str = "generate",
        skills: list[str] | None = None,
        threshold: float = 0.5,
    ) -> tuple[bool, dict[str, Any]]:
        """Execute with alignment gate and inflection logging.

        This is the compound engineering preferred path:
        1. Check alignment (HIHO gate)
        2. If alignment >= threshold, execute
        3. Log inflection points for critical anomalies
        4. Return success/failure with metrics

        Parameters
        ----------
        request : str
            Raw request text
        execute_fn : Callable
            Async function to execute (receives no args, returns output)
        skill_name : str
            Skill name for logging (default "auto")
        operation_type : str
            Operation type for alignment analysis
        skills : list[str] | None
            Available skills for matching
        threshold : float
            Minimum alignment coherence (default 0.5)

        Returns
        -------
        tuple[bool, dict[str, Any]]
            (success, metrics_dict)
        """
        if not self._session_id:
            self.start_session()

        alignment = self.check_alignment(request, skills, threshold=threshold)

        if not alignment.should_proceed:
            logger.warning(
                "Alignment gate blocked execution: coherence=%.2f < threshold=%.2f",
                alignment.coherence,
                threshold,
            )
            return False, {
                "error": "Alignment below threshold",
                "coherence": alignment.coherence,
                "issues": alignment.issues,
                "recommendations": alignment.recommendations,
                "blocked_at": "alignment_gate",
            }

        start_time = time.time()
        try:
            output = await execute_fn() if callable(execute_fn) else execute_fn
            duration = time.time() - start_time

            return True, {
                "output": output,
                "duration_seconds": duration,
                "coherence": alignment.coherence,
                "intent_match": alignment.intent_match,
                "session_id": self._session_id,
            }

        except Exception as e:
            logger.exception("Aligned execution failed")
            return False, {
                "error": str(e),
                "coherence": alignment.coherence,
                "session_id": self._session_id,
            }
