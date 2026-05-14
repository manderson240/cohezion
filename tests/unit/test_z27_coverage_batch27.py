"""Coverage batch Z27: skill_acquisition, huggingface_export, viz_bridge, adversarial_reviewer, surreal_logger."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: learning/skill_acquisition.py
# ---------------------------------------------------------------------------


class TestDynamicSkillAcquisition:
    def test_acquire_skill_creates_file(self, tmp_path):
        from cohezion.learning.skill_acquisition import DynamicSkillAcquisition, SkillRegistryRequest

        dsa = DynamicSkillAcquisition(registry_dir=str(tmp_path))
        req = SkillRegistryRequest(skill_id="my-skill")
        result = asyncio.run(dsa.acquire_skill(req))
        assert result is True
        assert (tmp_path / "MY-SKILL_PRIME.md").exists()

    def test_acquire_skill_file_content(self, tmp_path):
        from cohezion.learning.skill_acquisition import DynamicSkillAcquisition, SkillRegistryRequest

        dsa = DynamicSkillAcquisition(registry_dir=str(tmp_path))
        asyncio.run(dsa.acquire_skill(SkillRegistryRequest(skill_id="demo")))
        content = (tmp_path / "DEMO_PRIME.md").read_text()
        assert "DEMO" in content
        assert "v1.0 (Auto-acquired)" in content

    def test_acquire_skill_returns_false_on_error(self, tmp_path):
        from cohezion.learning.skill_acquisition import DynamicSkillAcquisition, SkillRegistryRequest

        dsa = DynamicSkillAcquisition(registry_dir=str(tmp_path))
        # Make the path unwritable by pointing to a file, not a dir
        bad_path = tmp_path / "not-a-dir.txt"
        bad_path.write_text("blocker")
        dsa.registry_dir = bad_path  # can't write inside a file
        result = asyncio.run(dsa.acquire_skill(SkillRegistryRequest(skill_id="fail")))
        assert result is False

    def test_list_acquired_skills(self, tmp_path):
        from cohezion.learning.skill_acquisition import DynamicSkillAcquisition, SkillRegistryRequest

        dsa = DynamicSkillAcquisition(registry_dir=str(tmp_path))
        asyncio.run(dsa.acquire_skill(SkillRegistryRequest(skill_id="alpha")))
        asyncio.run(dsa.acquire_skill(SkillRegistryRequest(skill_id="beta")))
        skills = dsa.list_acquired_skills()
        assert len(skills) == 2
        assert "ALPHA_PRIME" in skills

    def test_list_acquired_skills_empty_when_none(self, tmp_path):
        from cohezion.learning.skill_acquisition import DynamicSkillAcquisition

        dsa = DynamicSkillAcquisition(registry_dir=str(tmp_path))
        skills = dsa.list_acquired_skills()
        assert skills == []

    def test_skill_registry_request_model(self):
        from cohezion.learning.skill_acquisition import SkillRegistryRequest

        req = SkillRegistryRequest(skill_id="my_skill", source_url="https://example.com/skill")
        assert req.skill_id == "my_skill"
        assert req.source_url == "https://example.com/skill"

    def test_skill_registry_request_source_url_optional(self):
        from cohezion.learning.skill_acquisition import SkillRegistryRequest

        req = SkillRegistryRequest(skill_id="minimal")
        assert req.source_url is None


# ---------------------------------------------------------------------------
# Module 2: eval/huggingface_export.py
# ---------------------------------------------------------------------------


class TestHuggingFaceExporter:
    def test_export_research_dataset_creates_jsonl(self, tmp_path):
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exp = HuggingFaceExporter()
        evos = [{"journey_id": "j1", "coherence_amplitude": 0.8}]
        asyncio.run(exp.export_research_dataset(evos, tmp_path))
        assert (tmp_path / "data.jsonl").exists()

    def test_export_research_dataset_creates_readme(self, tmp_path):
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exp = HuggingFaceExporter()
        asyncio.run(exp.export_research_dataset([], tmp_path))
        assert (tmp_path / "README.md").exists()

    def test_export_research_dataset_jsonl_content(self, tmp_path):
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exp = HuggingFaceExporter()
        evos = [{"journey_id": "j1"}, {"journey_id": "j2"}]
        asyncio.run(exp.export_research_dataset(evos, tmp_path))
        lines = (tmp_path / "data.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["journey_id"] == "j1"

    def test_generate_dataset_card_includes_count(self):
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exp = HuggingFaceExporter()
        card = exp._generate_dataset_card(42)
        assert "42" in card

    def test_generate_dataset_card_is_yaml_fronted_markdown(self):
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exp = HuggingFaceExporter()
        card = exp._generate_dataset_card(5)
        assert card.startswith("---")
        assert "license: apache-2.0" in card

    def test_export_benchmark_harness_creates_file(self, tmp_path):
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exp = HuggingFaceExporter()
        asyncio.run(exp.export_benchmark_harness(tmp_path))
        assert (tmp_path / "benchmark.py").exists()

    def test_generate_benchmark_harness_returns_string(self):
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exp = HuggingFaceExporter()
        code = exp._generate_benchmark_harness()
        assert isinstance(code, str)
        assert "EVOTask" in code


# ---------------------------------------------------------------------------
# Module 3: universe/viz_bridge.py
# ---------------------------------------------------------------------------


def _make_journey(tmp_path):
    """Build a mock UniverseJourney with 2 trajectory points."""
    journey = MagicMock()
    journey.id = "journey-xyz"
    journey.agent_name = "test-agent"

    def make_pt(step, action, coherence, spin):
        pt = MagicMock()
        pt.step_number = step
        pt.action_taken = action
        pt.coherence = coherence
        pt.timestamp = 1700000000.0 + step
        pt.axiomatic = MagicMock(
            logic=0.8, novelty=0.3, precipitation=0.7,
            temporal=0.5, physics=0.6, spin_coherence=spin,
        )
        return pt

    journey.trajectory = [
        make_pt(1, "analyze the problem thoroughly", 0.9, 0.9),
        make_pt(2, "implement the solution carefully", 0.7, 0.6),
    ]
    return journey


class TestVisualizationBridge:
    def test_project_journey_returns_nodes_and_edges(self, tmp_path):
        from cohezion.universe.viz_bridge import VisualizationBridge

        vb = VisualizationBridge(str(tmp_path / ".obsidian/data.json"))
        data = vb.project_journey(_make_journey(tmp_path))
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_project_journey_node_id_format(self, tmp_path):
        from cohezion.universe.viz_bridge import VisualizationBridge

        vb = VisualizationBridge(str(tmp_path / ".obsidian/data.json"))
        data = vb.project_journey(_make_journey(tmp_path))
        assert data["nodes"][0]["id"] == "journey-xyz_step_1"

    def test_project_journey_edge_source_target(self, tmp_path):
        from cohezion.universe.viz_bridge import VisualizationBridge

        vb = VisualizationBridge(str(tmp_path / ".obsidian/data.json"))
        data = vb.project_journey(_make_journey(tmp_path))
        edge = data["edges"][0]
        assert edge["source"] == "journey-xyz_step_1"
        assert edge["target"] == "journey-xyz_step_2"

    def test_project_journey_is_bridging_flag(self, tmp_path):
        from cohezion.universe.viz_bridge import VisualizationBridge

        vb = VisualizationBridge(str(tmp_path / ".obsidian/data.json"))
        data = vb.project_journey(_make_journey(tmp_path))
        # spin_coherence=0.9 > 0.8 → is_bridging=True for first node
        assert data["nodes"][0]["is_bridging"] is True
        # spin_coherence=0.6 < 0.8 → is_bridging=False for second node
        assert data["nodes"][1]["is_bridging"] is False

    def test_project_journey_meta_counts(self, tmp_path):
        from cohezion.universe.viz_bridge import VisualizationBridge

        vb = VisualizationBridge(str(tmp_path / ".obsidian/data.json"))
        data = vb.project_journey(_make_journey(tmp_path))
        assert data["meta"]["nodes_count"] == 2
        assert data["meta"]["edges_count"] == 1

    def test_export_journey_writes_json_file(self, tmp_path):
        from cohezion.universe.viz_bridge import VisualizationBridge

        output_path = tmp_path / ".obsidian" / "3d-graph-data.json"
        vb = VisualizationBridge(str(output_path))
        vb.export_journey(_make_journey(tmp_path))
        assert output_path.exists()
        loaded = json.loads(output_path.read_text())
        assert loaded["meta"]["nodes_count"] == 2

    def test_project_journey_single_node_no_edges(self, tmp_path):
        from cohezion.universe.viz_bridge import VisualizationBridge

        vb = VisualizationBridge(str(tmp_path / ".obsidian/data.json"))
        journey = MagicMock()
        journey.id = "single"
        journey.agent_name = "agent"
        pt = MagicMock()
        pt.step_number = 1
        pt.action_taken = "start"
        pt.coherence = 0.5
        pt.timestamp = 1700000000.0
        pt.axiomatic = MagicMock(logic=0.5, novelty=0.5, precipitation=0.5, temporal=0.5, physics=0.5, spin_coherence=0.5)
        journey.trajectory = [pt]
        data = vb.project_journey(journey)
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 0


# ---------------------------------------------------------------------------
# Module 4: compound/tdd_adversarial/adversarial_reviewer.py
# ---------------------------------------------------------------------------


class TestAdversarialReviewer:
    def test_adversarial_critique_model(self):
        from cohezion.compound.tdd_adversarial.adversarial_reviewer import AdversarialCritique

        c = AdversarialCritique(
            is_contradictory=True, coherence_gap=0.7, leakage_detected=False, critique="Found a hole"
        )
        assert c.is_contradictory is True
        assert c.coherence_gap == pytest.approx(0.7)
        assert c.leakage_detected is False

    def test_adversarial_critique_false_values(self):
        from cohezion.compound.tdd_adversarial.adversarial_reviewer import AdversarialCritique

        c = AdversarialCritique(is_contradictory=False, coherence_gap=0.0, leakage_detected=False, critique="OK")
        assert c.is_contradictory is False
        assert c.coherence_gap == pytest.approx(0.0)

    def test_stress_test_parses_contradiction_true(self):
        from cohezion.compound.tdd_adversarial.adversarial_reviewer import AdversarialRedTeamAgent

        class ConcreteAgent(AdversarialRedTeamAgent):
            async def process(self, *args, **kwargs):
                pass

        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "[CONTRADICTION: True] [GAP: 0.75] [LEAKAGE: False] [CRITIQUE: Hole found]"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        with patch("cohezion.agents.base.asyncio.create_task", MagicMock()):
            agent = ConcreteAgent(provider=mock_provider, model_name="test-model")
        result = asyncio.run(agent.stress_test("strategy", [0.1, 0.2], ["TEK"]))
        assert result.is_contradictory is True
        assert result.coherence_gap == pytest.approx(0.75)
        assert result.leakage_detected is False

    def test_stress_test_parses_leakage_true(self):
        from cohezion.compound.tdd_adversarial.adversarial_reviewer import AdversarialRedTeamAgent

        class ConcreteAgent(AdversarialRedTeamAgent):
            async def process(self, *args, **kwargs):
                pass

        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "[CONTRADICTION: False] [GAP: 0.20] [LEAKAGE: True] [CRITIQUE: Leaked]"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        with patch("cohezion.agents.base.asyncio.create_task", MagicMock()):
            agent = ConcreteAgent(provider=mock_provider, model_name="test-model")
        result = asyncio.run(agent.stress_test("strategy", None, []))
        assert result.leakage_detected is True
        assert result.is_contradictory is False

    def test_stress_test_no_gap_defaults_to_half(self):
        from cohezion.compound.tdd_adversarial.adversarial_reviewer import AdversarialRedTeamAgent

        class ConcreteAgent(AdversarialRedTeamAgent):
            async def process(self, *args, **kwargs):
                pass

        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "No structured output here"
        mock_provider.generate = AsyncMock(return_value=mock_response)

        with patch("cohezion.agents.base.asyncio.create_task", MagicMock()):
            agent = ConcreteAgent(provider=mock_provider, model_name="test-model")
        result = asyncio.run(agent.stress_test("strategy", None, []))
        assert result.coherence_gap == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Module 5: persistence/surreal_logger.py
# ---------------------------------------------------------------------------


class TestSurrealTrajectoryLogger:
    def test_init_default_values(self):
        from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger

        logger = SurrealTrajectoryLogger()
        assert logger.url == "ws://localhost:8001/rpc"
        assert logger.namespace == "cohezion"
        assert logger.database == "core"

    def test_init_custom_values(self):
        from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger

        logger = SurrealTrajectoryLogger(url="ws://other:8002/rpc", namespace="test_ns", database="test_db")
        assert logger.url == "ws://other:8002/rpc"
        assert logger.namespace == "test_ns"

    def test_log_trajectory_happy_path(self):
        from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger

        mock_db = AsyncMock()
        mock_db.use = AsyncMock()
        mock_db.signin = AsyncMock()
        mock_db.create = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        mock_state = MagicMock()
        mock_state.doer.tolist.return_value = [0.1, 0.2]
        mock_state.thinker.tolist.return_value = [0.3, 0.4]
        mock_state.knower.tolist.return_value = [0.5, 0.6]

        with patch("cohezion.persistence.surreal_logger.AsyncSurreal", return_value=mock_db):
            logger = SurrealTrajectoryLogger()
            asyncio.run(logger.log_trajectory("traj-1", mock_state, 0.85))

        mock_db.create.assert_awaited_once()
        call_args = mock_db.create.call_args
        assert call_args[0][0] == "trajectory"
        assert call_args[0][1]["coherence"] == pytest.approx(0.85)
        assert call_args[0][1]["trajectory_id"] == "traj-1"

    def test_log_trajectory_raises_on_db_error(self):
        from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger

        mock_db = AsyncMock()
        mock_db.use = AsyncMock()
        mock_db.signin = AsyncMock()
        mock_db.create = AsyncMock(side_effect=RuntimeError("DB down"))
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        mock_state = MagicMock()
        mock_state.doer.tolist.return_value = []
        mock_state.thinker.tolist.return_value = []
        mock_state.knower.tolist.return_value = []

        with patch("cohezion.persistence.surreal_logger.AsyncSurreal", return_value=mock_db):
            logger = SurrealTrajectoryLogger()
            with pytest.raises(RuntimeError, match="DB down"):
                asyncio.run(logger.log_trajectory("traj-fail", mock_state, 0.5))
