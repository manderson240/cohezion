"""MCP Compound Server - Unified interface for compound engineering.

This MCP server exposes tools for:
1. Session lifecycle management (warm-start, execute, clean-shutdown)
2. Token cache operations (get metrics, optimize)
3. Adversarial review (Ralph Lopps checkpoint)
4. Autoresearch (analyze, generate research plan)
5. Experiential learning (capture, extract patterns)
"""

import json
import logging
from typing import Any

from fastmcp import FastMCP

from cohezion.compound.adversarial import MultiperspectiveReviewBoard, RalphLoppsReviewer
from cohezion.compound.autoresearch import (
    AutoresearchEngine,
    ExperientialLearningLoop,
    RetrospectionEngine,
    SkillRefiner,
)

# Import compound engineering components
from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.core.mcp_client import get_mcp_client


logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    "Compound Engineering",
    instructions=(
        "A compound engineering MCP server for multi-session AI workflows. "
        "Manage sessions with warm-start/clean-shutdown, optimize token efficiency, "
        "run adversarial reviews, and capture learnings to vault."
    ),
)

# Initialize components
session_manager: CompoundSessionManager | None = None
ralph_reviewer = RalphLoppsReviewer()
review_board = MultiperspectiveReviewBoard()
autoresearch = AutoresearchEngine()
retrospection = RetrospectionEngine()
skill_refiner = SkillRefiner()
learning_loop = ExperientialLearningLoop()


