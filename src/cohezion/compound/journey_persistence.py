"""SurrealDB journey persistence with JSONL fallback.

Stores full agent FLUME trajectories for experience-driven compound
engineering. Journeys include 12D axiomatic states, coherence scores,
and step outputs at each trajectory point.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_JSONL_DIR = Path("data/compound/journeys")


class JourneyPersistence:
    """Persist agent journeys to SurrealDB or JSONL.

    Parameters
    ----------
    jsonl_dir : Path | None
        Override directory for JSONL fallback files.
    """

    def __init__(self, jsonl_dir: Path | None = None) -> None:
        self._jsonl_dir = jsonl_dir or _JSONL_DIR
        self._surreal_available: bool | None = None

    async def save_journey(
        self,
        journey_data: dict[str, Any],
    ) -> str:
        """Save a completed journey.

        Parameters
        ----------
        journey_data : dict[str, Any]
            Serialized journey (from UniverseJourney.to_dict() + extras).

        Returns
        -------
        str
            Record ID or JSONL reference.
        """
        if await self._check_surreal():
            try:
                return await self._save_to_surreal(journey_data)
            except Exception:
                logger.warning("SurrealDB journey save failed, falling back to JSONL")

        return self._save_to_jsonl(journey_data)

    async def save_trajectory_point(
        self,
        journey_id: str,
        point_data: dict[str, Any],
    ) -> str:
        """Save an individual trajectory point (streaming persistence).

        Parameters
        ----------
        journey_id : str
            Parent journey ID.
        point_data : dict[str, Any]
            Serialized trajectory point.

        Returns
        -------
        str
            Record ID or JSONL reference.
        """
        point_data["journey_id"] = journey_id
        point_data["timestamp"] = point_data.get("timestamp", time.time())

        if await self._check_surreal():
            try:
                return await self._save_point_surreal(point_data)
            except Exception:
                logger.warning("SurrealDB point save failed, falling back to JSONL")

        return self._save_point_jsonl(journey_id, point_data)

    async def load_journeys(
        self,
        agent_name: str | None = None,
        skill_name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Load journey history with optional filters.

        Parameters
        ----------
        agent_name : str | None
            Filter by agent name.
        skill_name : str | None
            Filter by skill (matched against intent field).
        limit : int
            Maximum records to return.

        Returns
        -------
        list[dict[str, Any]]
            Most recent journeys first.
        """
        if await self._check_surreal():
            try:
                return await self._load_from_surreal(agent_name, skill_name, limit)
            except Exception:
                logger.warning("SurrealDB load failed, falling back to JSONL")

        return self._load_from_jsonl(agent_name, skill_name, limit)

    async def load_journey_with_trajectory(
        self, journey_id: str
    ) -> dict[str, Any] | None:
        """Load a single journey with its full trajectory.

        Parameters
        ----------
        journey_id : str
            Journey ID to load.

        Returns
        -------
        dict[str, Any] | None
            Journey with nested trajectory_points, or None.
        """
        if await self._check_surreal():
            try:
                return await self._load_full_surreal(journey_id)
            except Exception:
                logger.warning("SurrealDB full load failed, falling back to JSONL")

        return self._load_full_jsonl(journey_id)

    async def get_experience_guidance(
        self,
        skill_name: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Load past journey summaries to guide future executions.

        Returns condensed experience data: coherence trajectories,
        patterns detected, and phi scores from previous executions
        of the same or similar skills.

        Parameters
        ----------
        skill_name : str
            Skill to find guidance for.
        limit : int
            Number of past journeys to consider.

        Returns
        -------
        list[dict[str, Any]]
            Summaries with coherence_trajectory, patterns, phi_score.
        """
        journeys = await self.load_journeys(skill_name=skill_name, limit=limit)
        guidance = []
        for j in journeys:
            guidance.append(
                {
                    "journey_id": j.get("id", ""),
                    "final_coherence": j.get("final_coherence", 0.0),
                    "phi_score": j.get("final_phi_score", 0.0),
                    "trajectory_count": j.get("trajectory_count", 0),
                    "compound_score_delta": j.get("precipitation", {}).get(
                        "compound_score_delta", 0.0
                    ),
                    "patterns": j.get("patterns", []),
                    "status": j.get("status", "unknown"),
                }
            )
        return guidance

    # --- SurrealDB Methods ---

    async def _check_surreal(self) -> bool:
        """Check SurrealDB availability (cached)."""
        if self._surreal_available is None:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get("http://localhost:8000/health")
                    self._surreal_available = resp.status_code == 200
            except Exception:
                self._surreal_available = False
        return self._surreal_available

    async def _save_to_surreal(self, journey_data: dict[str, Any]) -> str:
        """Save journey to SurrealDB agent_journey table."""
        from cohezion.persistence.surreal_client import get_client

        client = await get_client()
        record = {
            "timestamp": time.time(),
            **journey_data,
        }
        result = await client.create("agent_journey", record)
        record_id = (
            result[0]["id"] if isinstance(result, list) and result else "unknown"
        )
        return str(record_id)

    async def _save_point_surreal(self, point_data: dict[str, Any]) -> str:
        """Save trajectory point to SurrealDB."""
        from cohezion.persistence.surreal_client import get_client

        client = await get_client()
        result = await client.create("trajectory_point", point_data)
        record_id = (
            result[0]["id"] if isinstance(result, list) and result else "unknown"
        )
        return str(record_id)

    async def _load_from_surreal(
        self,
        agent_name: str | None,
        skill_name: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Load from SurrealDB with optional filters."""
        from cohezion.persistence.surreal_client import get_client

        client = await get_client()

        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if agent_name:
            conditions.append("agent_name = $agent_name")
            params["agent_name"] = agent_name
        if skill_name:
            conditions.append("intent CONTAINS $skill_name")
            params["skill_name"] = skill_name

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = (
            f"SELECT * FROM agent_journey{where} ORDER BY timestamp DESC LIMIT $limit"
        )

        result = await client.query(query, params)
        if isinstance(result, list):
            return result[:limit]
        return []

    async def _load_full_surreal(self, journey_id: str) -> dict[str, Any] | None:
        """Load journey + trajectory from SurrealDB."""
        from cohezion.persistence.surreal_client import get_client

        client = await get_client()

        # Load journey
        result = await client.query(
            "SELECT * FROM agent_journey WHERE id = $id",
            {"id": journey_id},
        )
        if not result:
            return None

        journey = result[0] if isinstance(result, list) else result

        # Load trajectory points
        points = await client.query(
            "SELECT * FROM trajectory_point WHERE journey_id = $jid "
            "ORDER BY step_number ASC",
            {"jid": journey_id},
        )
        journey["trajectory_points"] = points if isinstance(points, list) else []
        return journey

    # --- JSONL Fallback Methods ---

    def _save_to_jsonl(self, journey_data: dict[str, Any]) -> str:
        """Save journey to JSONL file."""
        self._jsonl_dir.mkdir(parents=True, exist_ok=True)
        path = self._jsonl_dir / "journeys.jsonl"
        record = {"timestamp": time.time(), **journey_data}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return f"jsonl:journey:{record['timestamp']}"

    def _save_point_jsonl(self, journey_id: str, point_data: dict[str, Any]) -> str:
        """Save trajectory point to JSONL."""
        self._jsonl_dir.mkdir(parents=True, exist_ok=True)
        path = self._jsonl_dir / "trajectory_points.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(point_data, default=str) + "\n")
        return f"jsonl:point:{journey_id}:{point_data.get('step_number', 0)}"

    def _load_from_jsonl(
        self,
        agent_name: str | None,
        skill_name: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Load journeys from JSONL with optional filters."""
        path = self._jsonl_dir / "journeys.jsonl"
        if not path.exists():
            return []

        records = []
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            try:
                record = json.loads(line)
                if agent_name and record.get("agent_name") != agent_name:
                    continue
                if (
                    skill_name
                    and skill_name.lower() not in record.get("intent", "").lower()
                ):
                    continue
                records.append(record)
            except json.JSONDecodeError:
                continue

        records.reverse()  # Most recent first
        return records[:limit]

    def _load_full_jsonl(self, journey_id: str) -> dict[str, Any] | None:
        """Load a single journey + trajectory from JSONL."""
        # Find journey
        path = self._jsonl_dir / "journeys.jsonl"
        if not path.exists():
            return None

        journey = None
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            try:
                record = json.loads(line)
                if record.get("id") == journey_id:
                    journey = record
                    break
            except json.JSONDecodeError:
                continue

        if journey is None:
            return None

        # Find trajectory points
        points_path = self._jsonl_dir / "trajectory_points.jsonl"
        points = []
        if points_path.exists():
            for line in points_path.read_text(encoding="utf-8").strip().splitlines():
                try:
                    point = json.loads(line)
                    if point.get("journey_id") == journey_id:
                        points.append(point)
                except json.JSONDecodeError:
                    continue

        journey["trajectory_points"] = sorted(
            points, key=lambda p: p.get("step_number", 0)
        )
        return journey
