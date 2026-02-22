"""Tests for Trigger.dev integration module.

Tests cover:
- TriggerConfig
- TriggerClient (with mocked HTTP)
- Task definitions and registry
- ScheduleManager
- Task runners (health, research, simulation, compound)
- API routes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.triggers.config import TriggerConfig
from cohezion.triggers.tasks import (
    TaskCategory,
    TaskDefinition,
    TaskPriority,
    get_scheduled_tasks,
    get_task_registry,
    get_tasks_by_category,
)


# ---------------------------------------------------------------------------
# TriggerConfig tests
# ---------------------------------------------------------------------------


class TestTriggerConfig:
    def test_default_config(self):
        config = TriggerConfig()
        assert config.api_url == "https://api.trigger.dev"
        assert config.default_queue == "cohezion-default"
        assert config.max_concurrent == 4

    def test_config_not_configured_without_key(self):
        config = TriggerConfig(secret_key="")
        assert not config.is_configured

    def test_config_is_configured_with_key(self):
        config = TriggerConfig(secret_key="tr_dev_test123")
        assert config.is_configured

    def test_headers(self):
        config = TriggerConfig(secret_key="tr_dev_test123")
        headers = config.headers
        assert headers["Authorization"] == "Bearer tr_dev_test123"
        assert headers["Content-Type"] == "application/json"

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("TRIGGER_SECRET_KEY", "tr_prod_envkey")
        monkeypatch.setenv("TRIGGER_API_URL", "https://custom.trigger.dev")
        monkeypatch.setenv("TRIGGER_PROJECT_REF", "my-project")
        config = TriggerConfig()
        assert config.secret_key == "tr_prod_envkey"
        assert config.api_url == "https://custom.trigger.dev"
        assert config.project_ref == "my-project"


# ---------------------------------------------------------------------------
# Task registry tests
# ---------------------------------------------------------------------------


class TestTaskRegistry:
    def test_registry_not_empty(self):
        registry = get_task_registry()
        assert len(registry) > 0

    def test_all_tasks_have_valid_category(self):
        registry = get_task_registry()
        for task_id, task_def in registry.items():
            assert isinstance(task_def.category, TaskCategory)

    def test_all_tasks_have_descriptions(self):
        registry = get_task_registry()
        for task_id, task_def in registry.items():
            assert task_def.description, f"{task_id} missing description"

    def test_scheduled_tasks_have_cron(self):
        scheduled = get_scheduled_tasks()
        for task_def in scheduled:
            assert task_def.cron is not None, f"{task_def.task_id} missing cron"

    def test_task_categories_filter(self):
        health_tasks = get_tasks_by_category(TaskCategory.HEALTH)
        assert len(health_tasks) > 0
        for t in health_tasks:
            assert t.category == TaskCategory.HEALTH

    def test_all_categories_have_tasks(self):
        for cat in TaskCategory:
            tasks = get_tasks_by_category(cat)
            assert len(tasks) > 0, f"No tasks for category {cat.value}"

    def test_task_ids_are_unique(self):
        registry = get_task_registry()
        task_ids = [t.task_id for t in registry.values()]
        assert len(task_ids) == len(set(task_ids))

    def test_queue_names(self):
        registry = get_task_registry()
        for task_def in registry.values():
            queue_name = task_def.queue_name
            assert queue_name.startswith("cohezion-")

    def test_health_test_suite_definition(self):
        registry = get_task_registry()
        assert "health/test-suite" in registry
        task = registry["health/test-suite"]
        assert task.cron == "0 */6 * * *"
        assert task.priority == TaskPriority.HIGH
        assert task.timeout_seconds == 600

    def test_simulation_pipeline_definition(self):
        registry = get_task_registry()
        assert "simulation/training-pipeline" in registry
        task = registry["simulation/training-pipeline"]
        assert task.cron == "0 0 * * 0"
        assert task.max_concurrent == 1
        assert task.timeout_seconds == 28800


# ---------------------------------------------------------------------------
# TriggerClient tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestTriggerClient:
    @pytest.fixture
    def client(self):
        from cohezion.triggers.client import TriggerClient

        config = TriggerConfig(
            api_url="https://test.trigger.dev",
            secret_key="tr_dev_test",
        )
        return TriggerClient(config)

    @pytest.mark.asyncio
    async def test_trigger_task(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "run_abc123"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            handle = await client.trigger("health/test-suite", {"scope": "tests/"})
            assert handle.id == "run_abc123"
            assert handle.task_id == "health/test-suite"

    @pytest.mark.asyncio
    async def test_trigger_with_options(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "run_xyz789"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            handle = await client.trigger(
                "simulation/mass-sim",
                {"scale": "demo"},
                idempotency_key="unique-key",
                delay="1h",
                tags=["manual"],
            )
            assert handle.id == "run_xyz789"

            # Verify the request body contained options
            call_args = mock_http.post.call_args
            body = call_args.kwargs.get("json", call_args[1].get("json", {}))
            assert "options" in body
            assert body["options"]["idempotencyKey"] == "unique-key"
            assert body["options"]["delay"] == "1h"

    @pytest.mark.asyncio
    async def test_get_run(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "run_abc123",
            "status": "COMPLETED",
            "startedAt": "2026-01-01T00:00:00Z",
            "finishedAt": "2026-01-01T00:05:00Z",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_response
            mock_get.return_value = mock_http

            status = await client.get_run("run_abc123")
            assert status.status == "COMPLETED"
            assert status.started_at == "2026-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_create_schedule(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "sched_123",
            "taskIdentifier": "health/test-suite",
            "cron": "0 */6 * * *",
            "active": True,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            handle = await client.create_schedule(
                "health/test-suite",
                "0 */6 * * *",
                deduplication_key="cohezion-health/test-suite",
            )
            assert handle.id == "sched_123"
            assert handle.cron == "0 */6 * * *"
            assert handle.active is True

    @pytest.mark.asyncio
    async def test_batch_trigger(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "runs": [{"id": "run_1"}, {"id": "run_2"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            handles = await client.batch_trigger(
                "health/metrics-snapshot",
                [{"scope": "cpu"}, {"scope": "memory"}],
            )
            assert len(handles) == 2
            assert handles[0].id == "run_1"


# ---------------------------------------------------------------------------
# ScheduleManager tests
# ---------------------------------------------------------------------------


class TestScheduleManager:
    @pytest.mark.asyncio
    async def test_sync_all(self):
        from cohezion.triggers.scheduler import ScheduleManager
        from cohezion.triggers.client import TriggerClient, ScheduleHandle

        client = TriggerClient(
            TriggerConfig(secret_key="tr_dev_test", api_url="https://test.trigger.dev")
        )

        # Mock create_schedule to return handles
        async def mock_create_schedule(task_id, cron, **kwargs):
            return ScheduleHandle(id=f"sched_{task_id}", task_id=task_id, cron=cron)

        client.create_schedule = AsyncMock(side_effect=mock_create_schedule)

        manager = ScheduleManager(client)
        results = await manager.sync_all()

        scheduled_count = len(get_scheduled_tasks())
        assert len(results) == scheduled_count

    @pytest.mark.asyncio
    async def test_trigger_now(self):
        from cohezion.triggers.scheduler import ScheduleManager
        from cohezion.triggers.client import TriggerClient, RunHandle

        client = TriggerClient(
            TriggerConfig(secret_key="tr_dev_test", api_url="https://test.trigger.dev")
        )

        async def mock_trigger(task_id, payload=None, **kwargs):
            return RunHandle(id="run_manual_123", task_id=task_id)

        client.trigger = AsyncMock(side_effect=mock_trigger)

        manager = ScheduleManager(client)
        run_id = await manager.trigger_now("health/test-suite", {"scope": "tests/"})
        assert run_id == "run_manual_123"


# ---------------------------------------------------------------------------
# Health runner tests
# ---------------------------------------------------------------------------


class TestHealthRunners:
    def test_run_metrics_snapshot(self):
        from cohezion.triggers.runners.health import run_metrics_snapshot

        result = run_metrics_snapshot()
        assert result.task_id == "health/metrics-snapshot"
        assert result.status == "success"
        assert "cpu_percent" in result.metrics
        assert "memory_used_gb" in result.metrics
        assert "disk_free_gb" in result.metrics

    def test_run_repo_hygiene(self):
        from cohezion.triggers.runners.health import run_repo_hygiene

        result = run_repo_hygiene()
        assert result.task_id == "health/repo-hygiene"
        assert result.status in ("success", "warning")
        assert "uncommitted_files" in result.metrics

    def test_run_degradation_check(self):
        from cohezion.triggers.runners.health import run_degradation_check

        result = run_degradation_check()
        assert result.task_id == "health/degradation-check"
        # May be "warning" if DegradationDetector not fully set up
        assert result.status in ("success", "warning", "failure")

    @patch("subprocess.run")
    def test_run_test_suite_parses_output(self, mock_subprocess):
        from cohezion.triggers.runners.health import run_test_suite

        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="3200 passed, 4 failed, 2 warnings in 90.5s\n",
            stderr="",
        )

        result = run_test_suite()
        assert result.task_id == "health/test-suite"
        assert result.metrics["passed"] == 3200
        assert result.metrics["failed"] == 4

    @patch("subprocess.run")
    def test_run_test_suite_timeout(self, mock_subprocess):
        import subprocess as sp

        from cohezion.triggers.runners.health import run_test_suite

        mock_subprocess.side_effect = sp.TimeoutExpired(cmd="pytest", timeout=540)

        result = run_test_suite()
        assert result.status == "failure"
        assert any("timed out" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Research runner tests
# ---------------------------------------------------------------------------


class TestResearchRunners:
    def test_run_model_scout(self):
        from cohezion.triggers.runners.research import run_model_scout

        with patch("cohezion.triggers.runners.research.shutil") as mock_shutil:
            mock_shutil.disk_usage.return_value = (
                1000 * 1024**3,
                500 * 1024**3,
                500 * 1024**3,
            )
            result = run_model_scout()

        assert result.task_id == "research/model-scout"
        assert result.status == "success"
        assert "storage_free_gb" in result.metrics

    def test_run_experiment_analysis(self):
        from cohezion.triggers.runners.research import run_experiment_analysis

        result = run_experiment_analysis()
        assert result.task_id == "research/experiment-analysis"
        assert result.status == "success"


# ---------------------------------------------------------------------------
# Simulation runner tests
# ---------------------------------------------------------------------------


class TestSimulationRunners:
    @patch("subprocess.run")
    def test_run_mass_sim(self, mock_subprocess):
        from cohezion.triggers.runners.simulation import run_mass_sim

        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Simulation complete\n",
            stderr="",
        )

        result = run_mass_sim({"scale": "demo"})
        assert result.task_id == "simulation/mass-sim"
        assert result.metrics["scale"] == "demo"

    @patch("subprocess.run")
    def test_run_training_pipeline_success(self, mock_subprocess):
        from cohezion.triggers.runners.simulation import run_training_pipeline

        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="[STEP 1/9] Complete\n[STEP 2/9] Complete\n",
            stderr="",
        )

        result = run_training_pipeline({"scale": "demo"})
        assert result.task_id == "simulation/training-pipeline"
        assert result.metrics["scale"] == "demo"

    def test_run_universe_bridge(self):
        from cohezion.triggers.runners.simulation import run_universe_bridge

        result = run_universe_bridge()
        assert result.task_id == "simulation/universe-bridge"
        # May fail if no checkpoint exists, which is expected
        assert result.status in ("success", "warning", "failure")


# ---------------------------------------------------------------------------
# Compound runner tests
# ---------------------------------------------------------------------------


class TestCompoundRunners:
    def test_run_vault_compile(self):
        from cohezion.triggers.runners.compound import run_vault_compile

        result = run_vault_compile()
        assert result.task_id == "compound/vault-compile"
        # May warn if script not found
        assert result.status in ("success", "warning")

    def test_run_journey_audit(self):
        from cohezion.triggers.runners.compound import run_journey_audit

        result = run_journey_audit()
        assert result.task_id == "compound/journey-audit"
        assert result.status in ("success", "warning", "failure")

    def test_run_retrospection(self):
        from cohezion.triggers.runners.compound import run_retrospection

        result = run_retrospection()
        assert result.task_id == "compound/retrospection"
        assert result.status in ("success", "warning")

    def test_run_skill_refinement_dry_run(self):
        from cohezion.triggers.runners.compound import run_skill_refinement

        result = run_skill_refinement({"dry_run": True})
        assert result.task_id == "compound/skill-refinement"
        assert result.metrics.get("dry_run") is True


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class TestTriggerRoutes:
    @pytest.fixture
    def test_client(self):
        from fastapi.testclient import TestClient
        from cohezion.api import app

        return TestClient(app)

    def test_list_tasks(self, test_client):
        resp = test_client.get("/triggers/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert data["total"] > 0

    def test_list_tasks_by_category(self, test_client):
        resp = test_client.get("/triggers/tasks?category=health")
        assert resp.status_code == 200
        data = resp.json()
        for task in data["tasks"]:
            assert task["category"] == "health"

    def test_list_tasks_invalid_category(self, test_client):
        resp = test_client.get("/triggers/tasks?category=invalid")
        assert resp.status_code == 400

    def test_get_config(self, test_client):
        resp = test_client.get("/triggers/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "total_tasks" in data
        assert "categories" in data

    def test_trigger_unconfigured(self, test_client):
        """Triggering without TRIGGER_SECRET_KEY returns 503."""
        resp = test_client.post(
            "/triggers/trigger",
            json={"task_id": "health/test-suite"},
        )
        assert resp.status_code == 503

    def test_trigger_unknown_task(self, test_client):
        """Triggering an unknown task returns 404."""
        # Patch config to appear configured
        with patch(
            "cohezion.api.trigger_routes.TriggerConfig"
        ) as MockConfig:
            mock_config = MagicMock()
            mock_config.is_configured = True
            mock_config.secret_key = "tr_dev_test"
            MockConfig.return_value = mock_config

            resp = test_client.post(
                "/triggers/trigger",
                json={"task_id": "nonexistent/task"},
            )
            assert resp.status_code == 404
