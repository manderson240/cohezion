"""Health monitoring task runners.

Entry points for Trigger.dev health tasks:
- test_suite: Run pytest and report pass/fail/coverage
- repo_hygiene: Git health, dead code, bloat detection
- security_audit: Vulnerability scanning
- metrics_snapshot: Collect system/agent metrics
- degradation_check: HIHO coherence monitoring
- db_pruning: SurrealDB record cleanup
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]  # src/cohezion/triggers/runners -> repo root


@dataclass
class TaskResult:
    """Standardized result from a health task."""

    task_id: str
    status: str  # "success", "warning", "failure"
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def emit(self) -> None:
        """Write result as JSON to stdout for Trigger.dev capture."""
        json.dump(asdict(self), sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()


def run_test_suite(payload: dict[str, Any] | None = None) -> TaskResult:
    """Run the full pytest suite and report results.

    Parameters
    ----------
    payload : dict, optional
        - ``scope``: Test directory (default ``"tests/"``).
        - ``markers``: pytest marker expression.
        - ``verbose``: Include per-test output.
    """
    payload = payload or {}
    scope = payload.get("scope", "tests/")
    markers = payload.get("markers", "")
    start = time.time()

    cmd = ["uv", "run", "pytest", str(REPO_ROOT / scope), "-q", "--tb=short"]
    if markers:
        cmd.extend(["-m", markers])

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=540,  # 9 min hard timeout
        )
        duration = time.time() - start

        # Parse pytest summary line: "X passed, Y failed, Z errors in Ns"
        summary_line = ""
        for line in result.stdout.splitlines()[::-1]:
            if "passed" in line or "failed" in line or "error" in line:
                summary_line = line.strip()
                break

        passed = _extract_count(summary_line, "passed")
        failed = _extract_count(summary_line, "failed")
        errors = _extract_count(summary_line, "error")
        warnings_count = _extract_count(summary_line, "warning")

        total = passed + failed + errors
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        status = "success" if failed == 0 and errors == 0 else "failure"

        return TaskResult(
            task_id="health/test-suite",
            status=status,
            duration_seconds=duration,
            metrics={
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "warnings": warnings_count,
                "total": total,
                "pass_rate": round(pass_rate, 2),
                "summary": summary_line,
            },
            errors=result.stderr.splitlines()[-5:] if result.returncode != 0 else [],
        )
    except subprocess.TimeoutExpired:
        return TaskResult(
            task_id="health/test-suite",
            status="failure",
            duration_seconds=time.time() - start,
            errors=["Test suite timed out after 540s"],
        )
    except Exception as e:
        return TaskResult(
            task_id="health/test-suite",
            status="failure",
            duration_seconds=time.time() - start,
            errors=[str(e)],
        )


def run_repo_hygiene(payload: dict[str, Any] | None = None) -> TaskResult:
    """Run repository health checks: git status, bloat, dead code."""
    start = time.time()
    metrics: dict[str, Any] = {}
    errors: list[str] = []

    try:
        # Git status check
        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        uncommitted = len(git_status.stdout.strip().splitlines()) if git_status.stdout.strip() else 0
        metrics["uncommitted_files"] = uncommitted

        # Repo size
        git_size = subprocess.run(
            ["git", "count-objects", "-vH"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in git_size.stdout.splitlines():
            if "size-pack" in line:
                metrics["pack_size"] = line.split(":")[1].strip()

        # Check for large files staged
        diff_cached = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        metrics["staged_changes"] = len(diff_cached.stdout.strip().splitlines())

        # Run healing system check if available
        try:
            from cohezion.healing import get_healing_system

            healing = get_healing_system()
            health_status = healing.detector.check(
                "repository", "bloat", uncommitted, 1000
            )
            metrics["healing_status"] = health_status.status
        except Exception:
            metrics["healing_status"] = "unavailable"

        status = "success" if uncommitted < 50 else "warning"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="health/repo-hygiene",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


def run_security_audit(payload: dict[str, Any] | None = None) -> TaskResult:
    """Run security audit checks."""
    start = time.time()
    metrics: dict[str, Any] = {}
    errors: list[str] = []

    try:
        # Check for common security issues
        security_script = REPO_ROOT / "scripts" / "security_scout.py"
        if security_script.exists():
            result = subprocess.run(
                ["uv", "run", "python", str(security_script)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            metrics["exit_code"] = result.returncode
            metrics["scan_completed"] = result.returncode == 0
            if result.returncode != 0:
                errors.extend(result.stderr.splitlines()[-5:])
        else:
            metrics["scan_completed"] = False
            errors.append("security_scout.py not found")

        # Check for secrets in tracked files
        secrets_check = subprocess.run(
            ["git", "log", "--diff-filter=A", "--name-only", "--pretty=format:", "-10"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        recent_files = secrets_check.stdout.strip().splitlines()
        suspect_files = [
            f for f in recent_files if any(s in f.lower() for s in [".env", "secret", "credential", "key"])
        ]
        metrics["suspect_files_added"] = len(suspect_files)

        status = "success" if not errors and not suspect_files else "warning"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="health/security-audit",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


def run_metrics_snapshot(payload: dict[str, Any] | None = None) -> TaskResult:
    """Collect system and agent metrics snapshot."""
    start = time.time()
    metrics: dict[str, Any] = {}

    try:
        import psutil

        # System metrics
        metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        metrics["memory_used_gb"] = round(mem.used / (1024**3), 2)
        metrics["memory_total_gb"] = round(mem.total / (1024**3), 2)
        metrics["memory_percent"] = mem.percent

        disk = psutil.disk_usage("/")
        metrics["disk_used_gb"] = round(disk.used / (1024**3), 2)
        metrics["disk_free_gb"] = round(disk.free / (1024**3), 2)
        metrics["disk_percent"] = round(disk.percent, 1)

        # Ollama status
        try:
            import httpx

            resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
            models = resp.json().get("models", [])
            metrics["ollama_online"] = True
            metrics["ollama_models_count"] = len(models)
        except Exception:
            metrics["ollama_online"] = False
            metrics["ollama_models_count"] = 0

        # SurrealDB status
        try:
            import httpx

            resp = httpx.get("http://localhost:8000/health", timeout=5)
            metrics["surrealdb_online"] = resp.status_code == 200
        except Exception:
            metrics["surrealdb_online"] = False

        status = "success"

    except Exception as e:
        status = "failure"
        metrics["error"] = str(e)

    return TaskResult(
        task_id="health/metrics-snapshot",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
    )


def run_degradation_check(payload: dict[str, Any] | None = None) -> TaskResult:
    """Check HIHO coherence stability across the system."""
    start = time.time()
    metrics: dict[str, Any] = {}
    errors: list[str] = []

    try:
        from cohezion.compound.degradation_detector import DegradationDetector

        detector = DegradationDetector()

        # Check overall system coherence
        coherence_result = detector.check_coherence()
        metrics["coherence"] = getattr(coherence_result, "coherence", 0.5)
        metrics["status"] = getattr(coherence_result, "status", "unknown")
        metrics["drift_detected"] = getattr(coherence_result, "drift_detected", False)
        metrics["hiho_stable"] = metrics.get("coherence", 0) >= 0.4  # HIHO threshold

        if metrics.get("drift_detected"):
            errors.append(f"Coherence drift detected: {metrics.get('coherence', 'N/A')}")

        status = "success" if metrics.get("hiho_stable", False) else "warning"

    except ImportError:
        status = "warning"
        metrics["note"] = "DegradationDetector not available"
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="health/degradation-check",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


def run_db_pruning(payload: dict[str, Any] | None = None) -> TaskResult:
    """Prune stale SurrealDB records."""
    payload = payload or {}
    days = payload.get("retention_days", 7)
    start = time.time()
    metrics: dict[str, Any] = {"retention_days": days}
    errors: list[str] = []

    try:
        pruning_script = REPO_ROOT / "scripts" / "db_pruning.py"
        if pruning_script.exists():
            result = subprocess.run(
                ["uv", "run", "python", str(pruning_script), str(days)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            metrics["exit_code"] = result.returncode
            metrics["pruning_completed"] = result.returncode == 0
            if result.returncode != 0:
                errors.extend(result.stderr.splitlines()[-3:])
        else:
            metrics["pruning_completed"] = False
            errors.append("db_pruning.py not found")

        status = "success" if not errors else "warning"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="health/db-pruning",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_count(summary: str, keyword: str) -> int:
    """Extract a numeric count from pytest summary like '42 passed'."""
    import re

    match = re.search(rf"(\d+)\s+{keyword}", summary)
    return int(match.group(1)) if match else 0


# ---------------------------------------------------------------------------
# CLI entry point (invoked by Trigger.dev Python extension)
# ---------------------------------------------------------------------------

_RUNNERS = {
    "test-suite": run_test_suite,
    "repo-hygiene": run_repo_hygiene,
    "security-audit": run_security_audit,
    "metrics-snapshot": run_metrics_snapshot,
    "degradation-check": run_degradation_check,
    "db-pruning": run_db_pruning,
}


def main() -> None:
    """CLI entry point: ``python -m cohezion.triggers.runners.health <task> [payload_json]``."""
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <{'|'.join(_RUNNERS)}> [payload_json]", file=sys.stderr)
        sys.exit(1)

    task_name = sys.argv[1]
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None

    runner = _RUNNERS.get(task_name)
    if not runner:
        print(f"Unknown task: {task_name}. Available: {list(_RUNNERS)}", file=sys.stderr)
        sys.exit(1)

    result = runner(payload)
    result.emit()
    sys.exit(0 if result.status != "failure" else 1)


if __name__ == "__main__":
    main()
