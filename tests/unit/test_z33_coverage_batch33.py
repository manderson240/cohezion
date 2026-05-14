"""Coverage batch Z33: skills_mcp, cohezion_environment, experience_pipeline, knowledge routes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: mcp/skills_server_mcp.py
# ---------------------------------------------------------------------------


class TestSkillsServerMcp:
    @pytest.fixture(autouse=True)
    def _mock_server(self):
        self.mock_server = MagicMock()
        self.mock_server.invoke_skill = MagicMock(return_value={"name": "CODE_REVIEW", "content": "..."})
        self.mock_server.register_skill = MagicMock(return_value={"id": "new_skill"})
        self.mock_server.search_skills = MagicMock(return_value=[{"name": "CODE_REVIEW"}])
        self.mock_server.list_all = MagicMock(return_value=[{"name": "CODE_REVIEW", "desc": "Review code"}])

        with patch("cohezion.mcp.skills_server_mcp.get_server", return_value=self.mock_server):
            yield

    def test_invoke_skill_calls_server(self):
        from cohezion.mcp.skills_server_mcp import invoke_skill

        result = asyncio.run(invoke_skill("CODE_REVIEW"))
        self.mock_server.invoke_skill.assert_called_once_with("CODE_REVIEW")
        assert result["name"] == "CODE_REVIEW"

    def test_register_skill_calls_server(self):
        from cohezion.mcp.skills_server_mcp import register_skill

        result = asyncio.run(register_skill("MY_SKILL", "desc", ["kw1"], "path/to/skill.md"))
        self.mock_server.register_skill.assert_called_once_with("MY_SKILL", "desc", ["kw1"], "path/to/skill.md")

    def test_search_skills_calls_server(self):
        from cohezion.mcp.skills_server_mcp import search_skills

        result = asyncio.run(search_skills("code review", limit=3))
        self.mock_server.search_skills.assert_called_once_with("code review", 3)
        assert len(result) == 1

    def test_list_all_skills_calls_server(self):
        from cohezion.mcp.skills_server_mcp import list_all_skills

        result = asyncio.run(list_all_skills())
        self.mock_server.list_all.assert_called_once()
        assert result[0]["name"] == "CODE_REVIEW"


# ---------------------------------------------------------------------------
# Module 2: integrations/agentverse/cohezion_environment.py
# ---------------------------------------------------------------------------


class TestCohezionEnvironment:
    def _make_env(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionEnvironment

        env = CohezionEnvironment(mcp_client=MagicMock(), executor=MagicMock())
        return env

    def test_init_sets_attributes(self):
        env = self._make_env()
        assert env.agents == []

    def test_reset_clears_agents(self):
        env = self._make_env()
        env.agents.append(MagicMock())
        env.reset()
        assert env.agents == []

    def test_step_raises_not_implemented(self):
        env = self._make_env()
        with pytest.raises(NotImplementedError):
            env.step()

    def test_get_context_returns_dict(self):
        env = self._make_env()
        ctx = env.get_context()
        assert ctx["status"] == "context_available"

    def test_simulation_env_init(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionSimulationEnvironment

        env = CohezionSimulationEnvironment(mcp_client=MagicMock(), executor=MagicMock())
        assert env.n_round == 0

    def test_simulation_env_reset(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionSimulationEnvironment

        env = CohezionSimulationEnvironment(mcp_client=MagicMock(), executor=MagicMock())
        env.n_round = 5
        env.agents.append(MagicMock())
        env.reset()
        assert env.n_round == 0
        assert env.agents == []

    def test_simulation_env_add_agent(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionSimulationEnvironment

        env = CohezionSimulationEnvironment(mcp_client=MagicMock(), executor=MagicMock())
        mock_agent = MagicMock()
        mock_agent.name = "agent-1"
        env.add_agent(mock_agent)
        assert len(env.agents) == 1

    def test_simulation_env_get_observation(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionSimulationEnvironment

        env = CohezionSimulationEnvironment(mcp_client=MagicMock(), executor=MagicMock())
        obs = env.get_observation()
        assert obs["n_agents"] == 0
        assert obs["n_round"] == 0

    def test_task_env_init(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionTaskSolvingEnvironment

        env = CohezionTaskSolvingEnvironment(
            mcp_client=MagicMock(), executor=MagicMock(), task_description="Solve X"
        )
        assert env.task_description == "Solve X"

    def test_task_env_is_multi_agent(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionTaskSolvingEnvironment

        env = CohezionTaskSolvingEnvironment(mcp_client=MagicMock(), executor=MagicMock(), task_description="T")
        assert env.is_multi_agent() is True

    def test_task_env_get_task(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionTaskSolvingEnvironment

        env = CohezionTaskSolvingEnvironment(
            mcp_client=MagicMock(), executor=MagicMock(), task_description="Optimize the loop"
        )
        assert env.get_task() == "Optimize the loop"

    def test_task_env_reset(self):
        from cohezion.integrations.agentverse.cohezion_environment import CohezionTaskSolvingEnvironment

        env = CohezionTaskSolvingEnvironment(mcp_client=MagicMock(), executor=MagicMock(), task_description="T")
        env.n_round = 3
        env.agents.append(MagicMock())
        env.reset()
        assert env.n_round == 0
        assert env.agents == []


# ---------------------------------------------------------------------------
# Module 3: flume/experience_pipeline.py
# ---------------------------------------------------------------------------


class TestExperienceTrainingPipeline:
    def test_generate_synthetic_count(self):
        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        records = ExperienceTrainingPipeline._generate_synthetic(5, seed=42)
        assert len(records) == 5

    def test_generate_synthetic_keys(self):
        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        records = ExperienceTrainingPipeline._generate_synthetic(1, seed=42)
        assert "trajectory" in records[0]
        assert "operation_type" in records[0]
        assert "phi_score" in records[0]

    def test_generate_synthetic_operation_types_cycle(self):
        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        records = ExperienceTrainingPipeline._generate_synthetic(10, seed=0)
        op_types = {r["operation_type"] for r in records}
        assert len(op_types) > 1  # cycles through multiple types

    def test_run_raises_when_insufficient_data_no_fallback(self):
        mock_collector = MagicMock()
        mock_collector.collect_all.return_value = []

        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        pipeline = ExperienceTrainingPipeline(collector=mock_collector)
        with pytest.raises(ValueError, match="synthetic_fallback"):
            asyncio.run(pipeline.run(min_real=10, synthetic_fallback=False))

    def test_run_synthetic_fallback_pads_data(self):
        mock_collector = MagicMock()
        mock_collector.collect_all.return_value = []  # 0 real samples

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=50)
        mock_dataset_cls = MagicMock(return_value=mock_dataset)

        mock_trainer = MagicMock()
        mock_trainer.train.return_value = [{"total": 0.5}]
        mock_trainer_cls = MagicMock(return_value=mock_trainer)

        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        with (
            patch("cohezion.flume.experience_pipeline.ExperienceDataset", mock_dataset_cls),
            patch("cohezion.flume.experience_pipeline.FlumeVAETrainer", mock_trainer_cls),
        ):
            pipeline = ExperienceTrainingPipeline(collector=mock_collector)
            result = asyncio.run(
                pipeline.run(min_real=5, max_samples=50, epochs=2, synthetic_fallback=True)
            )
        assert result == Path("data/flume/checkpoints/flume_vae_ep2.pt")
        # Dataset was created with padded synthetic data
        mock_dataset_cls.assert_called_once()

    def test_run_with_enough_real_data(self):
        mock_collector = MagicMock()
        real_records = [{"id": i} for i in range(20)]
        mock_collector.collect_all.return_value = real_records

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=20)
        mock_dataset_cls = MagicMock(return_value=mock_dataset)

        mock_trainer = MagicMock()
        mock_trainer.train.return_value = []  # empty metrics
        mock_trainer_cls = MagicMock(return_value=mock_trainer)

        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        with (
            patch("cohezion.flume.experience_pipeline.ExperienceDataset", mock_dataset_cls),
            patch("cohezion.flume.experience_pipeline.FlumeVAETrainer", mock_trainer_cls),
        ):
            pipeline = ExperienceTrainingPipeline(collector=mock_collector)
            result = asyncio.run(pipeline.run(min_real=5, epochs=3))
        assert result == Path("data/flume/checkpoints/flume_vae_ep3.pt")


# ---------------------------------------------------------------------------
# Module 4: api/routes/knowledge.py
# ---------------------------------------------------------------------------


class TestKnowledgeRoutes:
    @pytest.fixture(autouse=True)
    def _mock_knowledge_server(self):
        self.mock_server = MagicMock()
        self.mock_server.search_knowledge = MagicMock(return_value=[{"id": "doc1"}])
        self.mock_server.list_skills = MagicMock(return_value=["skill_a", "skill_b"])
        self.mock_server.get_skill = MagicMock(return_value={"name": "vault_keeper"})

        with patch("cohezion.api.routes.knowledge.get_knowledge_server", return_value=self.mock_server):
            yield

    def test_search_knowledge_calls_server(self):
        from cohezion.api.routes.knowledge import SearchRequest, search_knowledge

        req = SearchRequest(query="vault operations", limit=3)
        result = asyncio.run(search_knowledge(req))
        self.mock_server.search_knowledge.assert_called_once_with("vault operations", 3)
        assert len(result["results"]) == 1

    def test_list_skills_calls_server(self):
        from cohezion.api.routes.knowledge import list_skills

        result = asyncio.run(list_skills())
        assert "skill_a" in result["skills"]

    def test_get_skill_happy_path(self):
        from cohezion.api.routes.knowledge import get_skill

        result = asyncio.run(get_skill("vault_keeper"))
        assert result["name"] == "vault_keeper"

    def test_get_skill_raises_404_on_error_key(self):
        from fastapi import HTTPException

        from cohezion.api.routes.knowledge import get_skill

        self.mock_server.get_skill = MagicMock(return_value={"error": "Skill not found: xyz"})
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_skill("nonexistent"))
        assert exc_info.value.status_code == 404

    def test_knowledge_query_calls_engine(self):
        from cohezion.api.routes.knowledge import KnowledgeQueryRequest, knowledge_query

        mock_engine = MagicMock()
        mock_engine.search_knowledge.return_value = [{"id": "r1", "content": "relevant"}]

        with patch("cohezion.knowledge_graph.query_engine.KnowledgeGraphQueryEngine", return_value=mock_engine):
            req = KnowledgeQueryRequest(query="find X", top_k=3)
            result = asyncio.run(knowledge_query(req))
        assert result.query == "find X"
        assert result.count == 1
