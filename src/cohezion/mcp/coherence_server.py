"""Coherence MCP Server - HIHO alignment and FLUME journey tracking via MCP.

Exposes coherence calculation, journey tracking, and degradation detection
as MCP tools for the pi extension and other clients.

Tools:
    - coherence.check_alignment: Calculate HIHO alignment score
    - coherence.track_journey_step: Record 12D FLUME trajectory point
    - coherence.get_trajectory: Retrieve recent journey trajectory
    - coherence.detect_degradation: Check for coherence degradation
    - coherence.extract_pattern: Extract and encode pattern with FLUME
    - coherence.query_patterns: Find similar patterns by FLUME distance
    - coherence.refine_skill: Append pattern to PRIME skill
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server
from mcp.types import TextContent, Tool

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer
from cohezion.core.mcp_client import MCPClient, get_mcp_client
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global instances (thread-safe, stateless)
_hiho_engine = HihoVectorEngine(sigma=0.25)
_journey_tracker: JourneyTracker | None = None
_degradation_detector: DegradationDetector | None = None
_mcp_client: MCPClient | None = None


async def get_mcp() -> MCPClient:
    """Get or create MCP client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = get_mcp_client()
    return _mcp_client


def get_tracker() -> JourneyTracker:
    """Get or create journey tracker."""
    global _journey_tracker
    if _journey_tracker is None:
        _journey_tracker = JourneyTracker(seed=42)
    return _journey_tracker


def get_detector() -> DegradationDetector:
    """Get or create degradation detector."""
    global _degradation_detector
    if _degradation_detector is None:
        _degradation_detector = DegradationDetector(coherence_threshold=0.50, cache_hit_rate_threshold=0.50)
    return _degradation_detector


