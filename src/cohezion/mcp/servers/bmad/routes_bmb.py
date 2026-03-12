"""BMAD BMB (BMAD Builder) tool routes."""

from aiohttp import web

from ._shared import routes


@routes.post("/tools/bmad_bmb_create_agent")
async def tool_bmad_bmb_create_agent(request: web.Request) -> web.Response:
    """Create agent tool."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_bmb_create_agent",
                "agent_name": data.get("agent_name"),
                "role": data.get("role"),
                "capabilities": data.get("capabilities", []),
                "message": "Agent creation guide provided",
                "agent_template": {
                    "name": data.get("agent_name"),
                    "role": data.get("role"),
                    "capabilities": data.get("capabilities", []),
                    "persona": "Define agent personality here",
                },
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_party_mode")
async def tool_bmad_party_mode(request: web.Request) -> web.Response:
    """Party mode tool."""
    try:
        data = await request.json()
        agents = data.get("agents", [])
        return web.json_response(
            {
                "tool": "bmad_party_mode",
                "objective": data.get("objective"),
                "agents": agents,
                "duration_minutes": data.get("duration_minutes", 30),
                "message": f"Multi-agent session configured with {len(agents)} agents",
                "facilitator_notes": "Guide agents through the objective, ensuring collaboration",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmb_create_workflow")
async def tool_bmad_bmb_create_workflow(request: web.Request) -> web.Response:
    """Create a new BMAD workflow."""
    try:
        data = await request.json()
        workflow_name = data.get("workflow_name", "")
        module = data.get("module", "core")
        return web.json_response(
            {
                "tool": "bmad_bmb_create_workflow",
                "workflow_name": workflow_name,
                "module": module,
                "template": {
                    "title": workflow_name,
                    "purpose": "Describe the workflow purpose",
                    "steps": ["1. First step", "2. Second step", "3. Third step"],
                    "outputs": ["Deliverable 1", "Deliverable 2"],
                },
                "location": f"_bmad/{module}/workflows/{workflow_name}.md",
                "next_step": f"Edit _bmad/{module}/workflows/{workflow_name}.md",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmb_create_module")
async def tool_bmad_bmb_create_module(request: web.Request) -> web.Response:
    """Create a new BMAD module."""
    try:
        data = await request.json()
        module_name = data.get("module_name", "")
        return web.json_response(
            {
                "tool": "bmad_bmb_create_module",
                "module_name": module_name,
                "description": data.get("description", ""),
                "structure": [
                    f"_bmad/{module_name}/",
                    f"_bmad/{module_name}/workflows/",
                    f"_bmad/{module_name}/agents/",
                    f"_bmad/{module_name}/templates/",
                ],
                "files_to_create": [
                    f"_bmad/{module_name}/README.md",
                    f"_bmad/{module_name}/_config.yaml",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmb_customize_agent")
async def tool_bmad_bmb_customize_agent(request: web.Request) -> web.Response:
    """Customize an existing agent."""
    try:
        data = await request.json()
        base_agent = data.get("base_agent", "bmm-pm")
        return web.json_response(
            {
                "tool": "bmad_bmb_customize_agent",
                "base_agent": base_agent,
                "customizations": data.get("customizations", {}),
                "new_agent_name": f"{base_agent}-custom",
                "location": f"_bmad/custom/agents/{base_agent}-custom.md",
                "template_sections": [
                    "Personality adjustments",
                    "Additional capabilities",
                    "Modified behavior",
                    "Custom responses",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmb_import_workflow")
async def tool_bmad_bmb_import_workflow(request: web.Request) -> web.Response:
    """Import external workflow into BMAD."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_bmb_import_workflow",
                "source": data.get("source_url", ""),
                "target_module": data.get("target_module", "core"),
                "steps": [
                    "1. Fetch workflow from source",
                    "2. Convert to BMAD format",
                    "3. Adapt terminology",
                    "4. Add BMAD metadata",
                    "5. Save to _bmad/",
                ],
                "adaptations": [
                    "Convert to BMAD style",
                    "Add agent references",
                    "Include success criteria",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_bmb_extend_tool")
async def tool_bmad_bmb_extend_tool(request: web.Request) -> web.Response:
    """Extend an existing BMAD tool."""
    try:
        data = await request.json()
        base_tool = data.get("base_tool", "bmad_bmm_create_prd")
        return web.json_response(
            {
                "tool": "bmad_bmb_extend_tool",
                "base_tool": base_tool,
                "new_tool_name": f"{base_tool}_extended",
                "new_params": data.get("new_params", []),
                "implementation_guide": [
                    "1. Copy base tool implementation",
                    "2. Add new parameters",
                    "3. Update parameter validation",
                    "4. Add new logic",
                    "5. Update response format",
                    "6. Test thoroughly",
                ],
                "file_location": f"src/cohezion/mcp/servers/bmad/tools/{base_tool}_extended.py",
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
