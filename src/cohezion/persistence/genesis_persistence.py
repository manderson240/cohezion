"""Genesis Engine persistence — write journey transitions to SurrealDB.

Stores (state, action, next_state, reward) tuples with enriched physics
data (spinor Bloch vector, fiber base, gauge curvature) for world model
training and retrospective analysis.

SurrealDB connection: ws://localhost:8001 (cohezion namespace, genesis database).

Design principle: ALL artifacts persisted. Nothing is ephemeral.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

import numpy as np


logger = logging.getLogger(__name__)

# SurrealDB connection config
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "genesis"
SURREAL_USER = "root"
SURREAL_PASS = "root"


async def _execute_surql(query: str) -> list[dict] | None:
    """Execute SurrealQL via HTTP API (async-safe with httpx fallback to urllib)."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SURREAL_URL,
                content=query,
                headers={
                    "Accept": "application/json",
                    "surreal-ns": SURREAL_NS,
                    "surreal-db": SURREAL_DB,
                },
                auth=(SURREAL_USER, SURREAL_PASS),
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
    except ImportError:
        # Fallback to synchronous urllib
        import urllib.request

        req = urllib.request.Request(
            SURREAL_URL,
            data=query.encode(),
            headers={
                "Accept": "application/json",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
                "Content-Type": "application/json",
            },
        )
        # Add basic auth
        import base64

        credentials = base64.b64encode(f"{SURREAL_USER}:{SURREAL_PASS}".encode()).decode()
        req.add_header("Authorization", f"Basic {credentials}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.debug("SurrealDB fallback failed: %s", e)
    except Exception as e:
        logger.debug("SurrealDB write failed: %s", e)
    return None


def _to_surql_value(v: Any) -> str:
    """Convert a Python value to SurrealQL literal."""
    if v is None:
        return "NONE"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        if not np.isfinite(v):
            return "0.0"
        return str(v)
    if isinstance(v, str):
        return f"'{v.replace(chr(39), chr(39) + chr(39))}'"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_to_surql_value(x) for x in v) + "]"
    if isinstance(v, np.ndarray):
        return _to_surql_value(v.tolist())
    if isinstance(v, dict):
        return json.dumps(v)
    return str(v)


async def persist_journey_transition(
    journey_id: str,
    step: int,
    state_12d: np.ndarray,
    next_state_12d: np.ndarray,
    reward: float,
    spinor_bloch: np.ndarray | None = None,
) -> bool:
    """Persist a single (state, action, next_state, reward) transition."""
    step_id = f"{journey_id}_{step}_{uuid4().hex[:8]}"

    bloch = spinor_bloch.tolist() if spinor_bloch is not None else [0.0, 0.0, 0.0]

    query = (
        f"CREATE journey_transitions SET "
        f"step_id = {_to_surql_value(step_id)}, "
        f"journey_id = {_to_surql_value(journey_id)}, "
        f"t = {step}, "
        f"state_12d = {_to_surql_value(state_12d)}, "
        f"next_state_12d = {_to_surql_value(next_state_12d)}, "
        f"reward = {_to_surql_value(reward)}, "
        f"spinor_bloch = {_to_surql_value(bloch)};"
    )

    result = await _execute_surql(query)
    if result:
        logger.debug("Persisted transition: %s step %d", journey_id, step)
        return True
    return False


async def persist_universe_snapshot(
    tick: int,
    global_coherence: float,
    symmetry_group: str,
    temperature: float,
    n_agents: int,
) -> bool:
    """Persist a periodic universe state snapshot."""
    snapshot_id = f"snap_{tick}_{uuid4().hex[:8]}"

    query = (
        f"CREATE universe_snapshots SET "
        f"snapshot_id = {_to_surql_value(snapshot_id)}, "
        f"tick = {tick}, "
        f"global_coherence = {_to_surql_value(global_coherence)}, "
        f"symmetry_group = {_to_surql_value(symmetry_group)}, "
        f"temperature = {_to_surql_value(temperature)}, "
        f"n_agents = {n_agents};"
    )

    result = await _execute_surql(query)
    return result is not None


async def persist_prompt_artifact(
    prompt_text: str,
    response_text: str,
    model_id: str,
    token_count_prompt: int = 0,
    token_count_completion: int = 0,
    latency_ms: float = 0.0,
    confidence: float = 0.5,
) -> bool:
    """Persist a prompt/response pair."""
    artifact_id = f"prompt_{uuid4().hex[:12]}"

    query = (
        f"CREATE prompt_artifacts SET "
        f"artifact_id = {_to_surql_value(artifact_id)}, "
        f"prompt_text = {_to_surql_value(prompt_text[:5000])}, "
        f"response_text = {_to_surql_value(response_text[:5000])}, "
        f"model_id = {_to_surql_value(model_id)}, "
        f"token_count_prompt = {token_count_prompt}, "
        f"token_count_completion = {token_count_completion}, "
        f"latency_ms = {_to_surql_value(latency_ms)}, "
        f"confidence = {_to_surql_value(confidence)};"
    )

    result = await _execute_surql(query)
    return result is not None


async def get_journey_transitions(journey_id: str | None = None, limit: int = 100) -> list[dict]:
    """Query stored journey transitions."""
    if journey_id:
        query = f"SELECT * FROM journey_transitions WHERE journey_id = {_to_surql_value(journey_id)} LIMIT {limit};"
    else:
        query = f"SELECT * FROM journey_transitions ORDER BY timestamp DESC LIMIT {limit};"

    result = await _execute_surql(query)
    if result and isinstance(result, list):
        for r in result:
            if r.get("status") == "OK" and isinstance(r.get("result"), list):
                return r["result"]
    return []


async def get_transition_count() -> int:
    """Count total stored transitions."""
    result = await _execute_surql("SELECT count() FROM journey_transitions GROUP ALL;")
    if result and isinstance(result, list):
        for r in result:
            if r.get("status") == "OK" and isinstance(r.get("result"), list):
                rows = r["result"]
                if rows:
                    return rows[0].get("count", 0)
    return 0


__all__ = [
    "get_journey_transitions",
    "get_transition_count",
    "persist_journey_transition",
    "persist_prompt_artifact",
    "persist_universe_snapshot",
]
