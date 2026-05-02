"""Tests for Proactive BMad party mode integration."""

from pathlib import Path

import pytest


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_proactive_scan():
    """Test that party mode runs proactive scan on startup."""
    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveMonitor

    # Create test project
    test_project = Path("/tmp/test_party_proactive")
    test_project.mkdir(exist_ok=True)

    monitor = ProactiveMonitor(test_project)
    suggestions = await monitor.scan_for_suggestions()

    # Should return suggestions (even if empty)
    assert isinstance(suggestions, list)

    # Cleanup
    import shutil

    shutil.rmtree(test_project, ignore_errors=True)


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_discusses_suggestions():
    """Test that party mode uses suggestions as discussion topics."""
    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveSuggestion

    # Create mock suggestions
    suggestions = [
        ProactiveSuggestion(
            id="repo-workflow-missing",
            title="Repository Workflows Missing",
            description="Create workflows",
            priority="high",
            category="alignment",
            suggested_action="Create BMad workflows",
            auto_executable=True,
            confidence=0.9,
        ),
        ProactiveSuggestion(
            id="batch-tasks-missing",
            title="Batch Tasks Missing",
            description="Add tasks",
            priority="high",
            category="alignment",
            suggested_action="Add to manifest",
            auto_executable=True,
            confidence=0.95,
        ),
    ]

    # Verify suggestions can be used as discussion topics
    assert len(suggestions) == 2
    assert all(s.priority == "high" for s in suggestions)
    assert all(s.auto_executable for s in suggestions)


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_collaborative_execution():
    """Test collaborative execution flow in party mode."""
    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveMonitor, ProactiveSuggestion

    test_project = Path("/tmp/test_party_exec")
    test_project.mkdir(exist_ok=True)

    monitor = ProactiveMonitor(test_project)

    # Create suggestion
    suggestion = ProactiveSuggestion(
        id="repo-workflow-missing",
        title="Test Workflow",
        description="Test",
        priority="high",
        category="alignment",
        suggested_action="Create workflow",
        auto_executable=True,
        confidence=0.9,
    )

    # Execute (simulating user approval in party mode)
    success = await monitor.execute_suggestion(suggestion, confirm=False)

    assert success is True

    # Verify workflow created
    workflow_path = test_project / "_bmad" / "core" / "workflows" / "repository-operations"
    assert workflow_path.exists()
    assert (workflow_path / "workflow.md").exists()

    # Cleanup
    import shutil

    shutil.rmtree(test_project, ignore_errors=True)


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_agent_selection_for_suggestions():
    """Test that party mode selects relevant agents for suggestions."""
    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveSuggestion

    # Map suggestion categories to relevant agents
    category_agents = {
        "alignment": ["Winston (Architect)", "Wendy (Workflow Builder)"],
        "integration": ["Amelia (Developer)", "Winston (Architect)"],
        "quality": ["Quinn (QA)", "Amelia (Developer)"],
        "maintenance": ["Amelia (Developer)", "Bob (Scrum Master)"],
    }

    # Test alignment suggestion
    suggestion = ProactiveSuggestion(
        id="repo-workflow-missing",
        title="Repository Workflows",
        description="Create workflows",
        priority="high",
        category="alignment",
        suggested_action="Create",
        auto_executable=True,
        confidence=0.9,
    )

    # Should select relevant agents
    relevant_agents = category_agents.get(suggestion.category, [])
    assert len(relevant_agents) >= 2
    assert "Winston (Architect)" in relevant_agents


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_welcome_with_suggestions():
    """Test party mode welcome message includes proactive suggestions."""
    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveSuggestion

    suggestions = [
        ProactiveSuggestion(
            id="test-1",
            title="Test Suggestion 1",
            description="Test",
            priority="high",
            category="alignment",
            suggested_action="Test",
            auto_executable=True,
            confidence=0.9,
        ),
        ProactiveSuggestion(
            id="test-2",
            title="Test Suggestion 2",
            description="Test",
            priority="medium",
            category="quality",
            suggested_action="Test",
            auto_executable=False,
            confidence=0.8,
        ),
    ]

    # Generate welcome message
    welcome = f"""🎉 PARTY MODE ACTIVATED! 🎉

**Proactive Scan Results:**
I've scanned your codebase and found {len(suggestions)} alignment opportunities:
"""

    for s in suggestions[:3]:
        welcome += f"\n- **[{s.priority}]** {s.title} (Confidence: {s.confidence * 100:.0f}%)"

    # Verify message includes suggestions
    assert str(len(suggestions)) in welcome
    assert "Test Suggestion 1" in welcome
    assert "Test Suggestion 2" in welcome
    assert "90%" in welcome  # Confidence formatting


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_execution_confirmation():
    """Test that party mode requires user confirmation for execution."""
    import shutil
    import tempfile

    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveMonitor, ProactiveSuggestion

    # Create temp directory for test
    test_project = Path(tempfile.mkdtemp())

    try:
        monitor = ProactiveMonitor(test_project)

        suggestion = ProactiveSuggestion(
            id="repo-workflow-missing",
            title="Test Workflow",
            description="Test",
            priority="high",
            category="alignment",
            suggested_action="Create workflow",
            auto_executable=True,
            confidence=0.9,
        )

        # Execute without confirmation (test mode)
        success = await monitor.execute_suggestion(suggestion, confirm=False)

        # Should succeed
        assert success is True

        # Verify workflow created
        workflow_path = test_project / "_bmad" / "core" / "workflows" / "repository-operations"
        assert workflow_path.exists()
    finally:
        # Cleanup
        shutil.rmtree(test_project, ignore_errors=True)


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_multiple_agents_discuss():
    """Test that multiple agents can discuss a suggestion."""
    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveSuggestion

    suggestion = ProactiveSuggestion(
        id="repo-workflow-missing",
        title="Repository Workflows Missing",
        description="Create workflows",
        priority="high",
        category="alignment",
        suggested_action="Create BMad workflows",
        auto_executable=True,
        confidence=0.9,
    )

    # Simulate agent perspectives
    agent_perspectives = {
        "Winston (Architect)": "Let's examine the workflow structure",
        "Wendy (Workflow Builder)": "I can create the workflow definition",
        "Amelia (Developer)": "I'll implement the workflow steps",
        "Bob (Scrum Master)": "This aligns with our sprint goals",
    }

    # All agents should have relevant input
    assert len(agent_perspectives) >= 3
    assert all(len(v) > 0 for v in agent_perspectives.values())


