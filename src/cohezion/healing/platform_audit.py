"""
Platform Audit - Comprehensive health check for Cohezion.

Checks:
- Package structure (__init__.py files)
- Test coverage
- Documentation completeness
- API health
- Component availability
- Skill registry
"""

import json
import logging
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_UV = shutil.which("uv") or "/usr/local/bin/uv"


logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Result of a single audit check."""

    name: str
    status: str  # pass, warn, fail
    value: Any
    details: str = ""


@dataclass
class PlatformAudit:
    """Complete platform audit report."""

    timestamp: str
    audit_type: str  # "pre" or "post"
    checks: list[AuditResult]
    summary: dict[str, int]  # counts by status

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "audit_type": self.audit_type,
            "checks": [asdict(c) for c in self.checks],
            "summary": self.summary,
        }


def run_audit(audit_type: str = "pre") -> PlatformAudit:
    """Run comprehensive platform audit."""
    checks = []
    base_path = Path("src/cohezion")

    # 1. Check package structure
    missing_init = []
    for subdir in base_path.rglob("*"):
        if subdir.is_dir() and "__pycache__" not in str(subdir):
            init_file = subdir / "__init__.py"
            if not init_file.exists():
                missing_init.append(str(subdir))

    checks.append(
        AuditResult(
            name="package_structure",
            status="pass" if not missing_init else "warn",
            value=len(missing_init),
            details=f"Missing __init__.py: {missing_init[:5]}"
            if missing_init
            else "All packages initialized",
        )
    )

    # 2. Count tests
    test_files = list(Path("tests").rglob("test_*.py"))
    checks.append(
        AuditResult(
            name="test_files",
            status="pass" if len(test_files) >= 5 else "warn",
            value=len(test_files),
            details=f"Found {len(test_files)} test files",
        )
    )

    # 3. Run tests (quick check)
    try:
        result = subprocess.run(  # noqa: S603 - static pytest invocation
            [_UV, "run", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        test_output = result.stdout + result.stderr
        passed = "passed" in test_output
        checks.append(
            AuditResult(
                name="tests_passing",
                status="pass" if passed else "fail",
                value=passed,
                details=test_output.split("\n")[-2] if test_output else "Unknown",
            )
        )
    except Exception as e:
        checks.append(AuditResult(name="tests_passing", status="warn", value=False, details=str(e)))

    # 4. Count skills
    skills = list(Path("src/cohezion/skills").glob("*.md"))
    checks.append(
        AuditResult(
            name="skills_count",
            status="pass" if len(skills) >= 10 else "warn",
            value=len(skills),
            details=f"Found {len(skills)} skill files",
        )
    )

    # 5. Check API endpoints (if running)
    try:
        import httpx

        resp = httpx.get("http://localhost:8080/health", timeout=5)
        api_healthy = resp.status_code == 200
        checks.append(
            AuditResult(
                name="api_health",
                status="pass" if api_healthy else "fail",
                value=api_healthy,
                details="API responding" if api_healthy else "API down",
            )
        )
    except Exception:
        checks.append(
            AuditResult(
                name="api_health",
                status="warn",
                value=False,
                details="API not reachable",
            )
        )

    # 6. Check Ollama models
    try:
        import httpx

        resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            slm_count = sum(
                1 for m in models if any(x in m["name"] for x in ["gemma", "phi", "mistral"])
            )
            checks.append(
                AuditResult(
                    name="ollama_slms",
                    status="pass" if slm_count >= 3 else "warn",
                    value=slm_count,
                    details=f"{slm_count} SLMs available",
                )
            )
        else:
            raise Exception("Ollama not responding")
    except Exception as e:
        checks.append(AuditResult(name="ollama_slms", status="warn", value=0, details=str(e)))

    # 7. Check documentation
    docs = list(Path("src/cohezion/knowledge_graph/retrospectives").glob("*.md"))
    docs += list(Path("src/cohezion/library").glob("*.md"))
    checks.append(
        AuditResult(
            name="documentation",
            status="pass" if len(docs) >= 3 else "warn",
            value=len(docs),
            details=f"Found {len(docs)} documentation files",
        )
    )

    # 8. Check universe nodes (journeys, simulations)
    journeys = list(Path("src/cohezion/knowledge_graph/universe_nodes/journeys").glob("*.json"))
    sims = list(Path("src/cohezion/knowledge_graph/universe_nodes/simulations").glob("*.json"))
    checks.append(
        AuditResult(
            name="universe_nodes",
            status="pass" if len(journeys) + len(sims) > 0 else "warn",
            value={"journeys": len(journeys), "simulations": len(sims)},
            details=f"{len(journeys)} journeys, {len(sims)} simulations",
        )
    )

    # 9. Check components
    components = [
        "swarm",
        "calm",
        "viz",
        "api",
        "security",
        "reliability",
        "healing",
        "learning",
        "mcp",
    ]
    present = [c for c in components if (base_path / c).exists()]
    checks.append(
        AuditResult(
            name="components",
            status="pass" if len(present) >= 7 else "warn",
            value=len(present),
            details=f"Components: {', '.join(present)}",
        )
    )

    # 10. Lines of code estimate
    py_files = list(base_path.rglob("*.py"))
    total_lines = sum(len(f.read_text().split("\n")) for f in py_files if f.exists())
    checks.append(
        AuditResult(
            name="code_size",
            status="pass",
            value=total_lines,
            details=f"{len(py_files)} Python files, {total_lines:,} lines",
        )
    )

    # Calculate summary
    summary = {
        "pass": sum(1 for c in checks if c.status == "pass"),
        "warn": sum(1 for c in checks if c.status == "warn"),
        "fail": sum(1 for c in checks if c.status == "fail"),
    }

    audit = PlatformAudit(
        timestamp=datetime.now(UTC).isoformat(),
        audit_type=audit_type,
        checks=checks,
        summary=summary,
    )

    # Save audit
    audit_dir = Path("src/cohezion/knowledge_graph/audits")
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / f"audit_{audit_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(audit_file, "w") as f:
        json.dump(audit.to_dict(), f, indent=2)

    logger.info(f"Audit saved to {audit_file}")
    return audit


def print_audit(audit: PlatformAudit):
    """Print audit results in a readable format."""
    print(f"\n{'=' * 60}")
    print(f"PLATFORM AUDIT ({audit.audit_type.upper()})")
    print(f"Timestamp: {audit.timestamp}")
    print(f"{'=' * 60}\n")

    for check in audit.checks:
        icon = "✅" if check.status == "pass" else "⚠️" if check.status == "warn" else "❌"
        print(f"{icon} {check.name}: {check.value}")
        if check.details:
            print(f"   {check.details}")

    print(f"\n{'─' * 60}")
    print(
        f"Summary: {audit.summary['pass']} pass, {audit.summary['warn']} warn, "
        f"{audit.summary['fail']} fail"
    )
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    audit = run_audit("pre")
    print_audit(audit)
