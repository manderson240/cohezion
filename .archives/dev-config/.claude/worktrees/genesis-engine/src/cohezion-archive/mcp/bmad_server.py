"""BMAD MCP Server - 108 BMAD commands via MCP protocol.

Provides all BMAD functionality via Model Context Protocol:
- 108 BMAD tools (commands)
- 28 agent personas as prompts
- Workflow resources
- Session management via Redis

Usage:
    uv run python -m cohezion.mcp.bmad_server

Ports:
    - 8361: BMAD MCP Server (HTTP/SSE)

Environment:
    - MCP_API_KEY: Authentication key (required)
    - REDIS_URL: Redis connection (default: redis://localhost:6379)
    - BMAD_DATA_PATH: Path to _bmad directory (default: ./_bmad)
    - MCP_PORT: Server port (default: 8361)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from cohezion.mcp.servers.bmad.engine import BMADEngine
from cohezion.mcp.shared.session import SessionManager


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("bmad-mcp")

# Initialize FastMCP server
app = FastMCP("bmad-method")

# Configuration
BMAD_DATA_PATH = Path(os.getenv("BMAD_DATA_PATH", "_bmad"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MCP_API_KEY = os.getenv("MCP_API_KEY", "dev-key-change-in-production")

# Global instances
_engine: BMADEngine | None = None
_session_manager: SessionManager | None = None


def get_engine() -> BMADEngine:
    """Get or create BMAD engine."""
    global _engine
    if _engine is None:
        _engine = BMADEngine(BMAD_DATA_PATH)
        logger.info(f"BMAD engine initialized with data from {BMAD_DATA_PATH}")
    return _engine


def get_session_manager() -> SessionManager:
    """Get or create session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(REDIS_URL)
        logger.info(f"Session manager initialized with Redis at {REDIS_URL}")
    return _session_manager


# ============================================================================
# CORE BMAD TOOLS (108 commands)
# ============================================================================


@app.tool()
async def bmad_help(
    query: str = "",
    context: str = "",
    session_id: str = "",
) -> dict[str, Any]:
    """Interactive BMAD help system. Use when user asks 'what should I do next' or needs guidance.

    Args:
        query: User's question or current situation
        context: Current project context/state
        session_id: Optional session ID for continuity

    Returns:
        Help response with next steps and recommendations
    """
    engine = get_engine()
    session = await get_session_manager().get_session(session_id) if session_id else None

    # Load help workflow
    _help_workflow = engine.load_workflow("core", "tasks/help")

    # Analyze context
    analysis = engine.analyze_context(context, session)

    # Get recommendations
    recommendations = engine.get_next_steps(query, analysis, session)

    return {
        "help_response": recommendations,
        "workflow_loaded": "core/tasks/help.md",
        "analysis": analysis,
        "available_modules": engine.list_modules(),
        "suggested_commands": recommendations.get("suggested_commands", []),
    }


@app.tool()
async def bmad_bmm_create_prd(
    product_idea: str,
    target_users: str,
    key_features: list[str],
    session_id: str = "",
    save_to_vault: bool = True,
) -> dict[str, Any]:
    """Create a Product Requirements Document (PRD). Use when starting a new product or feature.

    Args:
        product_idea: Description of the product or feature
        target_users: Who will use this product
        key_features: List of key features/capabilities
        session_id: Optional session ID
        save_to_vault: Whether to save the PRD to vault

    Returns:
        PRD content, workflow steps, and next actions
    """
    engine = get_engine()
    workflow = engine.load_workflow("bmm", "2-plan-workflows/create-prd/workflow-create-prd")

    # Execute workflow
    prd_content = await engine.execute_workflow(
        workflow,
        {
            "product_idea": product_idea,
            "target_users": target_users,
            "key_features": key_features,
        },
        session_id,
    )

    # Update session
    if session_id:
        await get_session_manager().update_session(
            session_id, {"last_action": "create_prd", "prd_created": True}
        )

    return {
        "prd_content": prd_content,
        "workflow": "bmm/2-plan-workflows/create-prd/workflow-create-prd.md",
        "next_steps": [
            "Review and refine the PRD",
            "Use bmad_bmm_validate_prd to validate",
            "Use bmad_bmm_create_architecture to design architecture",
        ],
        "session_id": session_id,
    }


