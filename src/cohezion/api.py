# ruff: noqa: S311  # random used for simulation/jitter, not cryptography
"""FastAPI backend for COHEZION.

Serves the Three.js + WASM frontend with:
- GET  /universe/nodes  -- 12D node data for HologramField visualization
- GET  /wallet          -- Ascension credit balance for WalletWidget
- WS   /pulse           -- Streaming 12D state vectors for useOuroboros
- POST /simulate/step   -- Advance simulation one step
- GET  /health          -- System vitals from ResourceMonitor
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.reliability import get_circuit
from cohezion.reliability.monitor import get_resource_monitor


logger = logging.getLogger(__name__)

# Allowed CORS origins from environment, default to localhost only
_CORS_ORIGINS = os.environ.get(
    "COHEZION_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
).split(",")

# ---------------------------------------------------------------------------
# Globals initialised during lifespan
# ---------------------------------------------------------------------------
_db: SurrealClient | None = None
_simulation_tick: int = 0


async def _get_db() -> SurrealClient:
    """Return the shared SurrealClient, connecting lazily if needed."""
    global _db
    if _db is None:
        _db = SurrealClient()
    if not _db._connected:
        await _db.connect()
    return _db


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def _lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _db
    logger.info("COHEZION API starting up")
    _db = SurrealClient()
    await _db.connect()
    yield
    if _db is not None:
        await _db.close()
    logger.info("COHEZION API shut down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="COHEZION API",
    description="12D Universe Simulation Backend",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Agent-Token"],
)


# ---------------------------------------------------------------------------
# Synthetic fallback data (used when SurrealDB is unreachable)
# ---------------------------------------------------------------------------
def _synthetic_nodes(count: int) -> list[dict[str, Any]]:
    """Generate synthetic universe nodes so the frontend always renders."""
    nodes: list[dict[str, Any]] = []
    for i in range(count):
        theta = (i / max(count, 1)) * 2 * math.pi
        r = 3.0 + random.random() * 4.0
        axiomatic = [
            r * math.cos(theta),  # spatial_x
            r * math.sin(theta),  # spatial_y
            (random.random() - 0.5) * 4,  # spatial_z
            time.time(),  # temporal
            0.5 + random.random() * 0.1,  # physics
            0.5 + random.random() * 0.1,  # biology
            0.5 + random.random() * 0.1,  # logic
            0.5 + random.random() * 0.1,  # quantum
            0.5 + random.random() * 0.1,  # field
            0.5 + random.random() * 0.1,  # control
            0.5 + random.random() * 0.1,  # novelty
            random.random() * 0.3,  # precipitation
        ]
        nodes.append(
            {
                "id": f"synth_{i:04d}",
                "position": axiomatic[:3],
                "axiomatic": axiomatic,
                "coherence": 0.5 + random.random() * 0.1,
                "agent_name": f"agent_{i % 5}",
                "intent": "synthetic dream node",
                "node_type": "synthetic",
            }
        )
    return nodes


def _synthetic_wallet() -> dict[str, Any]:
    return {
        "balance": 12_500,
        "history": [
            {
                "timestamp": "2026-02-05T00:00:00Z",
                "amount": 500,
                "reason": "Manifold coherence bonus",
                "agent": "orchestrator",
            },
            {
                "timestamp": "2026-02-04T12:00:00Z",
                "amount": 250,
                "reason": "Simulation step reward",
                "agent": "sim_runner",
            },
        ],
    }


# ---------------------------------------------------------------------------
# GET /universe/nodes
# ---------------------------------------------------------------------------
@app.get("/universe/nodes")
async def get_universe_nodes(
    limit: int = Query(default=100, ge=1, le=100_000),
) -> dict[str, Any]:
    """Return universe nodes for the HologramField visualisation.

    Each node carries its 12D axiomatic state vector plus spatial position.
    Falls back to synthetic data when the database is unavailable.
    """
    breaker = get_circuit("surrealdb")
    if not breaker.allow_request():
        return {"nodes": _synthetic_nodes(min(limit, 200)), "source": "synthetic"}

    try:
        db = await _get_db()
        raw_nodes = await db.get_all_nodes(limit=limit)
        breaker.record_success()

        nodes: list[dict[str, Any]] = []
        for n in raw_nodes:
            ps = n.physics_state
            axiomatic = [
                ps.x,
                ps.y,
                ps.z,
                ps.time,
                ps.physics,
                ps.biology,
                ps.logic,
                ps.quantum,
                ps.field,
                ps.control,
                ps.novelty,
                ps.precipitation,
            ]
            nodes.append(
                {
                    "id": n.id,
                    "position": [ps.x, ps.y, ps.z],
                    "axiomatic": axiomatic,
                    "coherence": (ps.control + ps.precipitation) / 2.0,
                    "agent_name": n.metadata.get("agent_name", "unknown"),
                    "intent": n.metadata.get("intent", n.content[:80] if n.content else ""),
                    "node_type": n.node_type,
                }
            )

        if not nodes:
            return {"nodes": _synthetic_nodes(min(limit, 200)), "source": "synthetic"}

        return {"nodes": nodes, "source": "surrealdb"}

    except Exception as exc:
        breaker.record_failure()
        logger.warning("get_universe_nodes falling back to synthetic: %s", exc)
        return {"nodes": _synthetic_nodes(min(limit, 200)), "source": "synthetic"}


# ---------------------------------------------------------------------------
# GET /wallet
# ---------------------------------------------------------------------------
@app.get("/wallet")
async def get_wallet() -> dict[str, Any]:
    """Return Ascension Credit wallet state for WalletWidget."""
    breaker = get_circuit("surrealdb")
    if not breaker.allow_request():
        return _synthetic_wallet()

    try:
        db = await _get_db()
        results = await db.query("SELECT * FROM wallet ORDER BY created_at DESC LIMIT 1")

        if results and isinstance(results, list):
            # Unpack SurrealDB response
            rows = results[0] if isinstance(results[0], list) else results[0].get("result", [])
            if rows:
                record = rows[0]
                breaker.record_success()
                return {
                    "balance": record.get("balance", 0),
                    "history": record.get("history", []),
                }

        breaker.record_success()
        return _synthetic_wallet()

    except Exception as exc:
        breaker.record_failure()
        logger.warning("get_wallet falling back to synthetic: %s", exc)
        return _synthetic_wallet()


# ---------------------------------------------------------------------------
# WS /pulse
# ---------------------------------------------------------------------------
@app.websocket("/pulse")
async def pulse(ws: WebSocket) -> None:
    """Stream 12D state pulses to the frontend (useOuroboros).

    Sends ``{ type: "pulse", payload: { brane: float[8] } }`` every ~500ms.
    The ``brane`` array maps to the 8 brane dimensions of the 12D manifold:
    [physics, biology, logic, quantum, field, control, novelty, precipitation].
    """
    await ws.accept()
    monitor = get_resource_monitor()

    try:
        while True:
            vitals = monitor.get_vitals()
            dilation = vitals.get("dilation_factor", 1.0)

            # Build brane vector from live telemetry + light noise
            cpu_norm = vitals.get("cpu_percent", 50.0) / 100.0
            mem_norm = vitals.get("memory_percent", 50.0) / 100.0
            vram_norm = vitals.get("vram_percent", 0.0) / 100.0

            brane = [
                1.0 - cpu_norm,  # physics  (system energy)
                0.5 + random.random() * 0.1,  # biology
                0.5 + random.random() * 0.1,  # logic
                0.5 + random.random() * 0.1,  # quantum
                vram_norm if vram_norm > 0 else 0.3,  # field    (GPU pressure)
                max(0.1, dilation),  # control  (stability)
                0.02 + random.random() * 0.03,  # novelty  (entropy)
                0.5 * (1 - cpu_norm) + 0.5 * (1 - mem_norm),  # precipitation (coherence)
            ]

            await ws.send_json({"type": "pulse", "payload": {"brane": brane}})
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.debug("Pulse client disconnected")
    except Exception as exc:
        logger.warning("Pulse stream error: %s", exc)


# ---------------------------------------------------------------------------
# POST /simulate/step
# ---------------------------------------------------------------------------
@app.post("/simulate/step")
async def simulate_step() -> dict[str, Any]:
    """Advance the universe simulation by one tick.

    Uses the lightweight axiomatic evolution (no Rust/FLUME dependency) so
    the endpoint works even when optional native extensions are absent.
    """
    global _simulation_tick
    _simulation_tick += 1

    # Evolve a simple axiomatic state locally
    t = time.time()
    axiomatic = [
        math.sin(t * 0.1) * 5,  # spatial_x
        math.cos(t * 0.1) * 5,  # spatial_y
        math.sin(t * 0.05) * 2,  # spatial_z
        t,  # temporal
        0.5 + 0.1 * math.sin(t),  # physics
        0.5 + 0.1 * math.cos(t),  # biology
        0.5,  # logic
        0.5 + 0.05 * math.sin(t * 2),  # quantum
        0.5,  # field
        0.5,  # control
        0.5 + 0.05 * math.cos(t * 3),  # novelty
        max(0.0, 0.3 * math.sin(t * 0.5)),  # precipitation
    ]

    coherence = 1.0 - min(sum((d - 0.5) ** 2 for d in axiomatic[4:11]) / 7.0 * 4, 1.0)

    return {
        "tick": _simulation_tick,
        "axiomatic": axiomatic,
        "coherence": round(coherence, 4),
        "timestamp": t,
    }


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, Any]:
    """System health: ResourceMonitor vitals + circuit breaker states."""
    monitor = get_resource_monitor()
    vitals = monitor.get_vitals()

    surreal_circuit = get_circuit("surrealdb")

    return {
        "status": "ok",
        "vitals": {
            "cpu_percent": vitals.get("cpu_percent", 0),
            "memory_percent": vitals.get("memory_percent", 0),
            "memory_available_gb": round(vitals.get("memory_available_gb", 0), 2),
            "vram_percent": round(vitals.get("vram_percent", 0), 1),
            "active_llm_calls": vitals.get("active_llm_calls", 0),
            "dilation_factor": vitals.get("dilation_factor", 1.0),
            "active_sandboxes": vitals.get("active_sandboxes", 0),
            "sandbox_memory_mb": vitals.get("sandbox_memory_mb", 0),
        },
        "circuits": {
            "surrealdb": surreal_circuit.get_stats(),
        },
        "simulation_tick": _simulation_tick,
    }
