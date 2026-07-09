"""Unit tests for CronManager — session-scoped cron job tracking."""

from __future__ import annotations

from cohezion.compound.cron_manager import STANDARD_JOBS, CronJob, CronManager


class TestCronManager:
    def test_empty_on_creation(self):
        cm = CronManager()
        assert len(cm) == 0

    def test_register_job(self):
        cm = CronManager()
        cm.register("abc123", "test-job", "A test job", "*/5 * * * *")
        assert len(cm) == 1

    def test_get_ids_returns_registered(self):
        cm = CronManager()
        cm.register("id-1", "job-1", "desc", "*/5 * * * *")
        cm.register("id-2", "job-2", "desc", "0 * * * *")
        ids = cm.get_ids()
        assert "id-1" in ids
        assert "id-2" in ids

    def test_cancel_removes_job(self):
        cm = CronManager()
        cm.register("id-x", "job-x", "desc", "*/1 * * * *")
        cm.cancel("id-x")
        assert len(cm) == 0

    def test_cancel_nonexistent_is_noop(self):
        cm = CronManager()
        cm.cancel("nonexistent")  # must not raise
        assert len(cm) == 0

    def test_cancel_all_returns_ids(self):
        cm = CronManager()
        cm.register("a", "job-a", "desc", "*/5 * * * *")
        cm.register("b", "job-b", "desc", "0 * * * *")
        ids = cm.cancel_all()
        assert set(ids) == {"a", "b"}
        assert len(cm) == 0

    def test_status_has_required_keys(self):
        cm = CronManager()
        cm.register("s1", "silicon-check", "Check NPU", "*/5 * * * *")
        status = cm.status()
        assert "active_jobs" in status
        assert "jobs" in status
        assert status["active_jobs"] == 1
        job = status["jobs"][0]
        assert job["id"] == "s1"
        assert job["name"] == "silicon-check"
        assert job["cron"] == "*/5 * * * *"

    def test_status_empty_engine(self):
        cm = CronManager()
        status = cm.status()
        assert status["active_jobs"] == 0
        assert status["jobs"] == []


class TestStandardJobs:
    def test_standard_jobs_have_required_fields(self):
        for job in STANDARD_JOBS:
            assert "name" in job
            assert "description" in job
            assert "cron" in job
            assert "prompt" in job

    def test_autoresearch_job_exists(self):
        names = [j["name"] for j in STANDARD_JOBS]
        assert "autoresearch-loop" in names

    def test_npu_liveness_job_exists(self):
        names = [j["name"] for j in STANDARD_JOBS]
        assert "npu-liveness" in names

    def test_cron_expressions_are_valid_format(self):
        """Basic cron format validation: 5 space-separated fields."""
        for job in STANDARD_JOBS:
            parts = job["cron"].split()
            assert len(parts) == 5, f"Invalid cron expression in {job['name']}: {job['cron']}"


class TestCronJob:
    def test_cron_job_has_timestamp(self):
        from cohezion.compound.cron_manager import CronJob

        job = CronJob("id", "name", "desc", "*/5 * * * *")
        assert job.created_at is not None

    def test_cron_job_fields(self):
        job = CronJob("my-id", "my-job", "my description", "0 8 * * *")
        assert job.job_id == "my-id"
        assert job.name == "my-job"
        assert job.cron_expression == "0 8 * * *"
