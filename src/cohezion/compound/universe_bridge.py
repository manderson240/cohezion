"""Bridge between compound executor journeys and universe simulation engine.

Converts JourneyTracker's TrajectoryPoints (12-parameter vectors) into
the UniverseSimulationEngine's AxiomaticState model, creating real
universe journeys from compound executions.

Lifecycle:
  1. start_journey() - Create UniverseJourney at execution start
  2. add_point() - Convert TrajectoryPoint to AxiomaticState, append
  3. complete_journey() - Finalize with phi_score and precipitation
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


class UniverseBridge:
    """Adapter connecting compound executor to universe simulation engine.

    Converts 12D trajectory points from JourneyTracker into AxiomaticState
    objects organized by fabric (Space, Field, Control, Precipitation).

    Parameters
    ----------
    engine : UniverseSimulationEngine, optional
        If None, bridge operates in no-op mode (graceful degradation).
    agent_name : str
        Name of the agent creating journeys.
    """

    # Mapping from 12D vector indices to AxiomaticState fabric dimensions
    # Space fabric: indices 0-2
    # Field fabric: indices 3-5
    # Control fabric: indices 6-8
    # Precipitation fabric: indices 9-11
    _DIM_NAMES = [
        "spatial_x",
        "spatial_y",
        "spatial_z",  # Space
        "physics",
        "biology",
        "field",  # Field
        "logic",
        "quantum",
        "control",  # Control
        "temporal",
        "novelty",
        "precipitation",  # Precipitation
    ]

    def __init__(
        self,
        engine: Any | None = None,
        agent_name: str = "compound-executor",
    ) -> None:
        self._engine = engine
        self._agent_name = agent_name
        self._active_journeys: dict[str, Any] = {}

    def _vector_to_axiomatic(self, vector_12d: Any) -> Any:
        """Convert a 12D numpy vector to an AxiomaticState.

        Parameters
        ----------
        vector_12d : np.ndarray
            12-dimensional trajectory point.

        Returns
        -------
        AxiomaticState
            Universe engine state organized by fabric.
        """
        import numpy as np

        from cohezion.universe.engine import AxiomaticState

        arr = np.asarray(vector_12d, dtype=float).ravel()
        # Pad to 12 if needed
        if len(arr) < 12:
            padded = np.zeros(12)
            padded[: len(arr)] = arr
            arr = padded

        return AxiomaticState(
            spatial_x=float(arr[0]),
            spatial_y=float(arr[1]),
            spatial_z=float(arr[2]),
            physics=float(arr[3]),
            biology=float(arr[4]),
            field=float(arr[5]),
            logic=float(arr[6]),
            quantum=float(arr[7]),
            control=float(arr[8]),
            temporal=float(arr[9]),
            novelty=float(arr[10]),
            precipitation=float(arr[11]),
        )

    def start_journey(self, task_description: str, execution_id: str | None = None) -> str | None:
        """Create a UniverseJourney at execution start.

        Parameters
        ----------
        task_description : str
            Human-readable description of the task.
        execution_id : str, optional
            Unique execution identifier. Auto-generated if not provided.

        Returns
        -------
        str or None
            Journey ID if created, None if engine unavailable.
        """
        if self._engine is None:
            return None

        try:
            from cohezion.universe.engine import (
                AxiomaticState,
                LatentState,
                UniverseJourney,
            )

            journey_id = execution_id or f"journey_{uuid4().hex[:12]}"

            journey = UniverseJourney(
                id=journey_id,
                agent_name=self._agent_name,
                intent=task_description,
                initial_axiomatic=AxiomaticState(),  # HIHO defaults
                initial_latent=LatentState(
                    embedding=[0.5] * 2048,
                    semantic_intent=task_description[:200],
                ),
            )

            self._active_journeys[journey_id] = journey
            logger.debug("Started universe journey: %s", journey_id)
            return journey_id

        except Exception as e:
            logger.debug("Failed to start universe journey (non-blocking): %s", e)
            return None

    def add_point(
        self,
        journey_id: str,
        trajectory_point: Any,
        step_number: int = 0,
        action: str = "",
    ) -> bool:
        """Add a trajectory point to an active journey.

        Converts JourneyTracker's TrajectoryPoint dimensions (12D vector)
        into AxiomaticState organized by fabric.

        Parameters
        ----------
        journey_id : str
            Active journey identifier.
        trajectory_point : TrajectoryPoint
            Point from JourneyTracker with 12D dimensions.
        step_number : int
            Step index in the execution.
        action : str
            Description of the action taken.

        Returns
        -------
        bool
            True if point was added successfully.
        """
        if self._engine is None or journey_id not in self._active_journeys:
            return False

        try:
            from cohezion.universe.engine import LatentState
            from cohezion.universe.engine import (
                TrajectoryPoint as UniverseTrajectoryPoint,
            )

            journey = self._active_journeys[journey_id]
            axiomatic = self._vector_to_axiomatic(trajectory_point.dimensions)

            universe_point = UniverseTrajectoryPoint(
                step_number=step_number,
                timestamp=trajectory_point.timestamp,
                axiomatic=axiomatic,
                latent=LatentState(
                    embedding=[0.5] * 2048,
                    semantic_intent=trajectory_point.task_description[:200],
                    confidence=trajectory_point.coherence,
                ),
                coherence=trajectory_point.coherence,
                action_taken=action or trajectory_point.operation_type,
            )

            journey.add_trajectory_point(universe_point)
            logger.debug(
                "Added point to journey %s (step=%d, coherence=%.2f)",
                journey_id,
                step_number,
                trajectory_point.coherence,
            )
            return True

        except Exception as e:
            logger.debug("Failed to add journey point (non-blocking): %s", e)
            return False

    def complete_journey(
        self,
        journey_id: str,
        success: bool,
        phi_score: float = 0.0,
        output: str = "",
    ) -> Any | None:
        """Finalize a universe journey with results.

        Parameters
        ----------
        journey_id : str
            Active journey identifier.
        success : bool
            Whether the execution succeeded.
        phi_score : float
            Trajectory quality score.
        output : str
            Execution output (precipitation).

        Returns
        -------
        UniverseJourney or None
            Completed journey if successful.
        """
        if self._engine is None or journey_id not in self._active_journeys:
            return None

        try:
            journey = self._active_journeys.pop(journey_id)

            precipitation = {
                "success": success,
                "output_preview": output[:500] if output else "",
                "type": "code" if success else "error",
            }

            journey.complete(precipitation, phi_score)

            if success:
                journey.status = "completed"
            else:
                journey.status = "failed"

            logger.debug(
                "Completed journey %s (status=%s, phi=%.2f)",
                journey_id,
                journey.status,
                phi_score,
            )
            return journey

        except Exception as e:
            logger.debug("Failed to complete journey (non-blocking): %s", e)
            return None
