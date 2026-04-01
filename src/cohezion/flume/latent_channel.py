"""LatentMAS Communication Channel — Agent-to-Agent via FLUME Vectors.

Implements the LatentMAS pattern (arXiv:2511.20639) where agents exchange
256D FLUME embeddings instead of serialized text. Training-free, 24x latency
reduction vs text communication.

Architecture:
  1. Agent A encodes its internal state via FLUME → 256D vector
  2. Vector stored in SharedLatentMemory (central buffer)
  3. Agent B retrieves from buffer → decodes to understand A's state
  4. Communication is lossless (no text serialization bottleneck)

The SharedLatentMemory acts as a KV cache transfer mechanism where each
agent's embeddings are keyed by agent_id + timestamp.

References:
    - LatentMAS (arXiv:2511.20639): Training-free multi-agent latent collaboration
    - Interlat (arXiv:2511.09149): 24x latency reduction via latent communication
    - DeepMind KV Alignment (arXiv:2601.06123): Multi-model latent coherence
    - Learning 226: FLUME 256D embeddings ARE the communication channel

Wired to: CompoundExecutor (execution context), TeamOrchestrator (agent routing)
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt


logger = logging.getLogger(__name__)


@dataclass
class LatentMessage:
    """A message in the latent communication channel."""

    agent_id: str
    embedding: npt.NDArray[np.float64]  # 256D FLUME vector
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    operation_type: str = ""  # What the agent was doing when it produced this


class SharedLatentMemory:
    """Central buffer for agent latent state transfer.

    Agents deposit their FLUME embeddings here after execution.
    Other agents retrieve relevant embeddings before their own execution,
    enabling training-free latent collaboration.

    The buffer is a deque with configurable max size (default 100 per agent).
    """

    def __init__(self, max_per_agent: int = 100) -> None:
        self._buffers: dict[str, deque[LatentMessage]] = {}
        self._max_per_agent = max_per_agent

    def deposit(self, message: LatentMessage) -> None:
        """Deposit an agent's latent state into the shared buffer.

        Args:
            message: LatentMessage with agent_id and 256D embedding
        """
        if message.agent_id not in self._buffers:
            self._buffers[message.agent_id] = deque(maxlen=self._max_per_agent)
        self._buffers[message.agent_id].append(message)
        logger.debug(
            "Latent deposit: agent=%s, dim=%d, buffer_size=%d",
            message.agent_id,
            len(message.embedding),
            len(self._buffers[message.agent_id]),
        )

    def retrieve(
        self,
        requesting_agent: str,
        n_recent: int = 5,
        exclude_self: bool = True,
    ) -> list[LatentMessage]:
        """Retrieve recent latent messages from other agents.

        Args:
            requesting_agent: Agent requesting the context
            n_recent: Number of recent messages per agent
            exclude_self: Whether to exclude own messages

        Returns:
            List of LatentMessage from other agents, most recent first
        """
        messages: list[LatentMessage] = []
        for agent_id, buffer in self._buffers.items():
            if exclude_self and agent_id == requesting_agent:
                continue
            recent = list(buffer)[-n_recent:]
            messages.extend(recent)

        # Sort by recency
        messages.sort(key=lambda m: m.timestamp, reverse=True)
        return messages

    def get_consensus_embedding(
        self, exclude_agent: str | None = None
    ) -> npt.NDArray[np.float64] | None:
        """Compute consensus embedding from all agents' most recent states.

        Averages the most recent embedding from each active agent.
        This represents the "group understanding" in latent space.

        Args:
            exclude_agent: Agent to exclude from consensus

        Returns:
            Mean embedding (256D) or None if no data
        """
        embeddings: list[npt.NDArray[np.float64]] = []
        for agent_id, buffer in self._buffers.items():
            if exclude_agent and agent_id == exclude_agent:
                continue
            if buffer:
                embeddings.append(buffer[-1].embedding)

        if not embeddings:
            return None

        return np.mean(embeddings, axis=0)

    def coherence_score(self) -> float:
        """Compute inter-agent coherence from latent embeddings.

        High coherence means agents are in similar latent states (aligned).
        Uses average pairwise cosine similarity of most recent embeddings.

        Returns:
            Coherence score [0, 1]
        """
        embeddings: list[npt.NDArray[np.float64]] = []
        for buffer in self._buffers.values():
            if buffer:
                embeddings.append(buffer[-1].embedding)

        if len(embeddings) < 2:
            return 1.0  # Single agent = perfect coherence

        # Pairwise cosine similarities
        similarities: list[float] = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                a, b = embeddings[i], embeddings[j]
                norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
                if norm_a > 0 and norm_b > 0:
                    sim = np.dot(a, b) / (norm_a * norm_b)
                    similarities.append(float(sim))

        return float(np.mean(similarities)) if similarities else 1.0

    @property
    def active_agents(self) -> list[str]:
        """List agents with at least one deposited message."""
        return [aid for aid, buf in self._buffers.items() if buf]

    @property
    def total_messages(self) -> int:
        """Total messages across all agent buffers."""
        return sum(len(buf) for buf in self._buffers.values())


# Singleton shared memory
_shared_memory: SharedLatentMemory | None = None


def get_shared_latent_memory() -> SharedLatentMemory:
    """Get the global SharedLatentMemory instance."""
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = SharedLatentMemory()
    return _shared_memory


__all__ = [
    "LatentMessage",
    "SharedLatentMemory",
    "get_shared_latent_memory",
]
