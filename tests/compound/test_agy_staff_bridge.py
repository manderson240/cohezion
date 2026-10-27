"""Unit tests for AgyStaffBridge delegation."""

import os
import tempfile
from pathlib import Path

from cohezion.compound.agy_staff_bridge import (
    AgyStaffBridge,
    JobExitCode,
    StaffPersona,
)


def test_dispatch_and_wait_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = AgyStaffBridge(state_dir=Path(tmpdir))
        job = bridge.dispatch(
            persona=StaffPersona.STAFFER,
            brief="Summarize architecture",
            custom_cmd=["python3", "-c", "print('DELIVERABLE: Synthesis complete.')"],
        )

        assert job.job_id.startswith("job-")
        assert job.persona == "staffer"

        exit_code, output = bridge.wait(job.job_id, timeout_sec=5.0)
        assert exit_code == JobExitCode.DONE
        assert "DELIVERABLE: Synthesis complete." in output


def test_wait_timeout_returns_running_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = AgyStaffBridge(state_dir=Path(tmpdir))
        job = bridge.dispatch(
            persona=StaffPersona.RESEARCHER,
            brief="Long-running deep research",
            custom_cmd=["sleep", "2"],
        )

        exit_code, msg = bridge.wait(job.job_id, timeout_sec=0.2)
        assert exit_code == JobExitCode.RUNNING_TIMEOUT
        assert "Worker is still running" in msg

        # Clean up
        bridge.cancel(job.job_id)


def test_cancel_job():
    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = AgyStaffBridge(state_dir=Path(tmpdir))
        job = bridge.dispatch(
            persona=StaffPersona.IMPLEMENTER,
            brief="Refactor module",
            custom_cmd=["sleep", "5"],
        )

        cancel_code = bridge.cancel(job.job_id)
        assert cancel_code == JobExitCode.CANCELED

        record = bridge.get_job(job.job_id)
        assert record is not None
        assert record.status == "canceled"
        assert record.exit_code == int(JobExitCode.CANCELED)


def test_observe_progress():
    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = AgyStaffBridge(state_dir=Path(tmpdir))
        job = bridge.dispatch(
            persona=StaffPersona.REVIEWER,
            brief="Review pull request",
            custom_cmd=["sleep", "1"],
        )

        obs = bridge.observe(job.job_id)
        assert obs["job_id"] == job.job_id
        assert obs["persona"] == "reviewer"
        assert "elapsed_sec" in obs

        bridge.cancel(job.job_id)


def test_workspace_audit():
    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = AgyStaffBridge(state_dir=Path(tmpdir))
        # Run audit on current working directory
        audit = bridge.audit_workspace(os.getcwd())
        assert "clean" in audit
        assert "dirty_files" in audit
        assert "count" in audit
