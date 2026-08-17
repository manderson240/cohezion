"""Cohezion AGI Premier MCP Server.

Exposes Cohezion's bleeding-edge AGI capabilities directly over Anthropic's Model Context Protocol (MCP):
1. `cohezion.autoharness_verify`: 0.00 ms AST static verification of Python actions/code without LLM calls.
2. `cohezion.poincare_project`: Project high-dimensional vectors to 12D/256D/2048D Poincaré hyperbolic manifolds.
3. `cohezion.sheaf_cohomology_gate`: Check multi-agent claim consistency (dim H^0 consensus, dim H^1 obstruction).
4. `cohezion.hiho_sonify`: Real-time 432 Hz acoustic thermodynamic loss frequency & dissonance computation.
5. `cohezion.bioelectric_self_heal`: FitzHugh-Nagumo bioelectric swarm state recovery and light-cone calculation.
6. `cohezion.provenance_sign`: Sign agent execution payloads with cryptographic HMAC-SHA256.
"""

from __future__ import annotations

import asyncio
import ast
import json
import logging
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

# Add src to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mcp.server import Server
from mcp.types import TextContent, Tool

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.flume.bioelectric_swarm import BioelectricSwarm
from cohezion.flume.poincare_manifold_visualizer import PoincareManifoldVisualizer, compute_hyperbolic_distance
from cohezion.governance.sheaf_consistency_gate import SheafConsistencyGate
from cohezion.physics.hiho_sonification import HIHOSonifier
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.security.data_provenance_signer import DataProvenanceSigner

logger = logging.getLogger("cohezion_mcp_server")
logging.basicConfig(level=logging.INFO)

app = Server("cohezion-agi-server")