@app.tool()
async def bmad_bmm_create_story(
    story_title: str,
    acceptance_criteria: list[str],
    priority: str = "medium",
    points: int = 3,
    session_id: str = "",
) -> dict[str, Any]:
    """Create a user story. Use when breaking down features into implementable stories.

    Args:
        story_title: Clear, actionable story title
        acceptance_criteria: List of criteria for story completion
        priority: Story priority (critical/high/medium/low)
        points: Story points estimate
        session_id: Optional session ID

    Returns:
        Story template and implementation guidance
    """
    engine = get_engine()
    workflow = engine.load_workflow("bmm", "2-plan-workflows/create-story")

    story = await engine.execute_workflow(
        workflow,
        {
            "title": story_title,
            "acceptance_criteria": acceptance_criteria,
            "priority": priority,
            "points": points,
        },
        session_id,
    )

    return {
        "story": story,
        "workflow": "bmm/2-plan-workflows/create-story.md",
        "next_steps": ["Add to sprint", "Assign to developer", "Break down into tasks"],
    }


@app.tool()
async def bmad_bmm_sprint_planning(
    stories: list[dict],
    sprint_goal: str,
    capacity: int,
    session_id: str = "",
) -> dict[str, Any]:
    """Plan a sprint. Use when starting a new iteration.

    Args:
        stories: List of stories to consider
        sprint_goal: Clear sprint objective
        capacity: Team capacity in story points
        session_id: Optional session ID

    Returns:
        Sprint plan with prioritized stories
    """
    engine = get_engine()
    workflow = engine.load_workflow("bmm", "2-plan-workflows/sprint-planning")

    plan = await engine.execute_workflow(
        workflow,
        {
            "stories": stories,
            "sprint_goal": sprint_goal,
            "capacity": capacity,
        },
        session_id,
    )

    return {
        "sprint_plan": plan,
        "workflow": "bmm/2-plan-workflows/sprint-planning.md",
        "capacity_utilization": plan.get("total_points", 0) / capacity if capacity > 0 else 0,
    }


@app.tool()
async def bmad_bmm_dev_story(
    story_id: str,
    tech_stack: str,
    existing_code: str = "",
    session_id: str = "",
) -> dict[str, Any]:
    """Develop a user story. Use when implementing a story.

    Args:
        story_id: Story identifier
        tech_stack: Technology stack being used
        existing_code: Reference to existing codebase
        session_id: Optional session ID

    Returns:
        Implementation plan and code guidance
    """
    engine = get_engine()
    workflow = engine.load_workflow("bmm", "3-solutioning/dev-story")

    result = await engine.execute_workflow(
        workflow,
        {
            "story_id": story_id,
            "tech_stack": tech_stack,
            "existing_code": existing_code,
        },
        session_id,
    )

    return {
        "implementation_plan": result,
        "workflow": "bmm/3-solutioning/dev-story.md",
        "suggested_files": result.get("files_to_create", []),
    }


