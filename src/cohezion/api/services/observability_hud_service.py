"""Cohezion Real-Time Observability & Topological HUD Web Server.

Provides a standalone FastAPI and WebSocket service serving live telemetry:
1. `/api/telemetry/live`: Instant snapshot of memory headroom, Poincaré geodesics, Sheaf H0/H1, and HIHO carrier.
2. `/api/mcp/tools`: Live catalog of available MCP AGI tools.
3. `/api/sheaf/evaluate`: On-demand Čech cohomology consistency evaluation across agent state vectors.
4. `/api/sandbox/execute`: Pre-flight static AST verification + resource-bounded isolated execution.
5. `/ws/telemetry`: Continuous 1 Hz streaming of swarm geometry and audio field metrics.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cohezion.flume.observability_hud import CohezionObservabilityHUD
from cohezion.governance.sheaf_consistency_gate import SheafConsistencyGate
from cohezion.mcp.cohezion_agi_server import list_tools
from cohezion.security.micro_sandbox import MicroSandboxEngine

logger = logging.getLogger("cohezion_hud_server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Cohezion Real-Time Observability & Topological HUD Server",
    version="2.0.0",
    description="Live telemetry, Čech cohomology gating, Poincaré manifold projections, and sandboxed execution API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_hud = CohezionObservabilityHUD()
_sheaf_gate = SheafConsistencyGate(tolerance=0.15)
_sandbox = MicroSandboxEngine(timeout_sec=3.0)


class SheafEvaluationRequest(BaseModel):
    agent_claims: dict[str, list[float]] = Field(..., description="Map of agent IDs to 12D state vectors")


class SandboxExecuteRequest(BaseModel):
    code: str = Field(..., description="Python action code to execute in isolated sandbox")


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "HEALTHY", "service": "cohezion-topological-hud", "timestamp": time.time()}


@app.get("/api/telemetry/live")
async def get_live_telemetry() -> dict[str, Any]:
    """Get current snapshot of memory, geometry, sheaf cohomology, and audio."""
    return await asyncio.to_thread(_hud.capture_live_telemetry_snapshot)


@app.get("/api/mcp/tools")
async def get_mcp_tools() -> list[dict[str, Any]]:
    """Return catalog of available AGI MCP tools."""
    tools = await list_tools()
    return [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools]


@app.post("/api/sheaf/evaluate")
async def evaluate_sheaf_consistency(req: SheafEvaluationRequest) -> dict[str, Any]:
    """Evaluate Čech cohomology over multi-agent claims."""
    import itertools
    import numpy as np

    keys = list(req.agent_claims.keys())
    intersections = list(itertools.combinations(keys, 2)) if len(keys) > 1 else []
    claims = {k: np.array(v) for k, v in req.agent_claims.items()}
    rep = await asyncio.to_thread(_sheaf_gate.evaluate_consistency, claims, intersections)
    return {
        "is_consistent": rep.is_consistent,
        "dim_h0_consensus": rep.dim_h0_consensus,
        "dim_h1_obstructions": rep.dim_h1_obstructions,
        "max_coboundary_residual": round(rep.max_coboundary_residual, 4),
        "conflicting_pairs": rep.conflicting_pairs,
    }


@app.post("/api/sandbox/execute")
async def execute_sandboxed_code(req: SandboxExecuteRequest) -> dict[str, Any]:
    """Execute Python code in isolated, resource-bounded micro-sandbox."""
    res = await asyncio.to_thread(_sandbox.execute_sandboxed_action, req.code)
    return {
        "passed": res.passed,
        "output": res.output,
        "execution_time_ms": res.execution_time_ms,
        "static_ast_verified": res.static_ast_verified,
        "sanitized": res.sanitized,
    }


@app.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """Stream live telemetry updates at 1 Hz over WebSocket."""
    await websocket.accept()
    try:
        while True:
            snapshot = await asyncio.to_thread(_hud.capture_live_telemetry_snapshot)
            await websocket.send_json(snapshot)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from telemetry stream")
    except Exception as exc:
        logger.error("Error in telemetry WebSocket stream: %s", exc)
