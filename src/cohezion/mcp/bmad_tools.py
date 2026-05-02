"""BMAD MCP tools - core BMAD commands via FastMCP (v6.3.0 catalog-driven)."""

from __future__ import annotations

from typing import Any

from cohezion.mcp.bmad_app import app, get_engine, get_session_manager


@app.tool()
async def bmad_help(
    query: str = "",
    context: str = "",
    session_id: str = "",
) -> dict[str, Any]:
    """Interactive BMAD help system. Use when user asks 'what should I do next', 'bmad help', or needs guidance.

    Args:
        query: User's question or current situation (e.g. 'what should I do next', 'help with PRD')
        context: Current project context/state
        session_id: Optional session ID for continuity
    """
    engine = get_engine()
    session = await get_session_manager().get_session(session_id) if session_id else None
    analysis = engine.analyze_context(context, session)
    recommendations = engine.get_next_steps(query, analysis, session)
    return {
        "help_response": recommendations,
        "analysis": analysis,
        "available_modules": engine.list_modules(),
        "suggested_commands": recommendations.get("suggested_commands", []),
        "suggested_skills": recommendations.get("suggested_skills", []),
    }


@app.tool()
async def bmad_load_skill(
    skill_name: str,
) -> dict[str, Any]:
    """Load a BMAD skill's full content (SKILL.md + workflow + steps). Use to get detailed instructions for a skill.

    Args:
        skill_name: Skill identifier (e.g. 'bmad-create-prd', 'bmad-help', 'bmad-teach-me-testing')
    """
    engine = get_engine()
    result = engine.load_skill(skill_name)
    return {
        **result,
        "available_skills": [s["name"] for s in engine.list_skills()],
    }


@app.tool()
async def bmad_bmm_create_prd(
    product_idea: str,
    target_users: str,
    key_features: list[str],
    session_id: str = "",
    save_to_vault: bool = True,
) -> dict[str, Any]:
    """Create a Product Requirements Document (PRD). Use when starting a new product.

    Args:
        product_idea: Description of the product or feature
        target_users: Who will use this product
        key_features: List of key features/capabilities
        session_id: Optional session ID
        save_to_vault: Whether to save the PRD to vault
    """
    engine = get_engine()
    # Load the skill content so the agent can follow the workflow
    skill = engine.load_skill("bmad-create-prd")
    workflow = engine.load_workflow("bmm", "2-plan-workflows/create-prd/workflow-create-prd")
    prd_content = await engine.execute_workflow(
        workflow,
        {"product_idea": product_idea, "target_users": target_users, "key_features": key_features},
        session_id,
    )
    if session_id:
        await get_session_manager().update_session(
            session_id, {"last_action": "create_prd", "prd_created": True}
        )
    return {
        "prd_content": prd_content,
        "skill_instructions": skill.get("content", ""),
        "workflow_steps": skill.get("steps", []),
        "next_steps": [
            "Review and refine the PRD",
            "Invoke bmad_load_skill with skill_name='bmad-validate-prd' to validate",
            "Invoke bmad_load_skill with skill_name='bmad-create-architecture' to design architecture",
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
    """
    engine = get_engine()
    skill = engine.load_skill("bmad-create-story")
    workflow = engine.load_workflow("bmm", "4-implementation/create-story")
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
        "skill_instructions": skill.get("content", ""),
        "workflow_steps": skill.get("steps", []),
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
    """
    engine = get_engine()
    skill = engine.load_skill("bmad-sprint-planning")
    workflow = engine.load_workflow("bmm", "4-implementation/sprint-planning")
    plan = await engine.execute_workflow(
        workflow,
        {"stories": stories, "sprint_goal": sprint_goal, "capacity": capacity},
        session_id,
    )
    return {
        "sprint_plan": plan,
        "skill_instructions": skill.get("content", ""),
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
    """
    engine = get_engine()
    skill = engine.load_skill("bmad-dev-story")
    workflow = engine.load_workflow("bmm", "4-implementation/dev-story")
    result = await engine.execute_workflow(
        workflow,
        {"story_id": story_id, "tech_stack": tech_stack, "existing_code": existing_code},
        session_id,
    )
    return {
        "implementation_plan": result,
        "skill_instructions": skill.get("content", ""),
        "workflow_steps": skill.get("steps", []),
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
    """
    engine = get_engine()
    skill = engine.load_skill("bmad-code-review")
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
        "skill_instructions": skill.get("content", ""),
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
    """
    engine = get_engine()
    skill = (
        engine.load_skill("bmad-gds-create-game-brief")
        if "bmad-gds-create-game-brief" in engine._skills
        else engine.load_skill("bmad-gds-game-brief")
    )
    workflow = engine.load_workflow("gds", "workflows/create-game-brief")
    brief = await engine.execute_workflow(
        workflow,
        {"game_concept": game_concept, "target_platform": target_platform, "genre": genre},
        session_id,
    )
    return {
        "game_brief": brief,
        "skill_instructions": skill.get("content", ""),
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
        "systems": arch.get("systems", []),
    }
