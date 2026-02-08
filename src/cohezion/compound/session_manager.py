"""Long-running inference session management with checkpointing.

Features:
- Multi-hour inference with automatic checkpointing
- Graceful resumption from checkpoint on failure
- Streaming progress via SSE events
- Graceful cancellation with timeout enforcement
- Vault-backed persistence (JSONL fallback)
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

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
                    self.state.model_usage[model] = (
                        self.state.model_usage.get(model, 0) + tokens
                    )

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
                            time.time() - self.state.last_checkpoint_time
                            > self.config.checkpoint_timeout_sec
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
                "error": f"Session failed: {str(e)}",
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
            # TODO: Wire to cohezion.core.mcp_client.MCPClient for vault persistence
            pass
        except Exception as e:
            logger.debug(f"Vault save failed, using JSONL fallback: {e}")

        # Fallback to local JSONL
        try:
            checkpoint_file = self.local_checkpoint_dir / f"{state.session_id}.json"
            with open(checkpoint_file, "w") as f:
                json.dump(asdict(state), f, indent=2)
            logger.debug(f"Checkpoint saved to {checkpoint_file}")
            return True
        except Exception as e:
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
        # TODO: Wire to MCPClient for vault lookup
        pass

        # Fallback to local JSONL
        try:
            checkpoint_file = self.local_checkpoint_dir / f"{session_id}.json"
            if checkpoint_file.exists():
                with open(checkpoint_file) as f:
                    data = json.load(f)
                state = SessionState(**data)
                logger.debug(f"Checkpoint loaded from {checkpoint_file}")
                return state
        except Exception as e:
            logger.exception("Checkpoint load failed")

        return None

    async def delete(self, session_id: str) -> bool:
        """Clean up checkpoint after successful completion.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully
        """
        # Try vault first
        # TODO: Wire to MCPClient
        pass

        # Clean local file
        try:
            checkpoint_file = self.local_checkpoint_dir / f"{session_id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                logger.debug(f"Checkpoint deleted: {checkpoint_file}")
                return True
        except Exception as e:
            logger.exception("Checkpoint delete failed")

        return False


# Global checkpoint manager
_vault_checkpoint_manager = VaultCheckpointManager()


# Session registry
_sessions: dict[str, InferenceSession] = {}


def create_session(
    session_id: str | None = None, config: SessionConfig | None = None
) -> InferenceSession:
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
