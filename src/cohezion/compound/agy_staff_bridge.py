"""Agy-Staff Delegation Bridge for Cohezion.

Implements model-facing CLI delegation architecture following the agy-staff
specification (keli-wen/agy-staff):
1. Model-as-caller design: deterministic exit codes, progressive disclosure.
2. Detached asynchronous worker lifecycles with state isolation.
3. Clean separation of user deliverables (stdout) and telemetry (stderr/logs).
4. Pre-execution workspace diff audit to prevent clobbering user edits.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class JobExitCode(IntEnum):
    """Deterministic exit codes matching agy-staff design."""

    DONE = 0
    INVALID_COMMAND = 1
    RUNNING_TIMEOUT = 2
    ERROR = 3
    CANCELED = 4
    ATTENTION = 5


class StaffPersona(str, Enum):
    """Supported agy-staff worker personas."""

    ASK = "ask"
    STAFFER = "staffer"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    IMPLEMENTER = "implementer"
    LEAD = "lead"


@dataclass
class JobRecord:
    """Persistent job execution metadata."""

    job_id: str
    persona: str
    brief: str
    workdir: str
    pid: Optional[int]
    status: str
    exit_code: Optional[int]
    created_at: float
    ended_at: Optional[float]
    stdout_file: str
    stderr_file: str
    snapshot_file: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgyStaffBridge:
    """Manages asynchronous worker delegations adhering to agy-staff specification."""

    def __init__(self, state_dir: Optional[Path] = None) -> None:
        if state_dir is None:
            self.state_dir = Path.home() / ".cache" / "cohezion" / "agy_staff_jobs"
        else:
            self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def audit_workspace(self, workdir: str) -> Dict[str, Any]:
        """Audit working tree before dispatch to identify preexisting modifications."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=False,
            )
            dirty_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            return {
                "clean": len(dirty_files) == 0,
                "dirty_files": dirty_files,
                "count": len(dirty_files),
            }
        except Exception as e:
            return {"clean": False, "dirty_files": [], "error": str(e), "count": 0}

    def dispatch(
        self,
        persona: StaffPersona | str,
        brief: str,
        workdir: Optional[str] = None,
        custom_cmd: Optional[list[str]] = None,
    ) -> JobRecord:
        """Dispatch a background worker task and return job metadata immediately."""
        persona_str = persona.value if isinstance(persona, StaffPersona) else str(persona)
        effective_workdir = workdir or os.getcwd()
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        job_dir = self.state_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        stdout_file = str(job_dir / "stdout.txt")
        stderr_file = str(job_dir / "stderr.txt")
        snapshot_file = str(job_dir / "snapshot.json")

        cmd = custom_cmd
        if not cmd:
            cmd = ["echo", f"[AGY-WORKER:{persona_str}] Completed task: {brief}"]

        # Launch detached process with its own process group
        with (
            open(stdout_file, "w", encoding="utf-8") as out,
            open(stderr_file, "w", encoding="utf-8") as err,
        ):
            proc = subprocess.Popen(
                cmd,
                cwd=effective_workdir,
                stdout=out,
                stderr=err,
                start_new_session=True,
            )

        record = JobRecord(
            job_id=job_id,
            persona=persona_str,
            brief=brief,
            workdir=effective_workdir,
            pid=proc.pid,
            status="running",
            exit_code=None,
            created_at=time.time(),
            ended_at=None,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            snapshot_file=snapshot_file,
        )

        self._save_record(record)
        return record

    def wait(self, job_id: str, timeout_sec: float = 30.0) -> Tuple[JobExitCode, str]:
        """Wait for worker with soft timeout, returning deterministic exit code and report."""
        record = self.get_job(job_id)
        if not record:
            return JobExitCode.INVALID_COMMAND, f"Error: Job ID '{job_id}' not found."

        if (
            record.status in ("done", "error", "canceled", "attention")
            and record.exit_code is not None
        ):
            return JobExitCode(record.exit_code), self._read_stdout(record)

        if not record.pid:
            return JobExitCode.ERROR, "Error: Missing process ID in job record."

        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            poll_res = self._check_process(record.pid)
            if poll_res is not None:
                record.ended_at = time.time()
                record.exit_code = JobExitCode.DONE if poll_res == 0 else JobExitCode.ERROR
                record.status = "done" if poll_res == 0 else "error"
                self._save_record(record)
                return JobExitCode(record.exit_code), self._read_stdout(record)
            time.sleep(0.1)

        # Timeout reached: worker is still running
        return (
            JobExitCode.RUNNING_TIMEOUT,
            f"Wait expired for job '{job_id}'. Worker is still running.",
        )

    def observe(self, job_id: str) -> Dict[str, Any]:
        """Observe bounded progress snapshot of active worker without resetting budget."""
        record = self.get_job(job_id)
        if not record:
            return {"error": f"Job {job_id} not found", "status": "unknown"}

        is_running = False
        if record.pid:
            is_running = self._check_process(record.pid) is None

        stdout_tail = ""
        if os.path.exists(record.stdout_file):
            with open(record.stdout_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                stdout_tail = "".join(lines[-10:]) if lines else ""

        return {
            "job_id": record.job_id,
            "persona": record.persona,
            "brief": record.brief,
            "status": "running" if is_running else record.status,
            "is_running": is_running,
            "elapsed_sec": round(time.time() - record.created_at, 2),
            "stdout_tail": stdout_tail,
        }

    def cancel(self, job_id: str) -> JobExitCode:
        """Cancel worker process group cleanly and publish canceled status."""
        record = self.get_job(job_id)
        if not record or not record.pid:
            return JobExitCode.INVALID_COMMAND

        if self._check_process(record.pid) is None:
            try:
                # Terminate entire process group
                pgid = os.getpgid(record.pid)
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(0.1)
                if self._check_process(record.pid) is None:
                    os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception:
                try:
                    os.kill(record.pid, signal.SIGKILL)
                except Exception:
                    pass

        record.status = "canceled"
        record.exit_code = int(JobExitCode.CANCELED)
        record.ended_at = time.time()
        self._save_record(record)
        return JobExitCode.CANCELED

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Retrieve job record from disk."""
        meta_file = self.state_dir / job_id / "job.json"
        if not meta_file.exists():
            return None
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return JobRecord(**data)

    def _save_record(self, record: JobRecord) -> None:
        meta_file = self.state_dir / record.job_id / "job.json"
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)

    def _check_process(self, pid: int) -> Optional[int]:
        """Check if process has exited, returning exit code or None if still alive."""
        try:
            pid_res, status = os.waitpid(pid, os.WNOHANG)
            if pid_res == 0:
                return None
            if os.WIFEXITED(status):
                return os.WEXITSTATUS(status)
            return 1
        except ChildProcessError:
            # Process was reaped elsewhere or isn't a direct child
            try:
                os.kill(pid, 0)
                return None  # still alive
            except OSError:
                return 0  # no longer exists
        except Exception:
            return None

    def _read_stdout(self, record: JobRecord) -> str:
        if os.path.exists(record.stdout_file):
            with open(record.stdout_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""
