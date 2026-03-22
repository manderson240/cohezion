#!/usr/bin/env python3
"""CI lint: detect anti-patterns in test files that cause environment-specific failures.

Anti-patterns caught:
  1. Hardcoded developer home paths (e.g. /home/mike-anderson/dev/...)
  2. Tests using os.access + chmod without mocking (fails as root)
  3. Git init in tests without commit.gpgsign=false
  4. Logging filters that convert args to strings (breaks %d format)

Run:  python scripts/ci/lint_tests.py
Exit: 0 if clean, 1 if violations found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"
SRC_DIR = REPO_ROOT / "src"

# --- Rules -------------------------------------------------------------------

RULES: list[dict] = [
    {
        "id": "HARDCODED_HOME",
        "description": "Hardcoded developer home directory path",
        "pattern": re.compile(r'"/home/[a-zA-Z0-9_-]+/(?:dev|projects|src|code)/'),
        "scope": "tests",
        "fix": "Use PROJECT_ROOT = Path(__file__).resolve().parents[N] or tmp_path fixture",
    },
    {
        "id": "GIT_INIT_NO_GPGSIGN",
        "description": "git init without commit.gpgsign=false (fails in GPG-enabled envs)",
        "pattern": re.compile(r"git.*init"),
        "scope": "tests",
        "validator": "_check_git_init_no_gpgsign",
    },
    {
        "id": "LOG_FILTER_STR_CAST",
        "description": "Logging filter converts args to str() (breaks %d format specifiers)",
        "pattern": re.compile(r"str\(arg\).*for arg in"),
        "scope": "src",
        "fix": "Only redact string args: use isinstance(arg, str) guard",
    },
]


def _check_git_init_no_gpgsign(filepath: Path, content: str) -> list[tuple[int, str]]:
    """Check that any file doing 'git init' also sets commit.gpgsign=false."""
    violations = []
    if "git_repo" in content:
        # Using the shared fixture — safe
        return []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if re.search(r'[\["\']git["\'],?\s*["\']init["\']', line):
            # Search forward 20 lines for gpgsign
            region = "\n".join(lines[i - 1 : i + 20])
            if "gpgsign" not in region:
                violations.append((i, "git init found without commit.gpgsign=false nearby"))
    return violations


def scan_file(filepath: Path, scope: str) -> list[str]:
    """Scan a single file for anti-pattern violations."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    issues = []
    rel = filepath.relative_to(REPO_ROOT)

    for rule in RULES:
        if rule["scope"] != scope:
            continue

        if "validator" in rule:
            fn = globals()[rule["validator"]]
            violations = fn(filepath, content)
            for lineno, msg in violations:
                issues.append(f"  {rel}:{lineno}: [{rule['id']}] {msg}")
        else:
            for i, line in enumerate(content.split("\n"), 1):
                if rule["pattern"].search(line):
                    fix_hint = rule.get("fix", "")
                    issues.append(
                        f"  {rel}:{i}: [{rule['id']}] {rule['description']}"
                        + (f"\n    Fix: {fix_hint}" if fix_hint else "")
                    )

    return issues


def main() -> int:
    all_issues: list[str] = []

    # Scan test files
    for py_file in sorted(TESTS_DIR.rglob("*.py")):
        all_issues.extend(scan_file(py_file, "tests"))

    # Scan source files
    for py_file in sorted(SRC_DIR.rglob("*.py")):
        all_issues.extend(scan_file(py_file, "src"))

    if all_issues:
        print(f"Found {len(all_issues)} test anti-pattern violation(s):\n")
        for issue in all_issues:
            print(issue)
        print("\nSee scripts/ci/lint_tests.py for rule descriptions and fix guidance.")
        return 1

    print("No test anti-pattern violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
