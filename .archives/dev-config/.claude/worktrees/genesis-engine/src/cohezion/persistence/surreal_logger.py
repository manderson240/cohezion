import datetime
import logging

from surrealdb import AsyncSurreal

from cohezion.universe.triune_manifold import TriuneState


logger = logging.getLogger(__name__)


class SurrealTrajectoryLogger:
    """
    Asynchronous logger for persisting triune manifold trajectories to SurrealDB 3.0.
    """

    def __init__(
        self,
        url: str = "ws://localhost:8000/rpc",
        namespace: str = "cohezion",
        database: str = "core",
    ):
        """
        Initializes the SurrealDB logger configuration.

        Args:
            url: The connection URL for SurrealDB.
            namespace: The SurrealDB namespace.
            database: The SurrealDB database name.
        """
        self.url = url
        self.namespace = namespace
        self.database = database

    async def log_trajectory(
        self, trajectory_id: str, state: TriuneState, coherence: float
    ) -> None:
        """
        Persists a single trajectory point to SurrealDB.

        Args:
            trajectory_id: Unique identifier for the current journey/trajectory.
            state: The TriuneState object containing manifold vectors.
            coherence: The calculated coherence score for this state.

        Raises:
            Exception: If database insertion fails.
        """
        data = {
            "trajectory_id": trajectory_id,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "coherence": coherence,
            "doer": state.doer.tolist(),
            "thinker": state.thinker.tolist(),
            "knower": state.knower.tolist(),
        }

        async with AsyncSurreal(self.url) as db:
            try:
                await db.use(self.namespace, self.database)

                import os

                user = os.getenv("SURREAL_USER", "root")
                password = os.getenv("SURREAL_PASS", "root")
                await db.signin({"user": user, "pass": password})

                await db.create("trajectory", data)
                logger.debug(
                    f"Successfully persisted trajectory point {trajectory_id} to SurrealDB."
                )
            except Exception as e:
                logger.error(f"Failed to persist trajectory to SurrealDB: {e}")
                raise
