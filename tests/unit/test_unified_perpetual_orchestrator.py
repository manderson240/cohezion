"""Unit tests for Cohezion Unified 24/7 Perpetual Orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.autopoiesis.tri_silicon_engine import TriSiliconCycleResult
from cohezion.inference.dynamic_model_evaluator import ModelEvaluationScorecard
from cohezion.ops.control_plane import (
    HardwareTelemetry,
    OperationsSnapshot,
    ProjectTelemetry,
    SoftwareTelemetry,
)
from cohezion.ops.unified_perpetual_orchestrator import (
    MasterCycleOutcome,
    PhaseResult,
    UnifiedPerpetualLoopDaemon,
)
from cohezion.reliability.oom_guard import MemoryState


@pytest.fixture
def mock_daemon():
    daemon = UnifiedPerpetualLoopDaemon(interval_seconds=1.0, cpu_threads=2)
    return daemon


@pytest.mark.asyncio
async def test_run_autopoiesis_phase(mock_daemon):
    mock_tri_res = TriSiliconCycleResult(
        cycle=1,
        npu_guidance="High-leverage focus",
        npu_model="llama3.2-1b-FLM",
        npu_latency_ms=120.0,
        cpu_arc_programs_found=1,
        cpu_kaggriculture_win_rate=0.85,
        cpu_sheaf_converged=True,
        cpu_latency_ms=80.0,
        igpu_synthesis_triggered=False,
        delta_entropy=-0.5848,
        autoharness_verified=True,
        total_latency_ms=200.0,
        details={"reward": 1.0},
    )
    with (
        patch.object(mock_daemon.tri_silicon_engine, "execute_cycle", return_value=mock_tri_res),
        patch.object(mock_daemon.event_bus, "publish", new_callable=AsyncMock) as mock_pub,
    ):
        res = await mock_daemon.run_autopoiesis_phase(cycle_num=1)
        assert res.success is True
        assert res.phase_name == "autopoiesis"
        assert "NPU guidance" in res.summary
        mock_pub.assert_called_once()


@pytest.mark.asyncio
async def test_run_kaggle_compute_phase(mock_daemon):
    mock_prog = MagicMock()
    with (
        patch.object(mock_daemon.dsl_engine, "solve_single_task", return_value=(mock_prog, [])),
        patch.object(
            mock_daemon.control_plane.projects,
            "get_kaggle_tracks",
            return_value=[{"competition": "arc-prize-2026-arc-agi-2", "status": "COMPLETE"}],
        ),
    ):
        res = await mock_daemon.run_kaggle_compute_phase(cycle_num=1)
        assert res.success is True
        assert res.phase_name == "kaggle_compute"
        assert res.details["programs_found"] == 1


@pytest.mark.asyncio
async def test_run_actioner_phase(mock_daemon, tmp_path):
    with (
        patch.object(
            mock_daemon.control_plane.projects,
            "get_kanban_summary",
            return_value={"approved": 0, "completed": 5},
        ),
    ):
        res = await mock_daemon.run_actioner_phase(cycle_num=1)
        assert res.success is True
        assert res.phase_name == "actioner_queue"
        assert "No approved items waiting" in res.summary


@pytest.mark.asyncio
async def test_run_model_eval_phase(mock_daemon):
    mock_scorecard = ModelEvaluationScorecard(
        model="Bonsai-8B-gguf",
        task_id="calibration_cycle_1",
        syntax_valid=True,
        test_pass_rate=1.0,
        quality_score=1.0,
        latency_ms=1200.0,
        tokens_per_second=45.0,
        hardware_lane="iGPU",
        evi_score=0.0,
        escalation_required=False,
    )
    with patch.object(mock_daemon.evaluator, "evaluate_model_on_task", return_value=mock_scorecard):
        res = await mock_daemon.run_model_eval_phase(cycle_num=1)
        assert res.success is True
        assert res.phase_name == "model_eval"
        assert "Bonsai-8B-gguf" in res.summary


@pytest.mark.asyncio
async def test_run_sentry_phase(mock_daemon):
    mock_snapshot = OperationsSnapshot(
        timestamp="2026-09-08T12:00:00Z",
        overall_status="HEALTHY",
        hardware=HardwareTelemetry(
            available_ram_gb=45.0,
            total_ram_gb=128.0,
            dynamic_floor_gb=20.0,
            gtt_used_gb=15.0,
            gtt_total_gb=96.0,
            swap_used_gb=0.0,
            psi_memory_avg10=0.0,
            is_memory_safe=True,
            cpu_cores_logical=32,
            cpu_cores_physical=16,
            load_avg_1m=1.0,
            load_avg_5m=1.0,
            status="HEALTHY",
        ),
        software=SoftwareTelemetry(
            lemonade_online=True,
            lemonade_models_loaded=["llama3.2-1b-FLM"],
            ollama_online=True,
            ollama_models_loaded=[],
            surrealdb_online=True,
            systemd_services={},
            git_index_file_count=1000,
            git_index_healthy=True,
            obsidian_vault_accessible=True,
            status="HEALTHY",
        ),
        projects=ProjectTelemetry(
            active_kaggle_tracks=[],
            kanban_summary={},
            autopoiesis_cycle=1,
            autopoiesis_target_cycles=240,
            autopoiesis_last_reward=1.0,
            autopoiesis_last_delta_s=-0.5848,
            autopoiesis_converged=True,
            status="HEALTHY",
        ),
        diagnostics=[],
    )
    with (
        patch.object(mock_daemon.control_plane, "snapshot", return_value=mock_snapshot),
        patch.object(
            mock_daemon.control_plane,
            "persist_snapshot",
            return_value={"surreal": True, "vault": True},
        ),
    ):
        res = await mock_daemon.run_sentry_phase(cycle_num=1)
        assert res.success is True
        assert res.phase_name == "control_sentry"
        assert "Surreal: True" in res.summary


@pytest.mark.asyncio
async def test_run_trace_refactor_phase(mock_daemon):
    with patch("scripts.ops.refactor_traces_to_goals.fetch_recent_traces", return_value=[]):
        res = await mock_daemon.run_trace_refactor_phase(cycle_num=1)
        assert res.success is True
        assert res.phase_name == "trace_goal_refactor"
        assert "Refactored traces into goals" in res.summary


@pytest.mark.asyncio
async def test_run_trace_refactor_phase_commits_memory_as_plans(mock_daemon):
    fake_traces = [
        {
            "type": "SECURITY_VIOLATION",
            "source": "sentry",
            "payload": {"finding": "untrusted input", "severity": "high"},
        },
    ]
    with (
        patch(
            "scripts.ops.refactor_traces_to_goals.fetch_recent_traces",
            side_effect=[fake_traces, []],
        ),
        patch(
            "cohezion.flume.loop_goal_refactor_engine.DurableSurrealGoalPersistence.persist_goal",
            return_value="goal:1",
        ),
        patch(
            "cohezion.flume.loop_goal_refactor_engine.DurableSurrealGoalPersistence.persist_loop_result",
            return_value="loop_trace:1",
        ),
    ):
        res = await mock_daemon.run_trace_refactor_phase(cycle_num=1)
        assert res.success is True
        assert res.details["goals_processed"] == 1
        assert res.details["loops_converged"] == 1
        assert res.details["segments_committed"] >= 1
        assert len(mock_daemon.memory_as_plans.segments) >= 1
        assert "O(1) context digest" in res.summary


@pytest.mark.asyncio
async def test_execute_master_cycle(mock_daemon):
    mock_mem = MemoryState(
        available_gb=40.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        is_safe=True,
        dynamic_floor_gb=20.0,
        gtt_used_gb=20.0,
        gtt_total_gb=96.0,
        psi_some_10=0.0,
    )
    with (
        patch("cohezion.reliability.oom_guard.OOMGuard.get_memory_state", return_value=mock_mem),
        patch.object(
            mock_daemon,
            "run_autopoiesis_phase",
            return_value=PhaseResult("autopoiesis", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_kaggle_compute_phase",
            return_value=PhaseResult("kaggle_compute", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_actioner_phase",
            return_value=PhaseResult("actioner_queue", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_model_eval_phase",
            return_value=PhaseResult("model_eval", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_trace_refactor_phase",
            return_value=PhaseResult("trace_goal_refactor", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_sentry_phase",
            return_value=PhaseResult("control_sentry", True, 10.0, "OK"),
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        outcome = await mock_daemon.execute_master_cycle(cycle_num=1)
        assert isinstance(outcome, MasterCycleOutcome)
        assert outcome.cycle_id == 1
        assert outcome.success is True
        assert len(outcome.phases) == 6


@pytest.mark.asyncio
async def test_run_forever_max_cycles(mock_daemon):
    with (
        patch.object(
            mock_daemon, "execute_master_cycle", return_value=MagicMock(success=True)
        ) as mock_exec,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        await mock_daemon.run_forever(max_cycles=1)
        assert mock_exec.call_count == 1
