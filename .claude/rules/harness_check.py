#!/usr/bin/env python3
"""
AutoHarness validation script for cohezion.

Usage:
    python .claude/rules/harness_check.py [file ...]
    python .claude/rules/harness_check.py --help
    python .claude/rules/harness_check.py --fast     # skip full test run

Outputs JSON: {"passed": bool, "results": {...}, "errors": [...]}
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

def _find_repo_root() -> Path:
    """Walk up from CWD until we find pyproject.toml or .git."""
    p = Path.cwd()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return p

REPO_ROOT = _find_repo_root()
PYTHON = REPO_ROOT / ".venv" / "bin" / "python3"
UV = "uv"


def _run(cmd: list[str], cwd: Path = REPO_ROOT, timeout: int = 120) -> dict:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        return {
            "passed": r.returncode == 0,
            "stdout": r.stdout[-2000:] if r.stdout else "",
            "stderr": r.stderr[-2000:] if r.stderr else "",
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "stdout": "", "stderr": f"Timeout after {timeout}s", "returncode": -1}
    except Exception as e:
        return {"passed": False, "stdout": "", "stderr": str(e), "returncode": -1}


def check_lint(files: list[Path] | None = None) -> dict:
    # Scope to src/ + tests/, exclude notebooks and archive
    targets = [str(f) for f in files] if files else ["src/", "tests/"]
    exclude = ["--exclude", "src/cohezion-archive", "--exclude", "*.ipynb"]
    r1 = _run(["ruff", "check", "--no-fix"] + exclude + targets, timeout=30)
    r2 = _run(["ruff", "format", "--check"] + exclude + targets, timeout=30)
    errors = []
    if not r1["passed"]:
        errors.append(r1["stderr"] or r1["stdout"])
    if not r2["passed"]:
        errors.append("Format check failed: " + (r2["stderr"] or r2["stdout"]))
    return {"passed": r1["passed"] and r2["passed"], "errors": errors}


def check_typecheck(files: list[Path] | None = None) -> dict:
    targets = [str(f) for f in files] if files else ["src/"]
    r = _run(
        ["mypy", "--ignore-missing-imports", "--no-error-summary"] + targets,
        timeout=60,
    )
    errors = []
    if not r["passed"]:
        lines = (r["stdout"] + r["stderr"]).splitlines()
        errors = [l for l in lines if ": error:" in l][:20]
    return {"passed": r["passed"], "errors": errors}


def check_tests(fast_only: bool = True) -> dict:
    cmd = [UV, "run", "pytest", "tests/", "--tb=short", "-q", "--no-header"]
    if fast_only:
        cmd += ["-m", "fast"]
    r = _run(cmd, timeout=180)
    errors = []
    if not r["passed"]:
        lines = (r["stdout"] + r["stderr"]).splitlines()
        errors = [l for l in lines if ("FAILED" in l or "ERROR" in l or "error" in l.lower())][:20]
    return {"passed": r["passed"], "errors": errors}


def check_forbidden_patterns(files: list[Path] | None = None) -> dict:
    """Scan for cohezion-specific anti-patterns."""
    src = REPO_ROOT / "src" / "cohezion"
    # Exclude archive — it's intentionally frozen and not actively maintained
    targets = files or [
        p for p in src.rglob("*.py")
        if "cohezion-archive" not in p.parts and "z5-" not in p.parts
        and "z6-" not in p.parts and "z7-" not in p.parts
    ]
    violations: list[str] = []

    forbidden = [
        ("Exception)", "except-tuple-with-exception", "stealth bare-except — Exception in except tuple makes all other types redundant"),
        ("sys.executable", "sys-executable-subprocess", "use .venv/bin/python3 in subprocesses"),
        ("pip install", "bare-pip", "use uv pip install"),
        ("time.sleep", "blocking-sleep-async", "blocking sleep — check if inside async def"),
    ]

    for path in targets:
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for lines_idx, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            for pattern, code, hint in forbidden:
                if pattern in stripped:
                    # Skip comments
                    if stripped.startswith("#"):
                        continue
                    violations.append(f"{path.relative_to(REPO_ROOT)}:{lines_idx}: [{code}] {hint}")

    return {"passed": len(violations) == 0, "errors": violations[:20]}


def main() -> None:
    parser = argparse.ArgumentParser(description="AutoHarness cohezion validator")
    parser.add_argument("files", nargs="*", type=Path, help="Specific files to check")
    parser.add_argument("--fast", action="store_true", help="Fast mode: skip full test run")
    parser.add_argument("--no-tests", action="store_true", help="Skip test execution entirely")
    args = parser.parse_args()

    files = [f.resolve() for f in args.files] if args.files else None

    results: dict[str, dict] = {}
    all_passed = True

    results["lint"] = check_lint(files)
    results["typecheck"] = check_typecheck(files)
    results["forbidden_patterns"] = check_forbidden_patterns(files)

    if not args.no_tests:
        results["tests"] = check_tests(fast_only=True)

    for name, r in results.items():
        if not r["passed"]:
            all_passed = False

    output = {
        "passed": all_passed,
        "results": {
            name: {"passed": r["passed"], "errors": r.get("errors", [])}
            for name, r in results.items()
        },
        "errors": [
            f"{name}: {e}"
            for name, r in results.items()
            for e in r.get("errors", [])
            if not r["passed"]
        ],
    }

    print(json.dumps(output, indent=2))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
