"""SurrealDB 3.0 client for Cohezion EVO semantic state and trajectory graph persistence.

Uses the HTTP SQL endpoint (POST /sql) with Basic auth.
Namespace: cohezion, Database: main (matches the running surreal process).
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Callable, cast

from pydantic import BaseModel

from cohezion.data_mesh.universe_telemetry import UniverseStateEvent


logger = logging.getLogger(__name__)

_HTTP_ENDPOINT = "http://127.0.0.1:8001/sql"
_AUTH_HEADER = "Basic " + base64.b64encode(b"root:root").decode()
_NS_HEADERS = {
    "Authorization": _AUTH_HEADER,
    "Content-Type": "application/json",  # SurrealDB /sql accepts raw SurrealQL with this CT
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Accept": "application/json",
}

_PROBE_QUERY = b"RETURN true;"  # minimal valid SurrealQL, avoids SELECT 1 parse error


class TrajectoryNode(BaseModel):
    """A single node in an EVO's semantic trajectory."""

    evo_id: str
    dimension_state: list[float]  # 12D down-projected state
    coherence: float
    timestamp: str


class SurrealDBClient:
    """Async HTTP client for SurrealDB 3.0 persistence.

    Uses POST /sql with Basic auth — no persistent connection required.
    Falls back to no-op logging if httpx is unavailable.
    """

    def __init__(self, endpoint: str = _HTTP_ENDPOINT) -> None:
        self.endpoint = endpoint
        self.connected = False
        self._active_journey_id: str | None = None

    async def connect(self) -> None:
        """Probe SurrealDB and mark as connected if reachable."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
                    self.endpoint,
                    headers=_NS_HEADERS,
                    content=_PROBE_QUERY,
                )
                if resp.status_code == 200:
                    self.connected = True
                    logger.info("SurrealDB connected at %s", self.endpoint)
                    return
                logger.warning(
                    "SurrealDB probe returned HTTP %d: %.120s", resp.status_code, resp.text
                )
        except Exception as e:
            logger.warning("SurrealDB probe failed: %s — inserts will be no-ops", e)
        self.connected = False

    async def _sql(self, query: str) -> list[Any]:
        """Execute a SurrealQL statement. Returns parsed result list."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.endpoint,
                    headers=_NS_HEADERS,
                    content=query,
                )
                resp.raise_for_status()
                return cast(list[Any], resp.json())
        except Exception as e:
            logger.debug("SurrealDB SQL error: %s | query: %.120s", e, query)
            return []

    async def ensure_journey(self, journey_id: str, agent_id: str, intent: str = "") -> str:
        """Create or update an agent_journey record. Returns the SurrealDB record ID.

        journey_point records require a reference to agent_journey (FK). This
        method uses UPSERT to be idempotent — safe to call multiple times per run.
        """
        safe_journey = journey_id.replace(":", "_").replace(" ", "_")[:64]
        safe_agent = agent_id.replace("'", "").replace('"', "")[:64]
        safe_intent = intent.replace("'", "").replace('"', "")[:120]
        record_id = f"agent_journey:`{safe_journey}`"

        # UPSERT with all required SCHEMAFULL fields
        q = (
            f"UPSERT agent_journey:`{safe_journey}` CONTENT {{"
            f"  journey_id: '{safe_journey}',"
            f"  agent_id: '{safe_agent}',"
            f"  agent_name: '{safe_agent}',"
            f"  intent: '{safe_intent}',"
            f"  status: 'active',"
            f"  started_at: time::now(),"
            f"  transaction_time: time::now(),"
            f"  valid_from: time::now(),"
            f"  total_steps: 0,"
            f"  total_duration_ms: 0.0,"
            f"  final_coherence: 0.5,"
            f"  final_phi_score: 0.5,"
            f"  coherence_trajectory: [],"
            f"  efficiency_trajectory: [],"
            f"  physics_state: {{x:0.0,y:0.0,z:0.0,time:0.0,"
            f"    physics:0.5,biology:0.5,logic:0.5,quantum:0.5,"
            f"    field:0.5,control:0.5,novelty:0.5,precipitation:0.5}},"
            f"  metadata: {{}}"
            f"}};"
        )
        result = await self._sql(q)
        if result and result[0].get("status") == "ERR":
            logger.warning("ensure_journey upsert error: %s", result[0].get("result", "?")[:200])
        self._active_journey_id = record_id
        logger.debug("Journey ensured: %s", record_id)
        return record_id

    async def insert_trajectory_node(self, node: TrajectoryNode) -> str:
        """Insert an EVO trajectory as a journey_point record."""
        if not self.connected:
            logger.debug("SurrealDB not connected — skipping insert for %s", node.evo_id)
            return f"noop:{node.evo_id}"

        journey_ref = self._active_journey_id or "agent_journey:default"
        safe_id = node.evo_id.replace(":", "_").replace(" ", "_")[:60]
        ts = node.timestamp.replace(" ", "T")

        # Map 12D dimension_state to physics_state object fields
        ds = node.dimension_state
        p: Callable[[int], float] = lambda i: float(ds[i]) if i < len(ds) else 0.5

        physics = {
            "x": p(0),
            "y": p(1),
            "z": p(2),
            "time": p(3),
            "physics": p(4),
            "biology": p(5),
            "logic": p(6),
            "quantum": p(7),
            "field": p(8),
            "control": p(9),
            "novelty": p(10),
            "precipitation": p(11),
        }

        q = (
            f"CREATE journey_point SET "
            f"journey = {journey_ref}, "
            f"agent_id = '{safe_id}', "
            f"timestamp = time::now(), "
            f"phase = 'execution', "
            f"coherence = {max(0.0, min(1.0, node.coherence))}, "
            f"efficiency = {max(0.0, min(1.0, node.coherence))}, "
            f"physics_state = {json.dumps(physics)}, "
            f"action = 'evo_deliberation', "
            f"duration_ms = 0.0, "
            f"skill_used = 'quadrature_nexus', "
            f"metadata = {{}};"
        )
        await self._sql(q)
        record_id = f"journey_point:{safe_id}_{ts[:10]}"
        logger.debug("Persisted journey_point %s (coherence=%.3f)", record_id, node.coherence)
        return record_id

    async def insert_flume_journey_event(self, event: object) -> str:
        """Insert a FlumeJourneyEvent into journey_point with full metadata.

        Used by JourneyWorker to persist EVO deliberation events including
        256D z_vector, EVO biography, and voice scores.
        """
        if not self.connected:
            return "noop"

        from cohezion.data_mesh.journey_telemetry import FlumeJourneyEvent

        if not isinstance(event, FlumeJourneyEvent):
            return "noop:wrong_type"

        journey_ref = self._active_journey_id or "agent_journey:default"
        safe_id = event.journey_id.replace(":", "_").replace(" ", "_")[:60]

        ds = event.state_12d
        p: Callable[[int], float] = lambda i: float(ds[i]) if i < len(ds) else 0.5
        physics = {
            "x": p(0),
            "y": p(1),
            "z": p(2),
            "time": p(3),
            "physics": p(4),
            "biology": p(5),
            "logic": p(6),
            "quantum": p(7),
            "field": p(8),
            "control": p(9),
            "novelty": p(10),
            "precipitation": p(11),
        }

        # Pack rich EVO data into result (option<string>) as compact JSON.
        # metadata stays {} — SCHEMAFULL table blocks arbitrary sub-field names
        # unless FLEXIBLE is declared, and we can't alter the schema safely here.
        bio = event.metadata.get("evo_biography") or {}
        voice_scores = event.metadata.get("voice_scores") or {}
        result_payload = json.dumps(
            {
                "event_id": event.event_id,
                "z_norm": round(sum(v * v for v in event.z_vector) ** 0.5, 4),
                "awareness": round(event.awareness_parameter, 4),
                "consensus": event.metadata.get("consensus_score", 0.0),
                "approved": event.metadata.get("approved", False),
                "voice_scores": voice_scores,
                "evo_coherence": bio.get("evo_coherence_metric", 0.0),
                "evo_marks": len(bio.get("witness_marks", [])),
                "evo_ticks": bio.get("lifetime_ticks", 0),
                "binding_energy": bio.get("binding_energy", 0.0),
            },
            separators=(",", ":"),
        ).replace("'", "\\'")

        q = (
            f"CREATE journey_point SET "
            f"journey = {journey_ref}, "
            f"agent_id = '{safe_id}', "
            f"timestamp = time::now(), "
            f"phase = 'execution', "
            f"coherence = {max(0.0, min(1.0, event.coherence))}, "
            f"efficiency = {max(0.0, min(1.0, event.awareness_parameter))}, "
            f"physics_state = {json.dumps(physics)}, "
            f"action = '{safe_id[:80]}', "
            f"model_used = '{event.hardware_tier.value}:{event.expert_stream.value}', "
            f"duration_ms = {event.latency_ms}, "
            f"result = '{result_payload}', "
            f"skill_used = 'quadrature_nexus', "
            f"metadata = {{}};"
        )
        await self._sql(q)
        logger.info(
            "Persisted FlumeJourneyEvent journey_point for %s (coherence=%.3f)",
            event.journey_id,
            event.coherence,
        )
        return f"journey_point:{safe_id}"

    async def insert_universe_state(self, event: UniverseStateEvent) -> str:
        """Insert a universe state shift event."""
        if not self.connected:
            return f"noop:universe_state:{getattr(event, 'universe_id', 'unknown')}"

        safe_id = getattr(event, "universe_id", "unknown")[:60].replace(":", "_")
        journey_ref = self._active_journey_id or "agent_journey:default"

        ds = getattr(event, "state_12d", [0.5] * 12)
        p: Callable[[int], float] = lambda i: float(ds[i]) if i < len(ds) else 0.5
        physics = {
            "x": p(0),
            "y": p(1),
            "z": p(2),
            "time": p(3),
            "physics": p(4),
            "biology": p(5),
            "logic": p(6),
            "quantum": p(7),
            "field": p(8),
            "control": p(9),
            "novelty": p(10),
            "precipitation": p(11),
        }

        q = (
            f"CREATE journey_point SET "
            f"journey = {journey_ref}, "
            f"agent_id = '{safe_id}', "
            f"timestamp = time::now(), "
            f"phase = 'execution', "
            f"coherence = {max(0.0, min(1.0, getattr(event, 'coherence', 0.5)))}, "
            f"efficiency = 0.5, "
            f"physics_state = {json.dumps(physics)}, "
            f"action = 'universe_state', "
            f"duration_ms = 0.0, "
            f"skill_used = 'universe_engine', "
            f"metadata = {json.dumps({'stability_shift': getattr(event, 'stability_shift', 0.0)})};"
        )
        await self._sql(q)
        return f"journey_point:universe_{safe_id}"

    async def query_holographic_record(self, journey_id: str) -> dict[str, Any]:
        """Query journey_point records for a given journey_id."""
        if not self.connected:
            return {"journey": [], "universe_shifts": [], "correlations": []}

        safe_id = journey_id.replace(":", "_").replace(" ", "_")[:64]
        result = await self._sql(
            f"SELECT * FROM journey_point WHERE agent_id = '{safe_id}' LIMIT 100;"
        )
        rows = result[0].get("result", []) if result else []
        return {"journey": rows, "universe_shifts": [], "correlations": []}

    async def query_evo_trajectory(self, evo_id: str) -> list[Any]:
        """Query journey_point records for an EVO by agent_id prefix."""
        if not self.connected:
            return []
        safe_id = evo_id.replace(":", "_").replace(" ", "_")[:64]
        # Use string::starts_with for prefix matching (avoids ~ fuzzy match issues)
        result = await self._sql(
            f"SELECT agent_id, coherence, efficiency, physics_state, metadata "
            f"FROM journey_point WHERE string::starts_with(agent_id, '{safe_id}') LIMIT 500;"
        )
        return result[0].get("result", []) if result else []
