#!/usr/bin/env python3
"""AutoHarness verification script for Cohezion (Pi variant).

Mirror of .claude/rules/harness_check.py with one extra check:
  --mcp-parity: ensure .pi/mcp.json and .claude/mcp.json have the same
                set of MCP server names (WS1 of the harness-alignment plan).

Usage:
    python .pi/rules/harness_check.py [files...]      # full check
    python .pi/rules/harness_check.py --fast          # format+lint only
    python .pi/rules/harness_check.py --mcp-parity    # only the parity check
    python .pi/rules/harness_check.py --help
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FAST_CHECKS = ["format", "lint-quick"]
FULL_CHECKS = ["format", "lint", "typecheck", "fast-tests"]
VALIDATE_CHECKS = ["validate-skills", "validate-registry"]
PARITY_CHECKS = ["mcp-parity"]

CHECKS: dict[str, dict[str, Any]] = {
    "format": {
        "cmd": ["ruff", "format", "--check", "src/", "tests/"],
        "desc": "Ruff format check",
        "timeout": 30,
    },
    "lint-quick": {
        "cmd": ["ruff", "check", "--select=F,E9,E501", "src/", "tests/"],
        "desc": "Ruff quick lint (syntax errors only)",
        "timeout": 30,
    },
    "lint": {
        "cmd": ["ruff", "check", "src/", "tests/"],
        "desc": "Ruff full lint",
        "timeout": 60,
    },
    "typecheck": {
        "cmd": ["mypy", "src/cohezion/", "--ignore-missing-imports"],
        "desc": "Mypy type check",
        "timeout": 90,
    },
    "fast-tests": {
        "cmd": [
            "uv",
            "run",
            "pytest",
            "tests/unit/",
            "--import-mode=append",
            "--tb=short",
            "-q",
            "-p",
            "no:warnings",
        ],
        "desc": "Fast unit tests",
        "timeout": 120,
    },
    "validate-skills": {
        "cmd": ["uv", "run", "python", "scripts/ci/validate_skills.py"],
        "desc": "Validate PRIME skills",
        "timeout": 60,
    },
    "validate-registry": {
        "cmd": ["uv", "run", "python", "scripts/ci/validate_registry.py"],
        "desc": "Validate skill registry",
        "timeout": 30,
    },
    "mcp-parity": {
        "cmd": [],  # special-cased: not a subprocess
        "desc": "MCP server name parity between .pi/mcp.json and .claude/mcp.json",
        "timeout": 5,
    },
}


def run_check(name: str, cfg: dict, files: list[str]) -> dict:
    cmd = cfg["cmd"]
    if files and cmd:
        cmd = cmd + files

    t0 = time.perf_counter()
    try:
        if name == "mcp-parity":
            return _run_mcp_parity(t0)

        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=cfg["timeout"],
        )
        elapsed = time.perf_counter() - t0
        passed = result.returncode == 0
        return {
            "check": name,
            "description": cfg["desc"],
            "passed": passed,
            "elapsed_s": round(elapsed, 3),
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        return {
            "check": name,
            "description": cfg["desc"],
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "error": f"Timed out after {cfg['timeout']}s",
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "check": name,
            "description": cfg["desc"],
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "error": str(exc),
        }


def _run_mcp_parity(t0: float) -> dict:
    """Verify .pi/mcp.json and .claude/mcp.json have the same set of MCP server names."""
    pi_path = PROJECT_ROOT / ".pi" / "mcp.json"
    claude_path = PROJECT_ROOT / ".claude" / "mcp.json"
    elapsed = time.perf_counter() - t0

    if not pi_path.exists():
        return {
            "check": "mcp-parity",
            "description": CHECKS["mcp-parity"]["desc"],
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "error": f"missing: {pi_path}",
        }
    if not claude_path.exists():
        return {
            "check": "mcp-parity",
            "description": CHECKS["mcp-parity"]["desc"],
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "error": f"missing: {claude_path}",
        }

    try:
        pi_servers = set(json.loads(pi_path.read_text())["mcpServers"].keys())
        claude_servers = set(json.loads(claude_path.read_text())["mcpServers"].keys())
    except Exception as exc:
        return {
            "check": "mcp-parity",
            "description": CHECKS["mcp-parity"]["desc"],
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "error": f"parse error: {exc}",
        }

    if pi_servers == claude_servers:
        return {
            "check": "mcp-parity",
            "description": CHECKS["mcp-parity"]["desc"],
            "passed": True,
            "elapsed_s": round(elapsed, 3),
            "exit_code": 0,
            "stdout": f"both have {len(pi_servers)} servers: {sorted(pi_servers)}",
        }

    only_pi = pi_servers - claude_servers
    only_claude = claude_servers - pi_servers
    return {
        "check": "mcp-parity",
        "description": CHECKS["mcp-parity"]["desc"],
        "passed": False,
        "elapsed_s": round(elapsed, 3),
        "exit_code": 1,
        "stderr": (
            f"only in .pi/mcp.json: {sorted(only_pi) or 'none'} | "
            f"only in .claude/mcp.json: {sorted(only_claude) or 'none'} | "
            f"intersection size: {len(pi_servers & claude_servers)}"
        ),
    }


def main() -> int:
    files = []
    check_names = FULL_CHECKS + VALIDATE_CHECKS

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("Available checks:", ", ".join(CHECKS))
        return 0

    if "--fast" in sys.argv:
        check_names = FAST_CHECKS
        sys.argv.remove("--fast")

    if "--mcp-parity" in sys.argv:
        check_names = PARITY_CHECKS
        sys.argv.remove("--mcp-parity")

    # All remaining args are file paths
    files = sys.argv[1:]

    t0 = time.perf_counter()
    results = []
    failures = 0
    for name in check_names:
        if name not in CHECKS:
            continue
        r = run_check(name, CHECKS[name], files)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['description']} ({r.get('elapsed_s', 0):.1f}s)")
        if not r["passed"]:
            failures += 1
            if r.get("stderr"):
                print(f"    {r['stderr'][:200]}")
            if r.get("error"):
                print(f"    {r['error'][:200]}")

    total_elapsed = time.perf_counter() - t0
    passed = failures == 0

    print(f"\n{'PASSED' if passed else 'FAILED'} ({failures} failures) in {total_elapsed:.1f}s")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