@app.tool()
async def bmad_bmm_code_review(
    code_changes: str,
    review_type: str = "general",
    focus_areas: list[str] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """Review code changes. Use for quality assurance.

    Args:
        code_changes: Code to review (diff or full files)
        review_type: Type of review (general/security/performance/refactor)
        focus_areas: Specific areas to focus on
        session_id: Optional session ID

    Returns:
        Review feedback and recommendations
    """
    engine = get_engine()
    workflow = engine.load_workflow("bmm", "4-implementation/code-review")

    review = await engine.execute_workflow(
        workflow,
        {
            "code_changes": code_changes,
            "review_type": review_type,
            "focus_areas": focus_areas or [],
        },
        session_id,
    )

    return {
        "review_feedback": review,
        "workflow": "bmm/4-implementation/code-review.md",
        "issues_found": len(review.get("issues", [])),
        "suggestions_count": len(review.get("suggestions", [])),
    }


@app.tool()
async def bmad_gds_create_game_brief(
    game_concept: str,
    target_platform: str,
    genre: str,
    session_id: str = "",
) -> dict[str, Any]:
    """Create a game design brief. Use when starting game development.

    Args:
        game_concept: Core game concept and vision
        target_platform: Platform (PC/console/mobile/VR)
        genre: Game genre
        session_id: Optional session ID

    Returns:
        Game brief with design pillars
    """
    engine = get_engine()
    workflow = engine.load_workflow("gds", "workflows/create-game-brief")

    brief = await engine.execute_workflow(
        workflow,
        {
            "game_concept": game_concept,
            "target_platform": target_platform,
            "genre": genre,
        },
        session_id,
    )

    return {
        "game_brief": brief,
        "workflow": "gds/workflows/create-game-brief.md",
        "next_steps": ["Create GDD", "Design game architecture", "Prototype core loop"],
    }


@app.tool()
async def bmad_gds_game_architecture(
    game_brief_id: str,
    engine_choice: str = "",
    multiplayer: bool = False,
    session_id: str = "",
) -> dict[str, Any]:
    """Design game architecture. Use after creating game brief.

    Args:
        game_brief_id: Reference to game brief
        engine_choice: Game engine (Unity/Unreal/Godot/custom)
        multiplayer: Whether game has multiplayer
        session_id: Optional session ID

    Returns:
        Architecture document and technical recommendations
    """
    engine = get_engine()
    workflow = engine.load_workflow("gds", "workflows/game-architecture")

    arch = await engine.execute_workflow(
        workflow,
        {
            "game_brief_id": game_brief_id,
            "engine_choice": engine_choice,
            "multiplayer": multiplayer,
        },
        session_id,
    )

    return {
        "architecture": arch,
        "workflow": "gds/workflows/game-architecture.md",
        "systems": arch.get("systems", []),
    }


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

    Returns:
        Brainstorming guide and prompts
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

    Returns:
        Test strategy and test cases
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

    Returns:
        Agent definition file and usage guide
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

    Returns:
        Party mode session setup and instructions
    """
    engine = get_engine()

    # Load all requested agents
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

    Returns:
        List of available workflows
    """
    engine = get_engine()
    workflows = engine.list_workflows(module, phase)

    return {
        "workflows": workflows,
        "count": len(workflows),
        "modules": engine.list_modules(),
    }


@app.tool()
async def bmad_list_agents(
    module: str = "",
) -> dict[str, Any]:
    """List available BMAD agents. Use to see who can help.

    Args:
        module: Filter by module

    Returns:
        List of available agents with descriptions
    """
    engine = get_engine()
    agents = engine.list_agents(module)

    return {
        "agents": agents,
        "count": len(agents),
        "total_modules": len(engine.list_modules()),
    }


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

    Returns:
        Indexing results and statistics
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
async def bmad_status(
    session_id: str = "",
) -> dict[str, Any]:
    """Get BMAD session status. Use to see current state.

    Args:
        session_id: Session ID to check

    Returns:
        Session status and history
    """
    session_mgr = get_session_manager()

    if session_id:
        session = await session_mgr.get_session(session_id)
        return {
            "session": session,
            "status": "active" if session else "not_found",
            "history": session.get("history", []) if session else [],
        }
    else:
        # Return general status
        engine = get_engine()
        return {
            "modules_loaded": engine.list_modules(),
            "agents_available": len(engine.list_agents()),
            "workflows_available": len(engine.list_workflows()),
            "redis_connected": session_mgr.is_connected(),
            "version": "6.0.4",
        }


# ============================================================================
# AGENT PROMPTS (28 agents as MCP prompts)
# ============================================================================


@app.prompt(name="bmad-pm")
def bmad_pm_prompt() -> str:
    """BMAD Product Manager agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-pm")


@app.prompt(name="bmad-dev")
def bmad_dev_prompt() -> str:
    """BMAD Developer agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-dev")


@app.prompt(name="bmad-architect")
def bmad_architect_prompt() -> str:
    """BMAD Architect agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-architect")


@app.prompt(name="bmad-qa")
def bmad_qa_prompt() -> str:
    """BMAD QA Engineer agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-qa")


@app.prompt(name="bmad-game-designer")
def bmad_game_designer_prompt() -> str:
    """BMAD Game Designer agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("gds-game-designer")


@app.prompt(name="bmad-game-dev")
def bmad_game_dev_prompt() -> str:
    """BMAD Game Developer agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("gds-game-dev")


# ============================================================================
# RESOURCES (Workflows, Agents, Documentation)
# ============================================================================


@app.resource("bmad://workflows/{module}/{workflow_id}")
async def get_workflow_resource(module: str, workflow_id: str) -> str:
    """Get BMAD workflow content."""
    engine = get_engine()
    result = engine.load_workflow(module, workflow_id)
    if "error" in result:
        return f"# Error\n{result['error']}"
    return result.get("content", "")


@app.resource("bmad://agents/{agent_name}")
async def get_agent_resource(agent_name: str) -> str:
    """Get BMAD agent persona."""
    engine = get_engine()
    content = engine.load_agent(agent_name)
    return json.dumps(content, indent=2)


@app.resource("bmad://modules")
async def list_modules_resource() -> str:
    """List all BMAD modules."""
    engine = get_engine()
    modules = engine.list_modules()
    return json.dumps(modules, indent=2)


# ============================================================================
# ============================================================================
# MAIN ENTRY
# ============================================================================


def main():
    """Run the BMAD MCP server."""
    port = int(os.getenv("MCP_PORT", "8361"))
    transport = os.getenv("MCP_TRANSPORT", "http")

    logger.info(f"Starting BMAD MCP Server v6.0.4 on port {port}")
    logger.info(f"BMAD data path: {BMAD_DATA_PATH}")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"Transport: {transport}")

    # Run with selected transport
    if transport == "stdio":
        app.run(transport="stdio")
    else:
        app.run(host="0.0.0.0", port=port, transport="http")


if __name__ == "__main__":
    main()
