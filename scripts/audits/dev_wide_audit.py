#!/usr/bin/env python3
"""Dev-wide V-model health scan across all of ~/dev.

Companion to vmodel_module_audit.py (which is cohezion-specific). This scans EVERY
git repo under a root (default ~/dev) and reports the language-agnostic V-model
dimensions — but ONLY for Python-package repos. Non-Python repos (Fortran MHD,
C++ PIC, textbooks) are marked ``N/A — <lang>`` rather than emitting misleading
metrics, per the type-detect-first rule.

Python dimensions per repo:
  - python files (excl .venv/node_modules)
  - has pyproject.toml / setup.py (packaged?)
  - top-level package dirs missing __init__.py (discoverability)
  - has a tests/ dir (verification leg)
  - largest single .py file (god-object signal, 500 LOC limit)

Run:  uv run python scripts/audits/dev_wide_audit.py [root]
Writes JSON to docs/audits/dev_wide_manifest.json and prints a markdown table.
Report-only, non-destructive.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

from pathlib import Path

DEFAULT_ROOT = Path.home() / "dev"
SKIP_DIRS = {
    ".venv", "venv", "node_modules", ".git", "__pycache__", "build", "dist",
    # vendored / generated / worktree copies — exclude so counts reflect first-party code
    ".worktrees", "site-packages", "vendor", "third_party", "htmlcov", "_build",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "external", "extern",
}
CODE_EXT = {
    ".py": "Python", ".f90": "Fortran", ".f": "Fortran", ".F90": "Fortran",
    ".cpp": "C++", ".cc": "C++", ".cu": "C++/CUDA", ".hpp": "C++", ".h": "C/C++",
    ".c": "C", ".rs": "Rust", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".md": "Markdown/docs", ".ipynb": "Notebook",
}


def _iter_code_files(repo: Path):
    # os.walk with in-place dir pruning: never descends into vendored/.git trees,
    # so it stays fast even on huge C++/Fortran repos with vendored copies.
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def detect_language(repo: Path) -> tuple[str, Counter]:
    """Dominant code language by file count (excluding vendored dirs)."""
    counts: Counter = Counter()
    for f in _iter_code_files(repo):
        lang = CODE_EXT.get(f.suffix)
        if lang:
            counts[lang] += 1
    if not counts:
        return "unknown/empty", counts
    # docs-only repos: Markdown dominant and little/no code
    code = {k: v for k, v in counts.items() if k not in ("Markdown/docs", "Notebook")}
    if not code:
        return "docs/notebook", counts
    return max(code, key=lambda k: code[k]), counts


def loc(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def audit_python_repo(repo: Path) -> dict:
    py_files = [f for f in _iter_code_files(repo) if f.suffix == ".py"]
    packaged = (repo / "pyproject.toml").exists() or (repo / "setup.py").exists()
    has_tests = (repo / "tests").is_dir() or (repo / "test").is_dir()
    # top-level package dirs (under src/ or repo root) missing __init__
    roots = [repo / "src"] if (repo / "src").is_dir() else [repo]
    missing_init = []
    for r in roots:
        for d in r.iterdir() if r.is_dir() else []:
            if (
                d.is_dir()
                and d.name not in SKIP_DIRS
                and any(d.glob("*.py"))
                and not (d / "__init__.py").exists()
            ):
                missing_init.append(str(d.relative_to(repo)))
    max_loc, max_file = 0, ""
    for f in py_files:
        n = loc(f)
        if n > max_loc:
            max_loc, max_file = n, str(f.relative_to(repo))
    return {
        "py_files": len(py_files),
        "packaged": packaged,
        "has_tests": has_tests,
        "missing_init_dirs": missing_init,
        "max_loc": max_loc,
        "max_file": max_file,
        "oversize": max_loc > 500,
    }


def main() -> int:
    root = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_ROOT
    repos = sorted(d for d in root.iterdir() if (d / ".git").is_dir())
    rows = []
    for repo in repos:
        lang, counts = detect_language(repo)
        row = {"repo": repo.name, "language": lang, "file_counts": dict(counts)}
        if lang == "Python":
            row.update(audit_python_repo(repo))
            row["status"] = "audited"
        else:
            row["status"] = f"N/A — {lang}"
        rows.append(row)

    out = Path(__file__).resolve().parents[2] / "docs" / "audits" / "dev_wide_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"# Dev-wide V-model scan — {root} ({len(repos)} git repos)\n")
    print("| Repo | Lang | py | pkg | tests | miss_init | maxLOC | status |")
    print("|---|---|--:|:--:|:--:|--:|--:|---|")
    for r in rows:
        if r["status"] == "audited":
            print(
                f"| {r['repo']} | {r['language']} | {r['py_files']} | "
                f"{'Y' if r['packaged'] else 'N'} | {'Y' if r['has_tests'] else '**N**'} | "
                f"{len(r['missing_init_dirs'])} | {r['max_loc']}{'!' if r['oversize'] else ''} | audited |"
            )
        else:
            print(f"| {r['repo']} | {r['language']} | — | — | — | — | — | {r['status']} |")
    py = [r for r in rows if r["status"] == "audited"]
    no_tests = ", ".join(r["repo"] for r in py if not r["has_tests"]) or "none"
    oversize = ", ".join(f"{r['repo']}({r['max_loc']})" for r in py if r["oversize"]) or "none"
    print(f"\n**Python repos audited:** {len(py)} / {len(repos)}")
    print(f"- no tests/: {no_tests}")
    print(f"- oversize files: {oversize}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
