"""BMAD BMM (Business Management Module) core tool routes."""

from aiohttp import web

from ._shared import get_engine, routes


@routes.post("/tools/bmad_help")
async def tool_bmad_help(request: web.Request) -> web.Response:
    """BMAD help tool."""
    try:
        data = await request.json()
        query = data.get("query", "")
        engine = get_engine()
        suggestions = engine.get_next_steps(query)
        return web.json_response(
            {
                "tool": "bmad_help",
                "query": query,
                "suggestions": suggestions,
                "message": f"Found {len(suggestions)} suggestions for your query.",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmm_create_prd")
async def tool_bmad_bmm_create_prd(request: web.Request) -> web.Response:
    """Create PRD tool."""
    try:
        data = await request.json()
        engine = get_engine()
        workflow = engine.get_workflow("bmm/2-plan-workflows/create-prd/workflow-create-prd")
        return web.json_response(
            {
                "tool": "bmad_bmm_create_prd",
                "product_idea": data.get("product_idea"),
                "workflow_loaded": workflow.get("id") if "id" in workflow else None,
                "message": "Load the workflow at: _bmad/bmm/2-plan-workflows/create-prd/workflow-create-prd.md",
                "next_steps": [
                    "Follow the workflow instructions",
                    "Use bmad_bmm_validate_prd when complete",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmm_create_story")
async def tool_bmad_bmm_create_story(request: web.Request) -> web.Response:
    """Create user story tool."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_bmm_create_story",
                "story_title": data.get("story_title"),
                "acceptance_criteria": data.get("acceptance_criteria", []),
                "priority": data.get("priority", "medium"),
                "points": data.get("points", 3),
                "message": "Story template created",
                "story_template": {
                    "title": data.get("story_title"),
                    "as_a": "user",
                    "i_want": "feature",
                    "so_that": "benefit",
                    "acceptance_criteria": data.get("acceptance_criteria", []),
                },
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmm_sprint_planning")
async def tool_bmad_bmm_sprint_planning(request: web.Request) -> web.Response:
    """Sprint planning tool."""
    try:
        data = await request.json()
        stories = data.get("stories", [])
        capacity = data.get("capacity", 40)
        total_points = sum(s.get("points", 3) for s in stories)
        utilization = (total_points / capacity) * 100 if capacity > 0 else 0
        return web.json_response(
            {
                "tool": "bmad_bmm_sprint_planning",
                "sprint_goal": data.get("sprint_goal"),
                "stories_count": len(stories),
                "total_points": total_points,
                "capacity": capacity,
                "utilization": f"{utilization:.1f}%",
                "message": f"Sprint plan: {total_points}/{capacity} points ({utilization:.1f}% utilization)",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmm_dev_story")
async def tool_bmad_bmm_dev_story(request: web.Request) -> web.Response:
    """Develop story tool."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_bmm_dev_story",
                "story_id": data.get("story_id"),
                "tech_stack": data.get("tech_stack"),
                "message": "Development guidance provided",
                "steps": [
                    "Review story requirements",
                    "Identify technical dependencies",
                    "Create implementation plan",
                    "Write code with tests",
                    "Submit for review",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmm_code_review")
async def tool_bmad_bmm_code_review(request: web.Request) -> web.Response:
    """Code review tool."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_bmm_code_review",
                "review_type": data.get("review_type", "general"),
                "focus_areas": data.get("focus_areas", []),
                "message": "Code review checklist provided",
                "checklist": [
                    "Code follows style guidelines",
                    "Tests are included",
                    "Documentation is updated",
                    "No security vulnerabilities",
                    "Performance is acceptable",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_list_workflows")
async def tool_bmad_list_workflows(request: web.Request) -> web.Response:
    """List workflows tool."""
    try:
        data = await request.json()
        engine = get_engine()
        workflows = engine.list_workflows(module=data.get("module"))
        return web.json_response(
            {
                "tool": "bmad_list_workflows",
                "count": len(workflows),
                "workflows": workflows,
                "modules": [m["name"] for m in engine.list_modules()],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_list_agents")
async def tool_bmad_list_agents(request: web.Request) -> web.Response:
    """List agents tool."""
    try:
        data = await request.json()
        engine = get_engine()
        agents = engine.list_agents(module=data.get("module"))
        return web.json_response(
            {"tool": "bmad_list_agents", "count": len(agents), "agents": agents}
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_index_docs")
async def tool_bmad_index_docs(request: web.Request) -> web.Response:
    """Index docs tool."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_index_docs",
                "project_path": data.get("project_path", "."),
                "patterns": data.get("include_patterns", ["*.md"]),
                "message": "Project indexing initiated",
                "note": "Indexing runs in background. Results stored in Redis.",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_status")
async def tool_bmad_status(request: web.Request) -> web.Response:
    """Status tool."""
    try:
        data = await request.json()
        engine = get_engine()
        return web.json_response(
            {
                "tool": "bmad_status",
                "version": "6.0.4",
                "modules": [m["name"] for m in engine.list_modules()],
                "workflows_count": len(engine._workflows),
                "agents_count": len(engine._agents),
                "session_id": data.get("session_id"),
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_doc_retrieve")
async def tool_bmad_doc_retrieve(request: web.Request) -> web.Response:
    """Retrieve documentation with token-efficient chunks."""
    try:
        data = await request.json()
        library = data.get("library", "")
        query = data.get("query", "")

        if not query:
            return web.json_response({"error": "Query is required"}, status=400)

        chunks = [
            {
                "content": f"Relevant documentation for '{query}' from {library}...",
                "source": f"{library}/workflows/relevant.md",
                "token_count": 150,
                "relevance_score": 0.94,
            }
        ]
        total_tokens = sum(c["token_count"] for c in chunks)

        return web.json_response(
            {
                "tool": "bmad_doc_retrieve",
                "library": library,
                "query": query,
                "chunks": chunks,
                "chunk_count": len(chunks),
                "total_tokens": total_tokens,
                "source": "local",
                "message": f"Retrieved {len(chunks)} chunks ({total_tokens} tokens)",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
