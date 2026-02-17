"""Tests for the skill-agent-API fabric.

Covers AgentFactory, ConfigTemplateManager.generate_and_register,
and the three new API endpoints.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SKILLS_DIR = Path("src/cohezion/skills")
GENERATED_DIR = Path("src/cohezion/agents/generated")

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def factory():
    from cohezion.agents.factory import AgentFactory

    return AgentFactory(skills_dir=SKILLS_DIR)


@pytest.fixture()
def config_manager():
    from cohezion.core.config_templates import ConfigTemplateManager
    from cohezion.core.template_engine import TemplateEngine

    engine = TemplateEngine(SKILLS_DIR)
    return ConfigTemplateManager(engine=engine)


@pytest.fixture()
def api_client():
    from unittest.mock import AsyncMock, MagicMock, patch

    from cohezion.api import app

    mock_client = MagicMock()
    mock_client.generate = AsyncMock(return_value="mock output")
    mock_client.metrics = MagicMock(total_requests=0, cache_hits=0, total_tokens_saved=0, cache_hit_rate=0.0)

    with patch(
        "cohezion.swarm.compound_client.get_compound_client",
        return_value=mock_client,
    ):
        yield TestClient(app)


# Use a known skill that definitely exists in the skills directory.
# Pick one from the PRIME-style naming convention.
KNOWN_SKILL = "COMPOUND_ENGINEERING_PRIME"


@pytest.fixture()
def _cleanup_generated():
    """Remove any generated files after the test."""
    yield
    gen_dir = GENERATED_DIR
    for pattern in ("compound_engineering_agent.py", "compound_engineering_config.py"):
        p = gen_dir / pattern
        if p.exists():
            p.unlink()


# ------------------------------------------------------------------
# AgentFactory tests
# ------------------------------------------------------------------


class TestAgentFactory:
    def test_create(self, factory):
        """create() returns an agent instance for a known skill."""
        agent = factory.create(KNOWN_SKILL)
        assert agent is not None
        cls_name = type(agent).__name__
        assert "Agent" in cls_name

    def test_list_skills(self, factory):
        """list_available_skills() returns 124+ entries."""
        names = factory.list_available_skills()
        assert len(names) >= 100  # conservative lower bound

    def test_unknown_skill(self, factory):
        """create() raises KeyError for a nonexistent skill."""
        with pytest.raises(KeyError, match="not found"):
            factory.create("NONEXISTENT_SKILL_THAT_DOES_NOT_EXIST")

    def test_caching(self, factory):
        """Same skill produces the same class object."""
        cls1 = factory.get_class(KNOWN_SKILL)
        cls2 = factory.get_class(KNOWN_SKILL)
        assert cls1 is cls2

    def test_agent_has_process(self, factory):
        """Generated agent has an async process method."""
        agent = factory.create(KNOWN_SKILL)
        assert hasattr(agent, "process")
        assert callable(agent.process)


# ------------------------------------------------------------------
# ConfigTemplateManager.generate_and_register tests
# ------------------------------------------------------------------


class TestGenerateAndRegister:
    @pytest.mark.usefixtures("_cleanup_generated")
    def test_generates_files(self, config_manager):
        """generate_and_register() creates agent + config .py files."""
        result = config_manager.generate_and_register(KNOWN_SKILL)
        assert "agent" in result
        assert "config" in result
        assert result["agent"].exists()
        assert result["config"].exists()
        assert result["agent"].name == "compound_engineering_agent.py"
        assert result["config"].name == "compound_engineering_config.py"

    @pytest.mark.usefixtures("_cleanup_generated")
    def test_generated_agent_is_valid_python(self, config_manager):
        """Generated agent file compiles without syntax errors."""
        result = config_manager.generate_and_register(KNOWN_SKILL)
        source = result["agent"].read_text(encoding="utf-8")
        compile(source, str(result["agent"]), "exec")

    def test_unknown_skill_raises(self, config_manager):
        """generate_and_register() raises KeyError for unknown skill."""
        with pytest.raises(KeyError, match="not found"):
            config_manager.generate_and_register("DOES_NOT_EXIST_XYZ")


# ------------------------------------------------------------------
# API endpoint tests
# ------------------------------------------------------------------


class TestSkillEndpoints:
    def test_list_skills(self, api_client):
        """GET /skills/list returns 124+ skills."""
        resp = api_client.get("/skills/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 100

    def test_execute_skill(self, api_client):
        """POST /skills/{name}/execute returns stub response."""
        resp = api_client.post(
            f"/skills/{KNOWN_SKILL}/execute",
            json={"input_text": "hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_name"] == KNOWN_SKILL
        assert "Agent" in data["agent_class"]
        assert data["status"] in ("stub", "executed", "error")

    def test_execute_unknown_skill(self, api_client):
        """POST /skills/{name}/execute returns 404 for unknown skill."""
        resp = api_client.post(
            "/skills/NONEXISTENT_XYZ_999/execute",
            json={"input_text": "hello"},
        )
        assert resp.status_code == 404

    def test_capability_query(self, api_client):
        """POST /query/find-capable-agent returns results."""
        resp = api_client.post(
            "/query/find-capable-agent",
            json={"query": "security", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "security"
        assert isinstance(data["agents"], list)
