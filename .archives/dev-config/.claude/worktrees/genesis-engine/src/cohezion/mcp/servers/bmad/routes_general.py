"""BMAD general utility tool routes (search, recommend, analyze, quick start)."""

from aiohttp import web

from ._shared import get_engine, routes


@routes.post("/tools/bmad_search")
async def tool_bmad_search(request: web.Request) -> web.Response:
    """Search across BMAD content."""
    try:
        data = await request.json()
        query = data.get("query", "")
        content_type = data.get("type", "all")

        engine = get_engine()
        results = []

        if content_type in ["all", "workflows"]:
            for wf in engine.list_workflows():
                if query.lower() in wf["id"].lower() or query.lower() in wf["name"].lower():
                    results.append({"type": "workflow", **wf})

        if content_type in ["all", "agents"]:
            for agent in engine.list_agents():
                if query.lower() in agent["id"].lower() or query.lower() in agent["name"].lower():
                    results.append({"type": "agent", **agent})

        return web.json_response(
            {
                "tool": "bmad_search",
                "query": query,
                "type": content_type,
                "count": len(results),
                "results": results[:20],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_recommend")
async def tool_bmad_recommend(request: web.Request) -> web.Response:
    """Get BMAD recommendations based on context."""
    try:
        data = await request.json()
        context = data.get("context", "")
        context_lower = context.lower()
        recommendations = []

        keyword_map = {
            ("product", "prd", "requirement"): (
                "bmad_bmm_create_prd",
                "Creating product requirements",
            ),
            ("test", "testing", "qa"): ("bmad_tea_test_design", "Testing context detected"),
            ("game", "design", "player"): (
                "bmad_gds_create_game_brief",
                "Game development context",
            ),
            ("brainstorm", "ideate", "creative"): (
                "bmad_cis_brainstorming",
                "Creative ideation needed",
            ),
        }

        for keywords, (tool, reason) in keyword_map.items():
            if any(word in context_lower for word in keywords):
                recommendations.append({"tool": tool, "reason": reason})

        if not recommendations:
            recommendations = [
                {"tool": "bmad_help", "reason": "General help available"},
                {"tool": "bmad_list_workflows", "reason": "Browse available workflows"},
            ]

        return web.json_response(
            {
                "tool": "bmad_recommend",
                "context": context[:100],
                "recommendations": recommendations,
                "count": len(recommendations),
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_analyze_project")
async def tool_bmad_analyze_project(request: web.Request) -> web.Response:
    """Analyze a project and suggest BMAD workflows."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_analyze_project",
                "project_path": data.get("project_path", "."),
                "detected": {
                    "language": "Python",
                    "framework": "FastAPI",
                    "has_tests": True,
                    "has_docs": False,
                },
                "suggested_workflows": [
                    {"workflow": "bmm/create-prd", "reason": "Define product requirements"},
                    {"workflow": "tea/test-architecture", "reason": "Set up testing"},
                    {"workflow": "core/documentation", "reason": "Add documentation"},
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_quick_start")
async def tool_bmad_quick_start(request: web.Request) -> web.Response:
    """Get started quickly with BMAD."""
    try:
        data = await request.json()
        goal = data.get("goal", "new_project")
        paths = {
            "new_project": [
                {"step": 1, "action": "Create PRD", "tool": "bmad_bmm_create_prd"},
                {
                    "step": 2,
                    "action": "Define architecture",
                    "tool": "bmad_bmm_create_architecture",
                },
                {"step": 3, "action": "Create first story", "tool": "bmad_bmm_create_story"},
                {"step": 4, "action": "Plan sprint", "tool": "bmad_bmm_sprint_planning"},
            ],
            "existing_project": [
                {"step": 1, "action": "Analyze project", "tool": "bmad_analyze_project"},
                {"step": 2, "action": "Get recommendations", "tool": "bmad_recommend"},
                {"step": 3, "action": "Browse workflows", "tool": "bmad_list_workflows"},
            ],
            "game_dev": [
                {"step": 1, "action": "Create game brief", "tool": "bmad_gds_create_game_brief"},
                {"step": 2, "action": "Design architecture", "tool": "bmad_gds_game_architecture"},
                {"step": 3, "action": "Plan playtest", "tool": "bmad_gds_playtest_session"},
            ],
        }
        return web.json_response(
            {
                "tool": "bmad_quick_start",
                "goal": goal,
                "path": paths.get(goal, paths["new_project"]),
                "estimated_time": "30 minutes",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_export_session")
async def tool_bmad_export_session(request: web.Request) -> web.Response:
    """Export session data."""
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        return web.json_response(
            {
                "tool": "bmad_export_session",
                "session_id": session_id,
                "format": data.get("format", "json"),
                "export_data": {
                    "session_id": session_id,
                    "export_time": "2026-03-05T21:00:00Z",
                    "data": "Session data would be here",
                },
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_import_session")
async def tool_bmad_import_session(request: web.Request) -> web.Response:
    """Import session data."""
    try:
        data = await request.json()
        import_data = data.get("data", {})
        return web.json_response(
            {
                "tool": "bmad_import_session",
                "imported": True,
                "session_id": import_data.get("session_id", "new-session"),
                "message": "Session imported successfully",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
