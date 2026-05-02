"""BMAD MCP tools - extended commands (CIS, TEA, BMB, utility)."""

from __future__ import annotations

from typing import Any

from cohezion.mcp.bmad_app import app, get_engine, get_session_manager


@app.tool()
async def bmad_cis_brainstorming(
    topic: str,
    participants: int = 1,
    timebox_minutes: int = 15,
    techniques: list[str] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """Facilitate brainstorming session. Use for creative ideation.

    Args:
        topic: Topic to brainstorm
        participants: Number of people (affects techniques)
        timebox_minutes: Time limit for session
        techniques: Specific techniques to use
        session_id: Optional session ID
    """
    engine = get_engine()
    workflow = engine.load_workflow("cis", "workflows/brainstorming")
    session = await engine.execute_workflow(
        workflow,
        {
            "topic": topic,
            "participants": participants,
            "timebox_minutes": timebox_minutes,
            "techniques": techniques or ["mind-mapping", "rapid-ideation"],
        },
        session_id,
    )
    return {
        "brainstorming_session": session,
        "workflow": "cis/workflows/brainstorming.md",
        "techniques_suggested": session.get("techniques", []),
    }


@app.tool()
async def bmad_tea_test_design(
    feature_description: str,
    risk_level: str = "medium",
    test_types: list[str] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """Design tests for a feature. Use when planning quality assurance.

    Args:
        feature_description: What needs testing
        risk_level: Risk level (low/medium/high/critical)
        test_types: Types of tests (unit/integration/e2e/performance)
        session_id: Optional session ID
    """
    engine = get_engine()
    workflow = engine.load_workflow("tea", "testarch/test-design")
    tests = await engine.execute_workflow(
        workflow,
        {
            "feature_description": feature_description,
            "risk_level": risk_level,
            "test_types": test_types or ["unit", "integration"],
        },
        session_id,
    )
    return {
        "test_strategy": tests,
        "workflow": "tea/testarch/test-design.md",
        "test_cases_count": len(tests.get("test_cases", [])),
    }


@app.tool()
async def bmad_bmb_create_agent(
    agent_name: str,
    role: str,
    capabilities: list[str],
    communication_style: str = "professional",
    session_id: str = "",
) -> dict[str, Any]:
    """Create a custom BMAD agent. Use to extend the system.

    Args:
        agent_name: Unique agent name
        role: Agent's primary role
        capabilities: List of capabilities
        communication_style: How agent communicates
        session_id: Optional session ID
    """
    engine = get_engine()
    workflow = engine.load_workflow("bmb", "workflows/create-agent")
    agent = await engine.execute_workflow(
        workflow,
        {
            "agent_name": agent_name,
            "role": role,
            "capabilities": capabilities,
            "communication_style": communication_style,
        },
        session_id,
    )
    return {
        "agent_definition": agent,
        "workflow": "bmb/workflows/create-agent.md",
        "activation_command": f"/bmad-agent-{agent_name}",
    }


@app.tool()
async def bmad_party_mode(
    objective: str,
    agents: list[str],
    duration_minutes: int = 30,
    session_id: str = "",
) -> dict[str, Any]:
    """Multi-agent collaboration mode. Use for complex tasks requiring multiple perspectives.

    Args:
        objective: What the group should accomplish
        agents: List of agent names to include
        duration_minutes: Time limit for session
        session_id: Optional session ID
    """
    engine = get_engine()
    agent_personas = []
    for agent_name in agents:
        persona = engine.load_agent(agent_name)
        if persona:
            agent_personas.append(persona)
    return {
        "party_session": {
            "objective": objective,
            "agents": agent_personas,
            "duration": duration_minutes,
            "facilitator_notes": f"Guide {len(agents)} agents to collaborate on: {objective}",
        },
        "workflow": "core/workflows/party-mode.md",
        "agent_count": len(agent_personas),
        "session_id": session_id or engine.generate_session_id(),
    }


@app.tool()
async def bmad_list_workflows(
    module: str = "",
    phase: str = "",
) -> dict[str, Any]:
    """List available BMAD workflows. Use to discover capabilities.

    Args:
        module: Filter by module (bmm/gds/cis/tea/bmb/core)
        phase: Filter by phase (discover/plan/build/ship)
    """
    engine = get_engine()
    workflows = engine.list_workflows(module, phase)
    return {"workflows": workflows, "count": len(workflows), "modules": engine.list_modules()}


@app.tool()
async def bmad_list_agents(module: str = "") -> dict[str, Any]:
    """List available BMAD agents. Use to see who can help.

    Args:
        module: Filter by module
    """
    engine = get_engine()
    agents = engine.list_agents(module)
    return {"agents": agents, "count": len(agents), "total_modules": len(engine.list_modules())}


@app.tool()
async def bmad_index_docs(
    project_path: str = ".",
    include_patterns: list[str] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """Index project documentation. Use to make project searchable.

    Args:
        project_path: Path to project
        include_patterns: File patterns to include
        session_id: Optional session ID
    """
    engine = get_engine()
    result = await engine.index_project(
        project_path,
        include_patterns or ["*.md", "*.py", "*.js", "*.ts", "*.json"],
    )
    return {
        "indexing_result": result,
        "files_indexed": result.get("files_indexed", 0),
        "workflow": "core/tasks/index-docs.md",
    }


@app.tool()
async def bmad_status(session_id: str = "") -> dict[str, Any]:
    """Get BMAD session status. Use to see current state.

    Args:
        session_id: Session ID to check
    """
    session_mgr = get_session_manager()
    if session_id:
        session = await session_mgr.get_session(session_id)
        return {
            "session": session,
            "status": "active" if session else "not_found",
            "history": session.get("history", []) if session else [],
        }
    engine = get_engine()
    return {
        "modules_loaded": engine.list_modules(),
        "agents_available": len(engine.list_agents()),
        "workflows_available": len(engine.list_workflows()),
        "redis_connected": session_mgr.is_connected(),
        "version": "6.0.4",
    }
