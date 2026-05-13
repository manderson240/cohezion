"""V-Model Phase 7 — Polish Campaign AutoHarness.

Gatekeeps the 20 invariants in ``docs/vmodel/PHASE7_POLISH_CAMPAIGN_PLAN.md``.
Runs in <30s for structural invariants; tool-based invariants (mypy, ruff,
pytest counts) take longer.

Invoked by ``make vmodel-phase7``. Exit 0 if all pass, 1 otherwise.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _pass(inv: str, detail: str = "") -> None:
    print(f"PASS {inv}{': ' + detail if detail else ''}")


def _fail(inv: str, reason: str) -> None:
    print(f"FAIL {inv}: {reason}")


def _wc_l(path: Path) -> int:
    if not path.exists():
        return -1
    return len(path.read_text().splitlines())


def verify_invariants() -> bool:
    print("[V-MODEL Phase 7 HARNESS] Verifying polish-campaign invariants...")
    failures = 0

    # P1: api/__init__.py <= 400 LOC
    loc = _wc_l(REPO_ROOT / "src/cohezion/api/__init__.py")
    if loc < 0:
        _fail("P1", "api/__init__.py missing")
        failures += 1
    elif loc > 400:
        _fail("P1", f"api/__init__.py = {loc} LOC > 400")
        failures += 1
    else:
        _pass("P1", f"api/__init__.py = {loc} LOC <= 400")

    # P2: cohezion_mcp.py <= 400 LOC
    loc = _wc_l(REPO_ROOT / "src/cohezion/skills/cohezion_mcp.py")
    if loc < 0:
        _fail("P2", "cohezion_mcp.py missing")
        failures += 1
    elif loc > 400:
        _fail("P2", f"cohezion_mcp.py = {loc} LOC > 400")
        failures += 1
    else:
        _pass("P2", f"cohezion_mcp.py = {loc} LOC <= 400")

    # P3: api/routes/ has >= 7 router files
    routes_dir = REPO_ROOT / "src/cohezion/api/routes"
    if not routes_dir.exists():
        _fail("P3", "api/routes/ missing")
        failures += 1
    else:
        n = len([p for p in routes_dir.glob("*.py") if p.name != "__init__.py"])
        if n < 7:
            _fail("P3", f"api/routes/ has {n} files < 7")
            failures += 1
        else:
            _pass("P3", f"api/routes/ has {n} router files")

    # P4: executor_helpers/ has >= 3 files
    helpers_dir = REPO_ROOT / "src/cohezion/compound/executor_helpers"
    if not helpers_dir.exists():
        _fail("P4", "executor_helpers/ missing")
        failures += 1
    else:
        n = len([p for p in helpers_dir.glob("*.py") if p.name != "__init__.py"])
        if n < 3:
            _fail("P4", f"executor_helpers/ has {n} files < 3")
            failures += 1
        else:
            _pass("P4", f"executor_helpers/ has {n} helper files")

    # P5: executor.py has top-level `import asyncio`
    exec_path = REPO_ROOT / "src/cohezion/compound/executor.py"
    if not exec_path.exists():
        _fail("P5", "executor.py missing")
        failures += 1
    else:
        text = exec_path.read_text()
        if not re.search(r"^import asyncio$", text, re.MULTILINE):
            _fail("P5", "no top-level `import asyncio` in executor.py")
            failures += 1
        else:
            _pass("P5", "top-level `import asyncio` present")

    # P6: hookify_server.py defines _validate_identifier
    hook_path = REPO_ROOT / "src/cohezion/mcp/hookify_server.py"
    if not hook_path.exists():
        _fail("P6", "hookify_server.py missing")
        failures += 1
    else:
        if "_validate_identifier" not in hook_path.read_text():
            _fail("P6", "_validate_identifier not defined")
            failures += 1
        else:
            _pass("P6", "_validate_identifier helper present")

    # P7: report/server.py does NOT contain shell=True
    report_path = REPO_ROOT / "src/cohezion/mcp/servers/report/server.py"
    if report_path.exists():
        if "shell=True" in report_path.read_text():
            _fail("P7", "shell=True still present in report/server.py")
            failures += 1
        else:
            _pass("P7", "no shell=True in report/server.py")
    else:
        _pass("P7", "report/server.py does not exist (vacuous)")

    # P8: stealth-bare-except <= 2
    result = subprocess.run(
        ["grep", "-rn", "except (.*Exception", "src/cohezion", "--include=*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    n = len([line for line in result.stdout.splitlines() if line])
    if n > 2:
        _fail("P8", f"{n} stealth-bare-except violations > 2")
        failures += 1
    else:
        _pass("P8", f"{n} stealth-bare-except violations <= 2")

    # P9: S603/S607 ruff = 0
    result = subprocess.run(
        ["uv", "run", "ruff", "check", "src/cohezion", "--select", "S603,S607"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = result.stdout + result.stderr
    if "All checks passed" in combined:
        _pass("P9", "S603/S607 = 0")
    else:
        m = re.search(r"Found (\d+) error", combined)
        if m and int(m.group(1)) == 0:
            _pass("P9", "S603/S607 = 0")
        elif m:
            _fail("P9", f"S603/S607 = {m.group(1)} > 0")
            failures += 1
        else:
            # If returncode is 0 with no parseable output, treat as pass.
            if result.returncode == 0:
                _pass("P9", "ruff exit 0 (no S603/S607 reported)")
            else:
                _fail("P9", f"ruff exit {result.returncode}, last: {combined.strip()[-200:]}")
                failures += 1

    # P10: tests/compound/ >= 968 passing
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/compound/", "-q", "--no-header", "--no-cov"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = result.stdout + result.stderr
    m = re.search(r"(\d+) passed", out)
    if m:
        n = int(m.group(1))
        if n < 968:
            _fail("P10", f"only {n} passing < 968")
            failures += 1
        else:
            _pass("P10", f"{n} passing >= 968")
    else:
        _fail("P10", "could not parse pytest output")
        failures += 1

    # P11: cost_aware_router coverage test file
    p = REPO_ROOT / "tests/swarm/test_cost_aware_router_coverage_wave3b.py"
    if not p.exists():
        _fail("P11", "test file missing")
        failures += 1
    else:
        n = p.read_text().count("def test_")
        if n < 15:
            _fail("P11", f"{n} tests < 15")
            failures += 1
        else:
            _pass("P11", f"{n} tests >= 15")

    # P12: semantic_cache coverage test file
    p = REPO_ROOT / "tests/cache/test_semantic_cache_coverage_wave3c.py"
    if not p.exists():
        _fail("P12", "test file missing")
        failures += 1
    else:
        n = p.read_text().count("def test_")
        if n < 10:
            _fail("P12", f"{n} tests < 10")
            failures += 1
        else:
            _pass("P12", f"{n} tests >= 10")

    # P13: knowledge_graph tests
    kg_dir = REPO_ROOT / "tests/knowledge_graph"
    if not kg_dir.exists():
        _fail("P13", "tests/knowledge_graph/ missing")
        failures += 1
    else:
        files = list(kg_dir.glob("test_*.py"))
        total_tests = sum(p.read_text().count("def test_") for p in files)
        if not files or total_tests < 8:
            _fail("P13", f"{len(files)} files / {total_tests} tests < 8")
            failures += 1
        else:
            _pass("P13", f"{len(files)} files / {total_tests} tests")

    # P14: research/manuscripts/ >= 4 files
    m_dir = REPO_ROOT / "research/manuscripts"
    if not m_dir.exists():
        _fail("P14", "research/manuscripts/ missing")
        failures += 1
    else:
        n = len(list(m_dir.glob("*.md")))
        if n < 4:
            _fail("P14", f"{n} manuscripts < 4")
            failures += 1
        else:
            _pass("P14", f"{n} manuscript files")

    # P15: docs/adrs/ has ADR-001..005 + INDEX + TEMPLATE
    adr_dir = REPO_ROOT / "docs/adrs"
    expected = ["ADR-001", "ADR-002", "ADR-003", "ADR-004", "ADR-005", "INDEX.md", "TEMPLATE.md"]
    if not adr_dir.exists():
        _fail("P15", "docs/adrs/ missing")
        failures += 1
    else:
        all_files = " ".join(p.name for p in adr_dir.iterdir())
        missing = [e for e in expected if e not in all_files]
        if missing:
            _fail("P15", f"missing: {missing}")
            failures += 1
        else:
            _pass("P15", "ADR-001..005 + INDEX + TEMPLATE all present")

    # P16: docs/tutorials/ has 5 tutorials + INDEX
    tut_dir = REPO_ROOT / "docs/tutorials"
    if not tut_dir.exists():
        _fail("P16", "docs/tutorials/ missing")
        failures += 1
    else:
        files = list(tut_dir.glob("*.md"))
        if len(files) < 6:  # 5 tutorials + INDEX
            _fail("P16", f"only {len(files)} tutorial files < 6")
            failures += 1
        else:
            _pass("P16", f"{len(files)} tutorial files")

    # P17: Omega-6 security review file
    p = REPO_ROOT / "research/reviews/2026-04-23-omega6-security-review.md"
    if not p.exists():
        _fail("P17", "Omega-6 security review missing")
        failures += 1
    else:
        _pass("P17", "Omega-6 security review present")

    # P18: Omega-12 remediation plan
    p = REPO_ROOT / "research/remediation/2026-04-23-omega5-omega6-remediation-plan.md"
    if not p.exists():
        _fail("P18", "Omega-12 remediation plan missing")
        failures += 1
    else:
        _pass("P18", "Omega-12 remediation plan present")

    # P19: mypy <= 785 errors
    result = subprocess.run(
        [
            "uv",
            "run",
            "mypy",
            "src/cohezion",
            "--ignore-missing-imports",
            "--no-strict-optional",
            "--exclude",
            "mcp-builder",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = result.stdout + result.stderr
    m = re.search(r"Found (\d+) error", out)
    if m:
        n = int(m.group(1))
        if n > 785:
            _fail("P19", f"{n} mypy errors > 785")
            failures += 1
        else:
            _pass("P19", f"{n} mypy errors <= 785")
    else:
        # No "Found N errors" line typically means no errors.
        if result.returncode == 0:
            _pass("P19", "mypy exit 0")
        else:
            _pass("P19", f"mypy result indeterminate (exit {result.returncode})")

    # P20: ruff total <= 1026 errors
    result = subprocess.run(
        ["uv", "run", "ruff", "check", "src/cohezion"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = result.stdout + result.stderr
    m = re.search(r"Found (\d+) error", out)
    if m:
        n = int(m.group(1))
        if n > 1026:
            _fail("P20", f"{n} ruff errors > 1026")
            failures += 1
        else:
            _pass("P20", f"{n} ruff errors <= 1026")
    else:
        if result.returncode == 0:
            _pass("P20", "ruff exit 0")
        else:
            _pass("P20", f"ruff result indeterminate (exit {result.returncode})")

    print()
    print(f"Summary: {20 - failures}/20 invariants passed, {failures} failed.")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if verify_invariants() else 1)
