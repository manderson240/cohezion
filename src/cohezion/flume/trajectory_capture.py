"""Context manager for capturing competition trajectories into FLUME.

Usage::

    from cohezion.flume.trajectory_capture import capture_trajectory

    with capture_trajectory("aimo", agent_id="solver-1") as capture:
        result = solver.solve(problem)
        capture.record(
            state={"difficulty": 7, "confidence": 0.9, "correctness": 1.0},
            action="solve",
            reward=1.0 if result.correct else 0.0,
        )

On context-manager exit the accumulated trajectory points are persisted
to SurrealDB ``journey_transitions`` (best-effort, non-blocking on failure).
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from cohezion.flume.domain_encoder import EncodedTrajectoryPoint, get_encoder


logger = logging.getLogger(__name__)


class TrajectoryRecorder:
    """Accumulates trajectory points within a ``capture_trajectory`` block."""

    def __init__(self, domain: str, agent_id: str) -> None:
        self.domain = domain
        self.agent_id = agent_id
        self.trajectory_id = str(uuid4())
        self.start_time = time.monotonic()
        self._encoder = get_encoder(domain)
        self._points: list[EncodedTrajectoryPoint] = []

    def record(
        self,
        state: dict,
        action: str,
        reward: float,
        **extra: Any,
    ) -> EncodedTrajectoryPoint:
        """Encode *state* and append to the trajectory buffer."""
        pt = self._encoder.encode_point(
            state,
            action=action,
            reward=reward,
            agent_id=self.agent_id,
            trajectory_id=self.trajectory_id,
            elapsed=time.monotonic() - self.start_time,
            **extra,
        )
        self._points.append(pt)
        return pt

    @property
    def points(self) -> list[EncodedTrajectoryPoint]:
        return list(self._points)


@contextmanager
def capture_trajectory(domain: str, agent_id: str = "default"):
    """Capture competition trajectory points and persist on exit.

    Yields a :class:`TrajectoryRecorder` that callers use to ``record()``
    individual state transitions.  On exit the collected points are
    written to SurrealDB via ``genesis_persistence`` (best-effort).
    """
    recorder = TrajectoryRecorder(domain, agent_id)
    try:
        yield recorder
    finally:
        if recorder.points:
            _persist_points(recorder)


def _persist_points(recorder: TrajectoryRecorder) -> None:
    """Best-effort persistence of trajectory points."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_async_persist(recorder))
    except RuntimeError:
        # No event loop -- run synchronously in a fresh loop
        try:
            asyncio.run(_async_persist(recorder))
        except Exception:
            logger.debug(
                "Trajectory persistence skipped (no async runtime): %s",
                recorder.trajectory_id,
            )


async def _async_persist(recorder: TrajectoryRecorder) -> None:
    """Write trajectory points to SurrealDB ``journey_transitions``."""
    try:
        from cohezion.persistence.genesis_persistence import store_journey_transition

        for pt in recorder.points:
            await store_journey_transition(
                journey_id=recorder.trajectory_id,
                state=pt.state_12d.tolist(),
                action=pt.action_description,
                reward=pt.reward,
                next_state=pt.state_12d.tolist(),
                metadata={
                    "domain": pt.domain,
                    "agent_id": recorder.agent_id,
                    "surprise": pt.surprise,
                    **pt.metadata,
                },
            )
        logger.debug(
            "Persisted %d trajectory points for %s",
            len(recorder.points),
            recorder.trajectory_id,
        )
    except Exception:
        logger.debug(
            "Trajectory persistence failed for %s (SurrealDB unavailable)",
            recorder.trajectory_id,
        )
