"""
Shared Context - Thread-safe shared state for swarm agents.

Provides a central store for:
- Conversation history
- Cached embeddings
- Task queue state
- Cross-agent communication
"""

import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    role: str  # "user", "analyst", "critic", "synthesizer"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class SharedContext:
    """
    Thread-safe shared context for swarm agents.

    Allows agents to share state, communicate, and maintain
    persistent conversation history.
    """

    def __init__(
        self,
        max_history: int = 100,
        persist_path: Path | None = None,
    ):
        self.max_history = max_history
        self.persist_path = persist_path

        self._lock = threading.RLock()
        self._history: deque[ConversationTurn] = deque(maxlen=max_history)
        self._cache: dict[str, Any] = {}
        self._task_queue: deque[dict[str, Any]] = deque()
        self._agent_state: dict[str, dict[str, Any]] = {}

        # Load persisted state if available
        if persist_path and persist_path.exists():
            self._load()

    # --- History Management ---

    def add_turn(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a conversation turn to history."""
        with self._lock:
            turn = ConversationTurn(
                role=role,
                content=content,
                metadata=metadata or {},
            )
            self._history.append(turn)
            self._auto_persist()

    def get_history(self, limit: int | None = None) -> list[ConversationTurn]:
        """Get recent conversation history."""
        with self._lock:
            history = list(self._history)
            if limit:
                return history[-limit:]
            return history

    def get_formatted_history(self, limit: int = 10) -> str:
        """Get history formatted for inclusion in prompts."""
        turns = self.get_history(limit)
        lines = []
        for turn in turns:
            lines.append(f"[{turn.role.upper()}]: {turn.content[:500]}")
        return "\n\n".join(lines)

    # --- Cache Management ---

    def cache_get(self, key: str) -> Any | None:
        """Get a cached value."""
        with self._lock:
            return self._cache.get(key)

    def cache_set(self, key: str, value: Any) -> None:
        """Set a cached value."""
        with self._lock:
            self._cache[key] = value
            self._auto_persist()

    def cache_clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

    # --- Task Queue ---

    def enqueue_task(self, task: dict[str, Any]) -> None:
        """Add a task to the queue."""
        with self._lock:
            task["enqueued_at"] = datetime.now().isoformat()
            self._task_queue.append(task)
            self._auto_persist()

    def dequeue_task(self) -> dict[str, Any] | None:
        """Remove and return the next task, or None if empty."""
        with self._lock:
            if self._task_queue:
                return self._task_queue.popleft()
            return None

    def peek_tasks(self, limit: int = 10) -> list[dict[str, Any]]:
        """View pending tasks without removing them."""
        with self._lock:
            return list(self._task_queue)[:limit]

    # --- Agent State ---

    def set_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Store state for a specific agent."""
        with self._lock:
            self._agent_state[agent_id] = {
                **state,
                "updated_at": datetime.now().isoformat(),
            }

    def get_agent_state(self, agent_id: str) -> dict[str, Any]:
        """Get state for a specific agent."""
        with self._lock:
            return self._agent_state.get(agent_id, {})

    def get_all_agent_states(self) -> dict[str, dict[str, Any]]:
        """Get all agent states."""
        with self._lock:
            return dict(self._agent_state)

    # --- Persistence ---

    def _auto_persist(self) -> None:
        """Automatically persist if path is configured."""
        if self.persist_path:
            self._save()

    def _save(self) -> None:
        """Save state to disk."""
        if not self.persist_path:
            return

        try:
            data = {
                "history": [
                    {
                        "role": t.role,
                        "content": t.content,
                        "timestamp": t.timestamp.isoformat(),
                        "metadata": t.metadata,
                    }
                    for t in self._history
                ],
                "cache": self._cache,
                "task_queue": list(self._task_queue),
                "agent_state": self._agent_state,
            }
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            self.persist_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to persist context: {e}")

    def _load(self) -> None:
        """Load state from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return

        try:
            data = json.loads(self.persist_path.read_text())

            for h in data.get("history", []):
                self._history.append(
                    ConversationTurn(
                        role=h["role"],
                        content=h["content"],
                        timestamp=datetime.fromisoformat(h["timestamp"]),
                        metadata=h.get("metadata", {}),
                    )
                )

            self._cache = data.get("cache", {})
            self._task_queue = deque(data.get("task_queue", []))
            self._agent_state = data.get("agent_state", {})

        except Exception as e:
            logger.error(f"Failed to load context: {e}")

    def __repr__(self) -> str:
        return (
            f"SharedContext(history={len(self._history)}, "
            f"cache={len(self._cache)}, tasks={len(self._task_queue)})"
        )