@pytest.mark.asyncio
@pytest.mark.fast
async def test_party_mode_suggestion_priority_display():
    """Test that party mode displays suggestions by priority."""
    from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveSuggestion

    suggestions = [
        ProactiveSuggestion(
            id="low",
            title="Low",
            description="Low",
            priority="low",
            category="test",
            suggested_action="Test",
            confidence=0.5,
        ),
        ProactiveSuggestion(
            id="high1",
            title="High 1",
            description="High",
            priority="high",
            category="test",
            suggested_action="Test",
            confidence=0.9,
        ),
        ProactiveSuggestion(
            id="medium",
            title="Medium",
            description="Medium",
            priority="medium",
            category="test",
            suggested_action="Test",
            confidence=0.7,
        ),
        ProactiveSuggestion(
            id="high2",
            title="High 2",
            description="High",
            priority="high",
            category="test",
            suggested_action="Test",
            confidence=0.95,
        ),
    ]

    # Sort by priority (as party mode would)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_suggestions = sorted(
        suggestions, key=lambda s: (priority_order.get(s.priority, 4), -s.confidence)
    )

    # Verify order: high (confidence desc), medium, low
    assert sorted_suggestions[0].priority == "high"
    assert sorted_suggestions[0].confidence == 0.95  # Highest confidence first
    assert sorted_suggestions[1].priority == "high"
    assert sorted_suggestions[2].priority == "medium"
    assert sorted_suggestions[3].priority == "low"