@mcp.tool()
async def compound_start_session(
    max_cache_entries: int = 256, enable_persistence: bool = True
) -> dict[str, Any]:
    """Start a compound session with warm-start from vault.

    Args:
        max_cache_entries: Maximum cache entries to load
        enable_persistence: Whether to enable vault persistence

    Returns:
        Session summary with cache status
    """
    global session_manager

    try:
        if session_manager is None:
            session_manager = CompoundSessionManager()
            await session_manager.__aenter__()

        summary = session_manager.start_session(max_cache_entries=max_cache_entries)

        return {
            "status": "success",
            "session_id": summary.get("session_id"),
            "cache_entries_loaded": summary.get("cache_entries_loaded", 0),
            "persistence_enabled": enable_persistence,
        }

    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def compound_check_alignment(request: str, threshold: float = 0.5) -> dict[str, Any]:
    """Check request alignment before execution.

    Args:
        request: The request to check
        threshold: Coherence threshold (default 0.5 HIHO)

    Returns:
        Alignment result with coherence score
    """
    try:
        if session_manager is None:
            return {
                "status": "error",
                "error": "No active session. Call compound_start_session first.",
            }

        result = session_manager.check_alignment(request, threshold)

        return {
            "status": "success",
            "coherence": result.coherence,
            "should_proceed": result.should_proceed,
            "issues": result.issues if hasattr(result, "issues") else [],
        }

    except Exception as e:
        logger.error(f"Alignment check failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def compound_end_session(save_cache: bool = True) -> dict[str, Any]:
    """End compound session with clean-shutdown to vault.

    Args:
        save_cache: Whether to save cache to vault

    Returns:
        Session end summary
    """
    global session_manager

    try:
        if session_manager is None:
            return {"status": "error", "error": "No active session to end."}

        summary = session_manager.end_session()

        # Persist via MCP if enabled
        if save_cache:
            mcp_client = get_mcp_client()
            await mcp_client.vault_write(
                f"logs/compound/session_{summary.get('session_id')}_end.json",
                json.dumps(summary, indent=2),
            )

        await session_manager.__aexit__(None, None, None)
        session_manager = None

        return {"status": "success", "session_summary": summary}

    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def cache_get_metrics() -> dict[str, Any]:
    """Get token cache efficiency metrics.

    Returns:
        Cache metrics including hit rate
    """
    try:
        from cohezion.swarm.token_cache_optimizer import get_token_cache_optimizer

        optimizer = get_token_cache_optimizer()
        metrics = optimizer.get_metrics()

        return {"status": "success", "metrics": metrics}

    except Exception as e:
        logger.error(f"Failed to get cache metrics: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def cache_optimize() -> dict[str, Any]:
    """Run cache optimization pass.

    Returns:
        Optimization recommendations
    """
    try:
        from cohezion.swarm.token_cache_optimizer import get_token_cache_optimizer

        optimizer = get_token_cache_optimizer()
        recommendations = await optimizer.optimize()

        return {"status": "success", "recommendations": recommendations}

    except Exception as e:
        logger.error(f"Cache optimization failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def ralph_lopps_review(code: str, context: str = "") -> dict[str, Any]:
    """Run Ralph Lopps Red Team adversarial review.

    Args:
        code: Code to review
        context: Optional execution context

    Returns:
        Adversarial findings
    """
    try:
        findings = ralph_reviewer.review(code, {"context": context} if context else {})

        return {
            "status": "success",
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "line_number": f.line_number,
                }
                for f in findings
            ],
            "total_findings": len(findings),
            "critical_count": sum(1 for f in findings if f.severity == "critical"),
        }

    except Exception as e:
        logger.error(f"Adversarial review failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def multiperspective_review(proposal: str) -> dict[str, Any]:
    """Run Blue/Green/Yellow Hat multiperspective review.

    Args:
        proposal: JSON string of proposal to review

    Returns:
        Multi-perspective review results
    """
    try:
        proposal_dict = json.loads(proposal)
        review = review_board.full_review(proposal_dict)

        return {
            "status": "success",
            "review": {
                "blue_process_optimizations": review["blue"],
                "green_alternatives": review["green"],
                "yellow_risks": review["yellow"],
                "ralph_findings": [
                    {"severity": f.severity, "description": f.description} for f in review["ralph"]
                ],
            },
        }

    except Exception as e:
        logger.error(f"Multiperspective review failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def autoresearch_analyze(metrics_json: str) -> dict[str, Any]:
    """Analyze metrics and identify improvement opportunities.

    Args:
        metrics_json: JSON string of metrics to analyze

    Returns:
        Improvement opportunities
    """
    try:
        metrics = json.loads(metrics_json)
        opportunities = await autoresearch.analyze(metrics)

        return {
            "status": "success",
            "opportunities": [
                {
                    "category": opp.category,
                    "priority": opp.priority,
                    "current_value": opp.current_value,
                    "target_value": opp.target_value,
                    "potential_impact": opp.potential_impact,
                    "recommendation": opp.recommendation,
                }
                for opp in opportunities
            ],
            "total_opportunities": len(opportunities),
        }

    except Exception as e:
        logger.error(f"Autoresearch analysis failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def learning_capture(execution_result_json: str) -> dict[str, Any]:
    """Capture execution learning to vault.

    Args:
        execution_result_json: JSON string of execution result

    Returns:
        Capture result
    """
    try:
        execution_result = json.loads(execution_result_json)
        mcp_client = get_mcp_client()

        path = await retrospection.capture_learning(execution_result, mcp_client)

        return {
            "status": "success" if path else "warning",
            "vault_path": path,
            "captured": path is not None,
        }

    except Exception as e:
        logger.error(f"Learning capture failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def learning_process_execution(execution_result_json: str) -> dict[str, Any]:
    """Process execution through full learning loop.

    Args:
        execution_result_json: JSON string of execution result

    Returns:
        Learning loop results
    """
    try:
        execution_result = json.loads(execution_result_json)
        mcp_client = get_mcp_client()

        results = await learning_loop.process_execution(execution_result, mcp_client)

        return {"status": "success", "results": results}

    except Exception as e:
        logger.error(f"Learning loop processing failed: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def skill_refinement_apply(skill_name: str, refinement_type: str) -> dict[str, Any]:
    """Apply refinement to a skill.

    Args:
        skill_name: Name of skill to refine (alphanumeric, hyphens, underscores only)
        refinement_type: Type of refinement (token_optimization, coherence_improvement, cache_optimization)

    Returns:
        Refinement result
    """
    import re

    try:
        # Validate skill_name - only allow safe characters
        if not re.match(r"^[\w\-]+$", skill_name):
            return {
                "status": "error",
                "error": "Invalid skill_name. Use only alphanumeric characters, hyphens, and underscores.",
            }

        # Validate refinement_type against whitelist
        valid_types = ["token_optimization", "coherence_improvement", "cache_optimization"]
        if refinement_type not in valid_types:
            return {
                "status": "error",
                "error": f"Invalid refinement_type. Must be one of: {', '.join(valid_types)}",
            }

        skill_path = f"src/cohezion/skills/{skill_name}.md"

        refinement = {
            "type": refinement_type,
            "finding": f"Auto-generated refinement for {refinement_type}",
            "recommendation": "See skill file for updates",
        }

        success = await skill_refiner.apply_refinement(skill_path, refinement)

        return {
            "status": "success" if success else "failed",
            "skill": skill_name,
            "refinement_applied": success,
        }

    except Exception as e:
        logger.error(f"Skill refinement failed: {e}")
        return {"status": "error", "error": str(e)}


async def check_redis_health() -> dict[str, Any]:
    """Check Redis connection health on startup."""
    import os

    import redis.asyncio as redis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        client = redis.from_url(redis_url, socket_connect_timeout=5)
        await client.ping()
        await client.close()
        logger.info(f"Redis health check passed: {redis_url}")
        return {"status": "healthy", "url": redis_url}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e), "url": redis_url}


# Server lifecycle
def main():
    """Run the MCP server."""
    # Run Redis health check on startup
    import asyncio

    health = asyncio.run(check_redis_health())
    if health["status"] != "healthy":
        logger.warning("Redis unavailable - cache persistence disabled")

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
