"""Coverage batch Z35: protoclr, resilience_loop, mcp_http_server, mcp_skill_tools."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Module 1: audio/protoclr.py
# ---------------------------------------------------------------------------


class TestProtoCLR:
    def test_compute_prototypes_shape(self):
        from cohezion.audio.protoclr import ProtoCLR

        model = ProtoCLR()
        features = torch.randn(6, 16)
        labels = torch.tensor([0, 0, 1, 1, 2, 2])
        protos, unique = model.compute_prototypes(features, labels)
        assert protos.shape == (3, 16)
        assert len(unique) == 3

    def test_compute_prototypes_mean(self):
        from cohezion.audio.protoclr import ProtoCLR

        model = ProtoCLR()
        features = torch.tensor([[1.0, 0.0], [3.0, 0.0]])
        labels = torch.tensor([0, 0])
        protos, _ = model.compute_prototypes(features, labels)
        # Mean of [1,0] and [3,0] → [2,0]
        assert protos[0][0].item() == pytest.approx(2.0)

    def test_forward_returns_scalar_loss(self):
        from cohezion.audio.protoclr import ProtoCLR

        model = ProtoCLR(temperature=0.1)
        features = torch.tensor([[1.0, 0.0], [1.0, 0.1], [0.0, 1.0], [0.1, 1.0]])
        labels = torch.tensor([0, 0, 1, 1])
        loss = model(features, labels)
        assert loss.ndim == 0  # scalar
        assert loss.item() >= 0.0

    def test_forward_normalizes_features(self):
        from cohezion.audio.protoclr import ProtoCLR

        model = ProtoCLR()
        # Unnormalized features — should still produce valid loss
        features = torch.tensor([[10.0, 0.0], [0.0, 10.0]])
        labels = torch.tensor([0, 1])
        loss = model(features, labels)
        assert not torch.isnan(loss)

    def test_temperature_affects_loss(self):
        from cohezion.audio.protoclr import ProtoCLR

        features = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        labels = torch.tensor([0, 1])
        loss_high_temp = ProtoCLR(temperature=1.0)(features, labels)
        loss_low_temp = ProtoCLR(temperature=0.01)(features, labels)
        # Low temperature → higher logit sharpness → should differ
        assert loss_high_temp.item() != loss_low_temp.item()

    def test_domain_invariance_harness_train_step(self):
        from cohezion.audio.protoclr import DomainInvarianceHarness

        class TinyEncoder(nn.Module):
            def forward(self, x):
                return x

        model = TinyEncoder()
        optimizer = MagicMock()
        optimizer.zero_grad = MagicMock()
        optimizer.step = MagicMock()

        harness = DomainInvarianceHarness(model=model, optimizer=optimizer)

        focal_batch = {"audio": torch.tensor([[1.0, 0.0]]), "label": torch.tensor([0])}
        passive_batch = {"audio": torch.tensor([[0.0, 1.0]]), "label": torch.tensor([1])}

        with patch.object(torch.Tensor, "backward"):
            _loss = harness.train_step(focal_batch, passive_batch)

        optimizer.zero_grad.assert_called_once()
        optimizer.step.assert_called_once()


# ---------------------------------------------------------------------------
# Module 2: compound/resilience_loop.py
# ---------------------------------------------------------------------------


class TestEcoResilienceCompoundLoop:
    def _make_loop(self):
        from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop

        mock_agent = MagicMock()
        mock_agent.execute_cycle = AsyncMock(return_value="synthesize water conservation")
        mock_agent.translator = MagicMock()
        mock_agent.translator.encoder = MagicMock()
        mock_agent.translator.encoder.encode = MagicMock(return_value="encoded")
        mock_proj = MagicMock()
        mock_proj.coherence = 0.75
        mock_agent.translator.project.return_value = mock_proj

        mock_executor = MagicMock()

        mock_guard = MagicMock()
        mock_check = MagicMock()
        mock_check.coherence = 0.75
        mock_check.suggestion = ""
        mock_guard.verify = AsyncMock(return_value=mock_check)
        mock_guard.should_refine = MagicMock(return_value=False)  # stable immediately

        return (
            EcoResilienceCompoundLoop(mock_agent, mock_executor, mock_guard),
            mock_agent,
            mock_guard,
        )

    def test_resilience_execution_result_model(self):
        from cohezion.compound.resilience_loop import ResilienceExecutionResult

        r = ResilienceExecutionResult(
            final_strategy="save water",
            stability_score=0.9,
            is_stable=True,
            iterations=1,
            trace_id="t1",
        )
        assert r.final_strategy == "save water"
        assert r.is_stable is True

    def test_run_stable_exits_on_stable_check(self):
        loop, _, mock_guard = self._make_loop()
        result = asyncio.run(loop.run_stable_simulation("analyze biome", max_retries=3))
        assert result.is_stable is True
        assert result.iterations == 1

    def test_run_stable_benchmark_mode_limits_to_one(self):
        loop, mock_agent, _ = self._make_loop()
        result = asyncio.run(loop.run_stable_simulation("test", max_retries=5, benchmark_mode=True))
        # benchmark_mode forces 1 iteration even with max_retries=5
        assert result.iterations == 1

    def test_run_stable_exhausts_retries_returns_unstable(self):
        from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop

        mock_agent = MagicMock()
        mock_agent.execute_cycle = AsyncMock(return_value="strategy")
        mock_proj = MagicMock()
        mock_proj.coherence = 0.3
        mock_agent.translator = MagicMock()
        mock_agent.translator.encoder.encode.return_value = "enc"
        mock_agent.translator.project.return_value = mock_proj

        mock_guard = MagicMock()
        mock_check = MagicMock()
        mock_check.coherence = 0.3
        mock_check.suggestion = "try again"
        mock_guard.verify = AsyncMock(return_value=mock_check)
        mock_guard.should_refine.return_value = True  # always refine

        loop = EcoResilienceCompoundLoop(mock_agent, MagicMock(), mock_guard)

        with patch("cohezion.compound.resilience_loop.asyncio.sleep", AsyncMock()):
            result = asyncio.run(loop.run_stable_simulation("input", max_retries=2))
        assert result.is_stable is False
        assert result.iterations == 2

    def test_get_resilience_loop_singleton(self):
        import cohezion.compound.resilience_loop as module
        from cohezion.compound.resilience_loop import get_resilience_loop

        module._loop_instance = None
        loop1 = get_resilience_loop(MagicMock(), MagicMock(), MagicMock())
        loop2 = get_resilience_loop(MagicMock(), MagicMock(), MagicMock())
        assert loop1 is loop2
        module._loop_instance = None  # cleanup


# ---------------------------------------------------------------------------
# Module 3: gateway/mcp_http_server.py
# ---------------------------------------------------------------------------


class TestMcpHttpServer:
    def test_health_endpoint_returns_ok(self):
        from cohezion.gateway.mcp_http_server import health

        mock_request = MagicMock()
        response = asyncio.run(health(mock_request))
        assert response.media_type == "text/plain"

    def test_tools_endpoint_returns_tools_list(self):
        from cohezion.gateway.mcp_http_server import tools

        mock_tool = MagicMock()
        mock_tool.name = "my_tool"
        mock_tool.description = "does stuff"
        mock_tool.inputSchema = {}

        with patch("cohezion.gateway.mcp_http_server.mcp_server") as mock_server:
            mock_server.list_tools = AsyncMock(return_value=[mock_tool])
            mock_request = MagicMock()
            response = asyncio.run(tools(mock_request))
        assert response.media_type == "text/event-stream"

    def test_main_calls_uvicorn_run(self):
        from cohezion.gateway.mcp_http_server import main

        with (
            patch("cohezion.gateway.mcp_http_server.uvicorn.run") as mock_uvicorn,
            patch.dict("os.environ", {"MCP_PORT": "6000", "MCP_HOST": "127.0.0.1"}),
        ):
            main()
        mock_uvicorn.assert_called_once()
        _, kwargs = mock_uvicorn.call_args
        assert kwargs.get("port") == 6000


# ---------------------------------------------------------------------------
# Module 4: skills/mcp_skill_tools.py
# ---------------------------------------------------------------------------


class TestMcpSkillTools:
    def test_execute_skill_not_found(self):
        from cohezion.skills.mcp_skill_tools import execute_skill

        result = execute_skill("UNKNOWN_SKILL", {}, {})
        text = result["content"][0]["text"]
        assert "not found" in text.lower()

    def test_execute_skill_missing_path(self):
        from cohezion.skills.mcp_skill_tools import execute_skill

        skills = {"MY_SKILL": {}}  # no path key
        result = execute_skill("MY_SKILL", {}, skills)
        text = result["content"][0]["text"]
        assert "path missing" in text.lower()

    def test_execute_skill_file_not_found(self):
        from cohezion.skills.mcp_skill_tools import execute_skill

        skills = {"MY_SKILL": {"path": "nonexistent/skill.md"}}
        with patch("cohezion.skills.mcp_skill_tools.cohezion_root", return_value="/fake"):
            result = execute_skill("MY_SKILL", {}, skills)
        text = result["content"][0]["text"]
        assert "not found" in text.lower()

    def test_execute_skill_reads_file(self, tmp_path):
        from cohezion.skills.mcp_skill_tools import execute_skill

        skill_file = tmp_path / "my_skill.md"
        skill_file.write_text("# Skill Content\nDo stuff.")
        skills = {"MY_SKILL": {"path": "my_skill.md"}}

        with patch("cohezion.skills.mcp_skill_tools.cohezion_root", return_value=str(tmp_path)):
            result = execute_skill("MY_SKILL", {}, skills)
        assert "Skill Content" in result["content"][0]["text"]

    def test_execute_skill_handles_read_error(self, tmp_path):
        from cohezion.skills.mcp_skill_tools import execute_skill

        # A directory looks like an existing path but can't be read as a file
        skill_dir = tmp_path / "skill_dir"
        skill_dir.mkdir()
        skills = {"MY_SKILL": {"path": "skill_dir"}}

        with patch("cohezion.skills.mcp_skill_tools.cohezion_root", return_value=str(tmp_path)):
            result = execute_skill("MY_SKILL", {}, skills)
        # Should return error message, not raise
        text = result["content"][0]["text"]
        assert "Error" in text

    def test_get_truth_anchors_returns_context(self):
        from cohezion.skills.mcp_skill_tools import get_truth_anchors

        with patch(
            "cohezion.reliability.residency_awareness.ResidencyAnchorBase.get_context_block"
        ) as mock_ctx:
            mock_ctx.return_value = "Hardware: AMD Ryzen AI MAX+"
            result = get_truth_anchors({})
        assert "AMD Ryzen AI MAX+" in result["content"][0]["text"]

    def test_remember_fact_calls_memory_manager(self):
        import sys

        from cohezion.skills.mcp_skill_tools import remember_fact

        mock_mgr = MagicMock()
        mock_mgr.add.return_value = {"id": "fact123"}
        mock_mgr_cls = MagicMock(return_value=mock_mgr)
        mock_module = MagicMock(MemoryManager=mock_mgr_cls)

        with patch.dict(sys.modules, {"cohezion.reliability.memory_manager": mock_module}):
            result = remember_fact({"fact": "Python is awesome", "category": "tech"})
        assert "remembered" in result["content"][0]["text"].lower()

    def test_recall_context_calls_memory_manager(self):
        import sys

        from cohezion.skills.mcp_skill_tools import recall_context

        mock_mgr = MagicMock()
        mock_mgr.search.return_value = [{"content": "Python tip"}]
        mock_mgr_cls = MagicMock(return_value=mock_mgr)
        mock_module = MagicMock(MemoryManager=mock_mgr_cls)

        with patch.dict(sys.modules, {"cohezion.reliability.memory_manager": mock_module}):
            result = recall_context({"query": "Python", "limit": 3})
        text = result["content"][0]["text"]
        assert "Python tip" in text

    def test_daily_scout_research_calls_scout(self):
        import sys

        from cohezion.skills.mcp_skill_tools import daily_scout_research

        mock_scout = MagicMock()
        mock_scout.perform_research.return_value = ["proposal1"]
        mock_scout.filter_proposals.return_value = ["filtered1"]
        mock_scout_cls = MagicMock(return_value=mock_scout)
        mock_daily_module = MagicMock(DailyScoutAgent=mock_scout_cls)

        with patch.dict(sys.modules, {"cohezion.agents.daily_scout": mock_daily_module}):
            result = daily_scout_research({})
        text = result["content"][0]["text"]
        assert "filtered1" in text
