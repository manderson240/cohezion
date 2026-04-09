"""Proactive BMad - Anticipates needs and suggests actions.

Adds proactive monitoring tools to BMad MCP Server:
- bmad_proactive_scan: Scan codebase for alignment suggestions
- bmad_proactive_execute: Execute a proactive suggestion
- bmad_proactive_summary: Get summary of proactive monitoring state
- bmad_proactive_enable: Enable/disable proactive patterns
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from ._shared import routes


logger = logging.getLogger(__name__)


async def proactive_scan(request: web.Request) -> web.Response:
    """Scan codebase for proactive BMad alignment suggestions.

    Request:
        POST /proactive/scan
        {}

    Response:
        {
            "suggestions": [
                {
                    "id": "repo-workflow-missing",
                    "title": "Repository Operations Missing BMad Workflows",
                    "priority": "high",
                    "category": "alignment",
                    "auto_executable": true,
                    "confidence": 0.9
                }
            ],
            "summary": {
                "total": 3,
                "by_priority": {"critical": 0, "high": 2, "medium": 1, "low": 0}
            }
        }
    """
    try:
        from .proactive_monitor import ProactiveMonitor

        project_root = Path(request.app.get("project_root", "."))
        monitor = ProactiveMonitor(project_root)

        suggestions = await monitor.scan_for_suggestions()
        summary = monitor.get_summary()

        return web.json_response(
            {
                "suggestions": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "description": s.description,
                        "priority": s.priority,
                        "category": s.category,
                        "suggested_action": s.suggested_action,
                        "auto_executable": s.auto_executable,
                        "confidence": s.confidence,
                    }
                    for s in suggestions
                ],
                "summary": summary,
            }
        )
    except Exception as e:
        logger.error(f"Proactive scan failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )


async def proactive_execute(request: web.Request) -> web.Response:
    """Execute a proactive suggestion.

    Request:
        POST /proactive/execute
        {
            "suggestion_id": "repo-workflow-missing",
            "confirm": true  # Skip confirmation if true
        }

    Response:
        {
            "success": true,
            "suggestion_id": "repo-workflow-missing",
            "actions_taken": ["Created workflow at _bmad/core/workflows/repository-operations/"]
        }
    """
    try:
        from .proactive_monitor import ProactiveMonitor

        data = await request.json()
        suggestion_id = data.get("suggestion_id")
        confirm = data.get("confirm", False)

        if not suggestion_id:
            return web.json_response(
                {"error": "suggestion_id required"},
                status=400,
            )

        project_root = Path(request.app.get("project_root", "."))
        monitor = ProactiveMonitor(project_root)

        # Find suggestion
        suggestions = await monitor.scan_for_suggestions()
        suggestion = next((s for s in suggestions if s.id == suggestion_id), None)

        if not suggestion:
            return web.json_response(
                {"error": f"Suggestion {suggestion_id} not found"},
                status=404,
            )

        if not suggestion.auto_executable:
            return web.json_response(
                {"error": f"Suggestion {suggestion_id} is not auto-executable"},
                status=400,
            )

        success = await monitor.execute_suggestion(suggestion, confirm=confirm)

        if success:
            return web.json_response(
                {
                    "success": True,
                    "suggestion_id": suggestion_id,
                    "message": f"Executed: {suggestion.suggested_action}",
                }
            )
        else:
            return web.json_response(
                {"error": f"Failed to execute {suggestion_id}"},
                status=500,
            )
    except Exception as e:
        logger.error(f"Proactive execute failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )


async def proactive_summary(request: web.Request) -> web.Response:
    """Get summary of proactive monitoring state.

    Request:
        GET /proactive/summary

    Response:
        {
            "total_patterns": 5,
            "enabled_patterns": 5,
            "active_suggestions": 3,
            "by_priority": {"critical": 0, "high": 2, "medium": 1, "low": 0},
            "by_category": {"alignment": 2, "integration": 1, "quality": 0}
        }
    """
    try:
        from .proactive_monitor import ProactiveMonitor

        project_root = Path(request.app.get("project_root", "."))
        monitor = ProactiveMonitor(project_root)
        await monitor.scan_for_suggestions()  # Refresh suggestions

        return web.json_response(monitor.get_summary())
    except Exception as e:
        logger.error(f"Proactive summary failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )


async def proactive_enable_pattern(request: web.Request) -> web.Response:
    """Enable or disable a proactive pattern.

    Request:
        POST /proactive/pattern/{pattern_id}/enable
        {
            "enabled": true
        }

    Response:
        {
            "pattern_id": "repository-workflow-gap",
            "enabled": true,
            "message": "Pattern enabled"
        }
    """
    try:
        from .proactive_monitor import ProactiveMonitor

        pattern_id = request.match_info.get("pattern_id")
        data = await request.json()
        enabled = data.get("enabled", True)

        if not pattern_id:
            return web.json_response(
                {"error": "pattern_id required"},
                status=400,
            )

        project_root = Path(request.app.get("project_root", "."))
        monitor = ProactiveMonitor(project_root)

        # Find pattern
        pattern = next((p for p in monitor.patterns if p.name == pattern_id), None)

        if not pattern:
            return web.json_response(
                {"error": f"Pattern {pattern_id} not found"},
                status=404,
            )

        pattern.enabled = enabled

        return web.json_response(
            {
                "pattern_id": pattern_id,
                "enabled": enabled,
                "message": f"Pattern {'enabled' if enabled else 'disabled'}",
            }
        )
    except Exception as e:
        logger.error(f"Proactive enable pattern failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )


async def proactive_list_patterns(request: web.Request) -> web.Response:
    """List all proactive patterns.

    Request:
        GET /proactive/patterns

    Response:
        {
            "patterns": [
                {
                    "name": "repository-workflow-gap",
                    "description": "New repository without BMad workflow",
                    "enabled": true
                }
            ]
        }
    """
    try:
        from .proactive_monitor import ProactiveMonitor

        project_root = Path(request.app.get("project_root", "."))
        monitor = ProactiveMonitor(project_root)

        return web.json_response(
            {
                "patterns": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "enabled": p.enabled,
                    }
                    for p in monitor.patterns
                ],
            }
        )
    except Exception as e:
        logger.error(f"Proactive list patterns failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )


# Register routes with BMad MCP server using decorators
from ._shared import routes


@routes.post("/proactive/scan")
async def scan_route(request: web.Request) -> web.Response:
    return await proactive_scan(request)


@routes.post("/proactive/execute")
async def execute_route(request: web.Request) -> web.Response:
    return await proactive_execute(request)


@routes.get("/proactive/summary")
async def summary_route(request: web.Request) -> web.Response:
    return await proactive_summary(request)


@routes.post("/proactive/pattern/{pattern_id}/enable")
async def enable_pattern_route(request: web.Request) -> web.Response:
    return await proactive_enable_pattern(request)


@routes.get("/proactive/patterns")
async def list_patterns_route(request: web.Request) -> web.Response:
    return await proactive_list_patterns(request)


logger.info("Proactive BMad routes registered")