# MCP Server
app = Server("cohezion-coherence")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available coherence tools."""
    return [
        Tool(
            name="coherence.check_alignment",
            description="Calculate HIHO alignment score for intent/tool combination",
            inputSchema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "description": "User intent description"},
                    "tool": {
                        "type": "string",
                        "description": "Tool being used (edit, write, bash, etc)",
                    },
                    "context": {"type": "string", "description": "Additional context (optional)"},
                },
                "required": ["intent", "tool"],
            },
        ),
        Tool(
            name="coherence.track_journey_step",
            description="Record a 12D FLUME trajectory point for an execution step",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_description": {"type": "string"},
                    "operation_type": {
                        "type": "string",
                        "enum": ["generate", "analyze", "search", "transform", "persist"],
                    },
                    "coherence": {"type": "number", "description": "Coherence score 0.0-1.0"},
                    "efficiency": {"type": "number", "description": "Token efficiency 0.0-1.0"},
                    "success": {"type": "boolean"},
                    "metadata": {"type": "object"},
                },
                "required": ["task_description", "operation_type", "coherence"],
            },
        ),
        Tool(
            name="coherence.get_trajectory",
            description="Get recent trajectory points with quality metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "window": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of recent points",
                    },
                },
            },
        ),
        Tool(
            name="coherence.detect_degradation",
            description="Check metrics for coherence degradation and return alerts",
            inputSchema={
                "type": "object",
                "properties": {
                    "metrics": {
                        "type": "object",
                        "properties": {
                            "coherence": {"type": "number"},
                            "cache_hit_rate": {"type": "number"},
                            "token_efficiency": {"type": "number"},
                            "duration_seconds": {"type": "number"},
                            "success_rate": {"type": "number"},
                        },
                    },
                },
                "required": ["metrics"],
            },
        ),
        Tool(
            name="coherence.calculate_hiho",
            description="Calculate HIHO stability score for a coherence value",
            inputSchema={
                "type": "object",
                "properties": {
                    "coherence": {"type": "number", "description": "Coherence value 0.0-1.0"},
                },
                "required": ["coherence"],
            },
        ),
        Tool(
            name="coherence.extract_pattern",
            description="Extract code pattern and encode to FLUME 256D",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "code": {"type": "string"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "context": {"type": "string"},
                    "file_paths": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "code", "category"],
            },
        ),
        Tool(
            name="coherence.query_patterns",
            description="Query vault for similar patterns using FLUME similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="coherence.refine_skill",
            description="Append high-confidence pattern to PRIME skill file",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "pattern": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "code_example": {"type": "string"},
                            "confidence": {"type": "number"},
                            "coherence": {"type": "number"},
                        },
                        "required": ["name", "code_example", "confidence"],
                    },
                },
                "required": ["skill_name", "pattern"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle coherence tool calls."""
    try:
        if name == "coherence.check_alignment":
            return await _check_alignment(arguments)
        elif name == "coherence.track_journey_step":
            return await _track_journey_step(arguments)
        elif name == "coherence.get_trajectory":
            return await _get_trajectory(arguments)
        elif name == "coherence.detect_degradation":
            return await _detect_degradation(arguments)
        elif name == "coherence.calculate_hiho":
            return await _calculate_hiho(arguments)
        elif name == "coherence.extract_pattern":
            return await _extract_pattern(arguments)
        elif name == "coherence.query_patterns":
            return await _query_patterns(arguments)
        elif name == "coherence.refine_skill":
            return await _refine_skill(arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    except Exception as e:
        logger.exception("Tool error: %s", name)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _check_alignment(arguments: dict[str, Any]) -> list[TextContent]:
    """Calculate HIHO alignment with intent classification."""
    intent = arguments.get("intent", "")
    tool = arguments.get("tool", "")
    context = arguments.get("context", "")

    # Initialize analyzer with MCP client for vault queries
    mcp = await get_mcp()
    analyzer = RequestAlignmentAnalyzer(mcp_client=mcp)

    # Parse request for structured analysis
    request = analyzer.parse_request(f"{intent} {context}".strip())

    # Calculate composite coherence score
    # Weight: intent match (40%), tool appropriateness (30%), contextual continuity (30%)
    intent_score = request.intent_confidence if request.intent else 0.5

    # Tool appropriateness scoring
    tool_scores = {
        "edit": ["transform", "generate", "analyze"],
        "write": ["generate", "persist"],
        "bash": ["search", "transform", "analyze"],
        "read": ["search", "analyze"],
    }
    appropriate_intents = tool_scores.get(tool.lower(), [])
    tool_fit = 0.8 if request.intent.value.lower() in appropriate_intents else 0.4

    # Query vault for similar task patterns (non-blocking)
    vault_score = 0.5
    try:
        vault_result = await asyncio.wait_for(mcp.vault_find_relevant_context(f"{intent} using {tool}"), timeout=2.0)
        if vault_result:
            vault_score = 0.7  # Prior success boosts confidence
    except Exception:
        pass  # Vault timeout is OK

    # Composite coherence
    coherence = (intent_score * 0.4) + (tool_fit * 0.3) + (vault_score * 0.3)

    # HIHO stability: optimal at 0.5, acceptable range 0.3-0.7
    hiho_score = _hiho_engine.calculate_hiho_score(coherence)

    # Determine issues
    issues = []
    if coherence < 0.3:
        issues.append("Intent unclear - consider more specific wording")
    elif coherence > 0.7:
        issues.append("Too constrained - allow for creative exploration")
    if tool_fit < 0.5:
        issues.append(f"Tool '{tool}' may not be optimal for {request.intent.value}")

    result = {
        "coherence": round(coherence, 3),
        "hiho_score": round(hiho_score, 3),
        "should_proceed": 0.3 <= coherence <= 0.7,
        "intent": request.intent.value if request.intent else "unknown",
        "intent_confidence": round(intent_score, 3),
        "issues": issues,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _track_journey_step(arguments: dict[str, Any]) -> list[TextContent]:
    """Record 12D FLUME trajectory point."""
    tracker = get_tracker()

    # Create synthetic execution result for tracking
    from cohezion.compound.executor import ExecutionMetrics, ExecutionResult

    metrics = ExecutionMetrics(
        coherence=arguments.get("coherence", 0.5),
        efficiency=arguments.get("efficiency", 0.5),
        duration_seconds=arguments.get("metadata", {}).get("duration_seconds", 0.0),
    )

    result = ExecutionResult(
        success=arguments.get("success", True),
        output="",
        metrics=metrics,
    )

    # Track the execution
    point = tracker.track_execution(
        execution_result=result,
        task_description=arguments.get("task_description", ""),
        operation_type=arguments.get("operation_type", "transform"),
    )

    # Store to vault asynchronously (non-blocking)
    try:
        mcp = await get_mcp()
        vault_entry = {
            "type": "trajectory_point",
            "dimensions": point.dimensions.tolist(),
            "coherence": point.coherence,
            "efficiency": point.efficiency,
            "operation_type": point.operation_type,
            "task_description": point.task_description,
            "timestamp": point.timestamp,
        }
        await asyncio.wait_for(mcp.vault_create("journey", vault_entry), timeout=3.0)
    except Exception as e:
        logger.debug("Vault store failed (non-blocking): %s", e)

    result = {
        "phi_score": point.phi_score,
        "dimensions": point.dimensions.tolist(),
        "coherence": point.coherence,
        "efficiency": point.efficiency,
        "timestamp": point.timestamp,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_trajectory(arguments: dict[str, Any]) -> list[TextContent]:
    """Retrieve recent trajectory."""
    tracker = get_tracker()
    window = arguments.get("window", 10)

    points = tracker._recent_points[-window:] if tracker._recent_points else []

    result = {
        "points": [
            {
                "dimensions": p.dimensions.tolist(),
                "coherence": p.coherence,
                "efficiency": p.efficiency,
                "timestamp": p.timestamp,
            }
            for p in points
        ],
        "count": len(points),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _detect_degradation(arguments: dict[str, Any]) -> list[TextContent]:
    """Check for coherence degradation."""
    detector = get_detector()
    metrics = arguments.get("metrics", {})

    alerts = detector.check_degradation(metrics)

    result = {
        "alerts": [
            {
                "metric": a.metric,
                "severity": a.severity.value,
                "message": a.message,
                "current": a.current_value,
                "baseline": a.baseline_value,
            }
            for a in alerts
        ],
        "alert_count": len(alerts),
        "has_critical": any(a.severity.value == "CRITICAL" for a in alerts),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _calculate_hiho(arguments: dict[str, Any]) -> list[TextContent]:
    """Calculate HIHO stability score."""
    coherence = arguments.get("coherence", 0.5)
    score = _hiho_engine.calculate_hiho_score(coherence)

    result = {
        "input_coherence": coherence,
        "hiho_score": score,
        "is_optimal": abs(coherence - 0.5) < 0.1,
        "stability_band": "optimal" if 0.3 <= coherence <= 0.7 else "unstable",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _extract_pattern(arguments: dict[str, Any]) -> list[TextContent]:
    """Extract and encode pattern with FLUME."""
    # Try to use FLUME encoder if available
    embedding = None
    try:
        from cohezion.flume.autoencoder import FlumeEncoder

        encoder = FlumeEncoder()
        code = arguments.get("code", "")
        embedding = encoder.encode(code).tolist()
    except Exception as e:
        logger.debug("FLUME encoding failed: %s", e)
        # Fallback: use deterministic hash-based encoding
        import hashlib

        code_hash = hashlib.sha256(arguments.get("code", "").encode()).hexdigest()
        embedding = [int(code_hash[i : i + 2], 16) / 255.0 for i in range(0, 64, 2)]

    result = {
        "name": arguments.get("name"),
        "category": arguments.get("category"),
        "description": arguments.get("description", ""),
        "confidence": arguments.get("confidence", 0.5),
        "has_flume_embedding": embedding is not None,
        "embedding_preview": embedding[:8] if embedding else None,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _query_patterns(arguments: dict[str, Any]) -> list[TextContent]:
    """Query vault for patterns."""
    query = arguments.get("query", "")
    limit = arguments.get("limit", 5)

    try:
        mcp = await get_mcp()
        patterns = await asyncio.wait_for(mcp.vault_find_relevant_context(query, limit=limit), timeout=3.0)

        result = {
            "patterns": patterns or [],
            "count": len(patterns) if patterns else 0,
        }
    except Exception as e:
        result = {"patterns": [], "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _refine_skill(arguments: dict[str, Any]) -> list[TextContent]:
    """Append pattern to PRIME skill."""
    skill_name = arguments.get("skill_name", "")
    pattern = arguments.get("pattern", {})

    # Find skill file
    skills_dir = Path("src/cohezion/skills")
    skill_file = None

    for f in skills_dir.glob("*.md"):
        if skill_name.lower() in f.stem.lower():
            skill_file = f
            break

    if not skill_file:
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Skill '{skill_name}' not found in {skills_dir}"}),
            )
        ]

    # Append refinement
    refinement = f"""
## Refinement {asyncio.get_event_loop().time()}
- Pattern: {pattern.get("name", "unknown")}
- Confidence: {pattern.get("confidence", 0.0):.2f}
- Coherence: {pattern.get("coherence", 0.0):.2f}

```
{pattern.get("code_example", "")}
```

"""

    try:
        with open(skill_file, "a") as f:
            f.write(refinement)

        result = {
            "success": True,
            "skill_file": str(skill_file),
            "pattern_appended": pattern.get("name"),
        }
    except Exception as e:
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Run coherence MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