_verifier = AutoHarnessVerifier()
_sheaf_gate = SheafConsistencyGate(tolerance=0.15)
_sonifier = HIHOSonifier()
_poincare_viz = PoincareManifoldVisualizer()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Cohezion AGI MCP tools."""
    return [
        Tool(
            name="cohezion_autoharness_verify",
            description="Verify Python code actions deterministically in 0.00ms via AST bytecode compilation (bypasses LLM token cost).",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code snippet or action to verify"},
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="cohezion_poincare_project",
            description="Project multi-dimensional state vectors into a 12D/256D Poincaré hyperbolic manifold and compute geodesic distance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vector": {"type": "array", "items": {"type": "number"}, "description": "Input coordinate vector"},
                    "target_dim": {"type": "integer", "default": 256, "description": "Target manifold dimension (12, 256, 2048)"},
                },
                "required": ["vector"],
            },
        ),
        Tool(
            name="cohezion_sheaf_cohomology_gate",
            description="Evaluate Čech Cohomology over multi-agent belief claims to detect obstructions (dim H^1) and compute consensus (dim H^0).",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_claims": {
                        "type": "object",
                        "description": "Dict mapping agent IDs to 12D state vectors",
                    },
                    "shared_intersections": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "Pairs of agent IDs sharing an intersection boundary",
                    },
                },
                "required": ["agent_claims", "shared_intersections"],
            },
        ),
        Tool(
            name="cohezion_hiho_sonify",
            description="Calculate real-time 432 Hz acoustic thermodynamic frequency and harmonic dissonance for a given coherence level.",
            inputSchema={
                "type": "object",
                "properties": {
                    "coherence": {"type": "number", "description": "Coherence value in [0.0, 1.0] (0.5 = max stability)"},
                    "fundamental_hz": {"type": "number", "default": 432.0, "description": "Base carrier frequency in Hz"},
                },
                "required": ["coherence"],
            },
        ),
        Tool(
            name="cohezion_bioelectric_self_heal",
            description="Execute Bioelectric Swarm Morphogenesis, FitzHugh-Nagumo ODE recovery, and light-cone radius expansion.",
            inputSchema={
                "type": "object",
                "properties": {
                    "num_nodes": {"type": "integer", "default": 12, "description": "Number of bioelectric nodes in swarm"},
                    "coupling_strength": {"type": "number", "default": 0.75, "description": "Gap-junction coupling tensor [0.0, 1.0]"},
                    "inject_fault_node": {"type": "integer", "description": "Optional node index to inject fault before self-healing"},
                },
            },
        ),
        Tool(
            name="cohezion_provenance_sign",
            description="Cryptographically sign an agent action or learning payload using HMAC-SHA256.",
            inputSchema={
                "type": "object",
                "properties": {
                    "payload": {"type": "object", "description": "Dictionary of payload data to sign"},
                    "key_id": {"type": "string", "default": "v2", "description": "Key ID identifier for HMAC signing"},
                },
                "required": ["payload"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a Cohezion MCP tool with strict input validation and non-blocking thread execution."""
    t0 = time.perf_counter()

    if name == "cohezion_autoharness_verify":
        code = str(arguments.get("code", ""))[:50000]
        v_res = await asyncio.to_thread(_verifier.verify_code, code)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        result = {
            "valid": v_res.valid,
            "score": v_res.score,
            "latency_ms": round(dt_ms, 3),
            "errors": v_res.errors if hasattr(v_res, "errors") else [],
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "cohezion_poincare_project":
        raw_vec = arguments.get("vector", [])
        if not isinstance(raw_vec, list) or len(raw_vec) == 0:
            return [TextContent(type="text", text=json.dumps({"error": "vector must be non-empty list"}))]
        # Validate finite floats and clamp dimension to valid choices
        vec = [float(np.clip(x, -0.99, 0.99)) for x in raw_vec[:2048] if np.isfinite(x)]
        target_dim = int(arguments.get("target_dim", 256))
        if target_dim not in (12, 16, 26, 32, 256, 2048):
            target_dim = len(vec)

        def _do_poincare():
            # Pad or slice vector to target_dim
            if len(vec) < target_dim:
                padded = vec + [0.0] * (target_dim - len(vec))
            else:
                padded = vec[:target_dim]
            p_pt = PoincareManifoldND.project(tuple(padded), target_dim=target_dim)
            d_p = PoincareManifoldND.distance(PoincareManifoldND.origin(target_dim), p_pt)
            return p_pt, d_p

        p_pt, d_p = await asyncio.to_thread(_do_poincare)
        result = {
            "target_dim": target_dim,
            "norm": round(p_pt.norm, 4),
            "hyperbolic_distance_to_origin": round(d_p, 4),
            "is_valid_poincare_point": p_pt.norm < 1.0,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "cohezion_sheaf_cohomology_gate":
        raw_claims = arguments.get("agent_claims", {})
        claims = {k: np.array([float(np.clip(x, -1.0, 1.0)) for x in v[:12]]) for k, v in list(raw_claims.items())[:64]}
        intersections = [tuple(p) for p in arguments.get("shared_intersections", [])]
        rep = await asyncio.to_thread(_sheaf_gate.evaluate_consistency, claims, intersections)
        result = {
            "is_consistent": rep.is_consistent,
            "dim_h0_consensus": rep.dim_h0_consensus,
            "dim_h1_obstructions": rep.dim_h1_obstructions,
            "max_coboundary_residual": round(rep.max_coboundary_residual, 4),
            "conflicting_pairs": rep.conflicting_pairs,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "cohezion_hiho_sonify":
        raw_c = float(arguments.get("coherence", 0.5))
        c = float(np.clip(raw_c, 0.0, 1.0))
        base_hz = float(np.clip(float(arguments.get("fundamental_hz", 432.0)), 20.0, 20000.0))
        audio_frame = await asyncio.to_thread(_sonifier.sonify_coherence_state, coherence=c, fundamental_hz=base_hz)
        result = {
            "coherence": c,
            "fundamental_hz": round(audio_frame.fundamental_hz, 2),
            "dissonance_index": round(audio_frame.dissonance_index, 4),
            "is_hiho_stable": abs(c - 0.5) <= 0.05,
            "drift_from_hiho": round(abs(c - 0.5), 4),
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "cohezion_bioelectric_self_heal":
        n_nodes = int(np.clip(int(arguments.get("num_nodes", 12)), 2, 256))
        coupling = float(np.clip(float(arguments.get("coupling_strength", 0.75)), 0.0, 1.0))
        
        def _do_swarm():
            swarm = BioelectricSwarm(n_nodes=n_nodes, coupling_strength=coupling)
            r_c = swarm.calculate_light_cone_radius()
            fault_node = arguments.get("inject_fault_node")
            healed_nodes = []
            if fault_node is not None and int(fault_node) in swarm.nodes:
                swarm.nodes[int(fault_node)].inject_fault("oom")
                swarm.heal_swarm()
                healed_nodes = [int(fault_node)]
            return swarm, r_c, healed_nodes

        swarm, r_c, healed_nodes = await asyncio.to_thread(_do_swarm)
        result = {
            "num_nodes": n_nodes,
            "coupling_strength": coupling,
            "light_cone_radius": round(r_c, 2),
            "mean_coupling": round(swarm.mean_coupling(), 4),
            "healed_nodes": healed_nodes,
            "swarm_healthy": all(n.is_healthy for n in swarm.nodes.values()),
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "cohezion_provenance_sign":
        payload = arguments.get("payload", {})
        key_id = arguments.get("key_id", "v2")
        sig = DataProvenanceSigner.sign_sample(payload, key_id=key_id)
        result = {
            "key_id": key_id,
            "hmac_sha256_signature": sig,
            "payload_signed": True,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool '{name}'"}))]


async def main():
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
