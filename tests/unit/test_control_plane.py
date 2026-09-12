"""Unit tests for Cohezion Unified Operations Control Plane."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from cohezion.ops.control_plane import (
    CohezionControlPlane,
    HardwareOrchestrator,
    HardwareTelemetry,
    OperationsSnapshot,
    ProjectOrchestrator,
    ProjectTelemetry,
    SoftwareOrchestrator,
    SoftwareTelemetry,
)
from cohezion.reliability.oom_guard import MemoryState


def test_hardware_orchestrator_healthy():
    mock_mem = MemoryState(
        available_gb=40.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        is_safe=True,
        dynamic_floor_gb=20.0,
        gtt_used_gb=25.0,
        gtt_total_gb=96.0,
        psi_some_10=0.0,
    )
    with patch("cohezion.reliability.oom_guard.OOMGuard.get_memory_state", return_value=mock_mem):
        hw = HardwareOrchestrator.get_telemetry()
        assert hw.status == "HEALTHY"
        assert hw.available_ram_gb == 40.0
        assert hw.gtt_used_gb == 25.0
        assert hw.is_memory_safe is True
        assert hw.to_dict()["status"] == "HEALTHY"


def test_hardware_orchestrator_degraded():
    mock_mem = MemoryState(
        available_gb=21.0,  # Below 24.0 threshold
        total_gb=128.0,
        swap_used_gb=0.0,
        is_safe=True,
        dynamic_floor_gb=20.0,
        gtt_used_gb=43.0,  # Above 42.0 threshold
        gtt_total_gb=96.0,
        psi_some_10=6.0,
    )
    with patch("cohezion.reliability.oom_guard.OOMGuard.get_memory_state", return_value=mock_mem):
        hw = HardwareOrchestrator.get_telemetry()
        assert hw.status == "DEGRADED"


def test_software_orchestrator_telemetry(tmp_path: Path):
    models_payload = json.dumps({"data": [{"id": "llama3.2-1b-FLM"}, {"id": "Bonsai-8B-gguf"}]})
    ollama_payload = json.dumps({"models": [{"name": "qwen3.5:397b-cloud"}]})

    def mock_endpoint(url: str, timeout: float = 2.0):
        if "13305" in url:
            return True, models_payload
        if "11434" in url:
            return True, ollama_payload
        if "8001" in url:
            return True, "SurrealDB 3.2.3"
        return False, "Not found"

    mock_git_res = MagicMock(stdout="\n".join([f"file_{i}.py" for i in range(500)]))

    with (
        patch.object(SoftwareOrchestrator, "_check_http_endpoint", side_effect=mock_endpoint),
        patch("subprocess.run", return_value=mock_git_res),
    ):
        sw = SoftwareOrchestrator.get_telemetry()
        assert sw.lemonade_online is True
        assert "Bonsai-8B-gguf" in sw.lemonade_models_loaded
        assert sw.ollama_online is True
        assert "qwen3.5:397b-cloud" in sw.ollama_models_loaded
        assert sw.surrealdb_online is True
        assert sw.git_index_healthy is True
        assert sw.to_dict()["lemonade_online"] is True


def test_project_orchestrator_telemetry(tmp_path: Path):
    work_queue_file = tmp_path / "work-queue.json"
    work_queue_data = {
        "items": [
            {"id": "t1", "status": "approved"},
            {"id": "t2", "status": "in_progress"},
            {"id": "t3", "status": "completed"},
        ]
    }
    work_queue_file.write_text(json.dumps(work_queue_data))

    autopoiesis_log = tmp_path / "autopoiesis.log"
    autopoiesis_log.write_text(
        "2026-09-08 11:49:41 | INFO | --- [Cycle 4/240] Launching Goal Loop ---\n"
        "2026-09-08 11:49:48 | INFO | Cycle 4 Executed: Converged=True, Reward=1.0000, Delta S=-0.5848 (Negentropy OK=True)\n"
    )

    with (
        patch("cohezion.ops.control_plane.WORK_QUEUE_PATH", work_queue_file),
        patch("cohezion.ops.control_plane.AUTOPOIESIS_LOG_PATH", autopoiesis_log),
        patch.object(
            ProjectOrchestrator,
            "get_kaggle_tracks",
            return_value=[
                {
                    "competition": "rsna-knee",
                    "latest_ref": "56100850",
                    "status": "PENDING",
                    "public_score": "N/A",
                }
            ],
        ),
    ):
        proj = ProjectOrchestrator.get_telemetry()
        assert proj.status == "HEALTHY"
        assert proj.autopoiesis_cycle == 4
        assert proj.autopoiesis_last_delta_s == -0.5848
        assert proj.autopoiesis_converged is True
        assert proj.kanban_summary["approved"] == 1
        assert proj.kanban_summary["in_progress"] == 1
        assert len(proj.active_kaggle_tracks) == 1


def test_control_plane_snapshot_and_diagnostics():
    cp = CohezionControlPlane()

    hw = HardwareTelemetry(
        available_ram_gb=35.0,
        total_ram_gb=128.0,
        dynamic_floor_gb=20.0,
        gtt_used_gb=20.0,
        gtt_total_gb=96.0,
        swap_used_gb=0.0,
        psi_memory_avg10=0.0,
        is_memory_safe=True,
        cpu_cores_logical=32,
        cpu_cores_physical=16,
        load_avg_1m=1.2,
        load_avg_5m=1.5,
        status="HEALTHY",
    )

    sw = SoftwareTelemetry(
        lemonade_online=True,
        lemonade_models_loaded=["llama3.2-1b-FLM"],
        ollama_online=True,
        ollama_models_loaded=["deepseek-v4-pro:cloud"],
        surrealdb_online=True,
        systemd_services={"cohezion-actioner.service": "active"},
        git_index_file_count=1200,
        git_index_healthy=True,
        obsidian_vault_accessible=True,
        status="HEALTHY",
    )

    proj = ProjectTelemetry(
        active_kaggle_tracks=[{"competition": "arc-prize", "status": "COMPLETE"}],
        kanban_summary={"approved": 2},
        autopoiesis_cycle=5,
        autopoiesis_target_cycles=240,
        autopoiesis_last_reward=1.0,
        autopoiesis_last_delta_s=-0.5848,
        autopoiesis_converged=True,
        status="HEALTHY",
    )

    diagnostics = cp.run_diagnostics(hw, sw, proj)
    assert all(d.passed for d in diagnostics)

    with (
        patch.object(cp.hardware, "get_telemetry", return_value=hw),
        patch.object(cp.software, "get_telemetry", return_value=sw),
        patch.object(cp.projects, "get_telemetry", return_value=proj),
    ):
        snap = cp.snapshot()
        assert snap.overall_status == "HEALTHY"
        assert snap.hardware.available_ram_gb == 35.0
        assert len(snap.diagnostics) == 7


def test_control_plane_persistence_fail_open(tmp_path: Path):
    cp = CohezionControlPlane()
    vault_dir = tmp_path / "cohezion-vault"

    snap = OperationsSnapshot(
        timestamp="2026-09-08T12:00:00Z",
        overall_status="HEALTHY",
        hardware=HardwareTelemetry(
            available_ram_gb=40.0,
            total_ram_gb=128.0,
            dynamic_floor_gb=20.0,
            gtt_used_gb=20.0,
            gtt_total_gb=96.0,
            swap_used_gb=0.0,
            psi_memory_avg10=0.0,
            is_memory_safe=True,
            cpu_cores_logical=32,
            cpu_cores_physical=16,
            load_avg_1m=0.5,
            load_avg_5m=0.5,
            status="HEALTHY",
        ),
        software=SoftwareTelemetry(
            lemonade_online=True,
            lemonade_models_loaded=["llama3.2-1b-FLM"],
            ollama_online=True,
            ollama_models_loaded=[],
            surrealdb_online=True,
            systemd_services={},
            git_index_file_count=500,
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
            autopoiesis_last_delta_s=-0.5,
            autopoiesis_converged=True,
            status="HEALTHY",
        ),
        diagnostics=[],
    )

    # Mock urllib for SurrealDB to fail, but vault should succeed
    with (
        patch("cohezion.ops.control_plane.OBSIDIAN_VAULT_DIR", vault_dir),
        patch("urllib.request.urlopen", side_effect=Exception("Connection refused")),
    ):
        res = cp.persist_snapshot(snap)
        assert res["surreal"] is False
        assert res["vault"] is True
        written_file = vault_dir / "ops" / "latest_control_plane.md"
        assert written_file.exists()
        assert "Cohezion Operations Snapshot" in written_file.read_text()
