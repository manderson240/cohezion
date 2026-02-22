"""Compound engineering task runners.

Entry points for Trigger.dev compound tasks:
- skill_refinement: Analyze and refine PRIME skill definitions
- retrospection: Run retrospection engine on recent executions
- journey_audit: Audit 12D journey tracking for drift
- vault_compile: Compile MEMORY.md from vault learnings
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass
class TaskResult:
    """Standardized result from a compound task."""

    task_id: str
    status: str
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    refinements: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def emit(self) -> None:
        json.dump(asdict(self), sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()


def run_skill_refinement(payload: dict[str, Any] | None = None) -> TaskResult:
    """Run skill refinement loop: analyze failures, update definitions, validate.

    Parameters
    ----------
    payload : dict, optional
        - ``skill_name``: Specific skill to refine (default: auto-detect worst).
        - ``dry_run``: If True, analyze but don't modify skills.
    """
    payload = payload or {}
    dry_run = payload.get("dry_run", False)
    start = time.time()
    metrics: dict[str, Any] = {"dry_run": dry_run}
    refinements: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        # Find skills directory
        skills_dir = REPO_ROOT / "src" / "cohezion" / "skills"
        if skills_dir.exists():
            skill_files = list(skills_dir.glob("*PRIME*.md"))
            metrics["total_prime_skills"] = len(skill_files)
        else:
            metrics["total_prime_skills"] = 0

        # Run skill refinement pipeline if available
        refine_script = REPO_ROOT / "scripts" / "drivers" / "refine_skill.py"
        if refine_script.exists() and not dry_run:
            skill_name = payload.get("skill_name", "")
            cmd = ["uv", "run", "python", str(refine_script)]
            if skill_name:
                cmd.extend(["--skill", skill_name])

            result = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=1800,
            )
            metrics["exit_code"] = result.returncode
            metrics["refinement_completed"] = result.returncode == 0

            # Parse refinements from output
            for line in result.stdout.splitlines():
                if "refined" in line.lower() or "updated" in line.lower():
                    refinements.append({"log": line.strip()})

            if result.returncode != 0:
                errors.extend(result.stderr.splitlines()[-5:])
        elif dry_run:
            metrics["refinement_completed"] = False
            metrics["note"] = "Dry run - analysis only"

        # Check skill registry health
        registry_file = skills_dir / "skill_registry.json" if skills_dir.exists() else None
        if registry_file and registry_file.exists():
            with open(registry_file) as f:
                registry = json.load(f)
            metrics["registered_skills"] = len(registry) if isinstance(registry, (list, dict)) else 0

        status = "success" if not errors else "warning"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="compound/skill-refinement",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        refinements=refinements,
        errors=errors,
    )


def run_retrospection(payload: dict[str, Any] | None = None) -> TaskResult:
    """Run retrospection engine on recent compound executions.

    Extracts learnings, flags anomalies, and feeds insights back
    into the skill refinement loop.
    """
    start = time.time()
    metrics: dict[str, Any] = {}
    refinements: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        from cohezion.core.compound.retrospection import RetrospectionEngine

        engine = RetrospectionEngine()
        metrics["engine_available"] = True

        # Check for recent execution data
        data_dir = REPO_ROOT / "data"
        executions_dir = data_dir / "compound_executions"
        if executions_dir.exists():
            execution_files = sorted(executions_dir.glob("*.jsonl"))
            metrics["execution_files"] = len(execution_files)
        else:
            metrics["execution_files"] = 0

        # Run retrospection script if available
        retro_script = REPO_ROOT / "scripts" / "retrospective_persist.py"
        if retro_script.exists():
            result = subprocess.run(
                ["uv", "run", "python", str(retro_script)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=1200,
            )
            metrics["retrospection_completed"] = result.returncode == 0
            if result.returncode != 0:
                errors.extend(result.stderr.splitlines()[-3:])

        status = "success" if not errors else "warning"

    except ImportError:
        status = "warning"
        metrics["engine_available"] = False
        metrics["note"] = "RetrospectionEngine not importable"
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="compound/retrospection",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        refinements=refinements,
        errors=errors,
    )


def run_journey_audit(payload: dict[str, Any] | None = None) -> TaskResult:
    """Audit 12D journey tracking for drift and anomalies."""
    start = time.time()
    metrics: dict[str, Any] = {}
    errors: list[str] = []

    try:
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        metrics["tracker_available"] = True

        # Run journey audit script
        journey_script = REPO_ROOT / "scripts" / "journey_12d_tracker.py"
        if journey_script.exists():
            result = subprocess.run(
                ["uv", "run", "python", str(journey_script)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=600,
            )
            metrics["audit_completed"] = result.returncode == 0
            if result.returncode != 0:
                errors.extend(result.stderr.splitlines()[-3:])
        else:
            metrics["audit_completed"] = False
            metrics["note"] = "Journey audit script not found"

        status = "success" if not errors else "warning"

    except ImportError:
        status = "warning"
        metrics["tracker_available"] = False
    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="compound/journey-audit",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


def run_vault_compile(payload: dict[str, Any] | None = None) -> TaskResult:
    """Compile MEMORY.md from vault learnings."""
    start = time.time()
    metrics: dict[str, Any] = {}
    errors: list[str] = []

    compile_script = REPO_ROOT / "scripts" / "compile_memory_from_vault.py"

    try:
        if compile_script.exists():
            result = subprocess.run(
                ["uv", "run", "python", str(compile_script)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            metrics["exit_code"] = result.returncode
            metrics["compilation_completed"] = result.returncode == 0
            if result.returncode != 0:
                errors.extend(result.stderr.splitlines()[-3:])
        else:
            metrics["compilation_completed"] = False
            errors.append("compile_memory_from_vault.py not found")

        # Check vault stats
        vault_dir = Path.home() / "vaults" / "cohezion-vault"
        if vault_dir.exists():
            decisions = list((vault_dir / "decisions").glob("*.md")) if (vault_dir / "decisions").exists() else []
            patterns = list((vault_dir / "patterns").glob("*.md")) if (vault_dir / "patterns").exists() else []
            experiments = list((vault_dir / "experiments").glob("*.md")) if (vault_dir / "experiments").exists() else []
            metrics["vault_decisions"] = len(decisions)
            metrics["vault_patterns"] = len(patterns)
            metrics["vault_experiments"] = len(experiments)
            metrics["vault_total"] = len(decisions) + len(patterns) + len(experiments)
        else:
            metrics["vault_available"] = False

        status = "success" if not errors else "warning"

    except Exception as e:
        status = "failure"
        errors.append(str(e))

    return TaskResult(
        task_id="compound/vault-compile",
        status=status,
        duration_seconds=time.time() - start,
        metrics=metrics,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_RUNNERS = {
    "skill-refinement": run_skill_refinement,
    "retrospection": run_retrospection,
    "journey-audit": run_journey_audit,
    "vault-compile": run_vault_compile,
}


def main() -> None:
    """CLI: ``python -m cohezion.triggers.runners.compound <task> [payload_json]``."""
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
