#!/usr/bin/env python3
"""Root health guard: keep the repository root, and path casing, the way they were meant to be.

History (why this is an allowlist and not a counter). The first version of this guard
(2026-04-19) counted non-hidden root items and failed above 75. It said it "fails CI", but
nothing ever ran it: no workflow, no pre-commit hook, no landing guard. Measured against the
2026-11-04 cleanup it could not have fired even if wired, for two reasons:

1. Most new clutter was hidden (``.playwright-cli/``, ``.hermes-sessions/``, ``.claire/``),
   and dot-names were skipped entirely.
2. A count only fails once the pile is already large. The root sat at ~57 visible items, so
   ``EOF``, ``package.json.harness-bak`` and a stray JPEG all landed under the threshold.

Three root sweeps (2026-04-19, 2026-05-02, 2026-08-20) each regressed within weeks. This
version asks narrower questions that can fail on the first bad commit:

- **Root allowlist.** Every top-level tracked name must be listed in ``ROOT_ALLOWLIST``.
  Adding a root entry is allowed; it just has to be a reviewed edit to this file.
- **No zero-byte root files.** An empty root file is almost always an accident (a mistyped
  heredoc left ``EOF``; an editor left ``package.json.harness-bak``). Deliberate flag files
  go in ``ROOT_FLAG_FILES``.
- **No case-insensitive path collisions.** ``docs/ARCHITECTURE.md`` and
  ``docs/architecture.md`` coexisted for nine months; on macOS and Windows one silently
  overwrites the other on checkout.

It reads the git index (``git ls-files``), not the working tree, so untracked local state
never fails it and a staged ``git add -A`` mistake does. See
``docs/audits/ROOT_CLEANUP_2026-11-04.md``.

Usage:
    python src/cohezion/governance/scripts/root_health_guard.py --self-test
    python src/cohezion/governance/scripts/root_health_guard.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]

# Every tracked top-level name. Grouped so a reviewer can see what kind of thing is being added.
ROOT_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Project docs and metadata
        "AGENTS.md",
        "CHANGELOG.md",
        "CITATION.cff",
        "CLAUDE.md",
        "CONTRIBUTING.md",
        "CONTRIBUTOR_LICENSE_AGREEMENT.md",
        "LICENSE",
        "LICENSING.md",
        "README.md",
        "SECURITY.md",
        # Build, packaging and type-check config
        "Dockerfile",
        "Makefile",
        "docker-compose.yml",
        "mypy_baseline.txt",
        "pyproject.toml",
        "pyrightconfig.json",
        "skills-lock.json",
        "uv.lock",
        # Git and CI config
        ".git-blame-ignore-revs",
        ".gitattributes",
        ".githooks",
        ".github",
        ".gitignore",
        ".gitmodules",
        ".pre-commit-config.yaml",
        ".secrets.baseline",
        ".semgrep",
        ".worktreeinclude",
        ".env.sheets-research.example",
        # Agent harness config, read by the tools from the repo root
        ".agent",
        ".agents",
        ".antigravity.md",
        ".autoharness",
        ".claude",
        ".hermes",
        ".obsidian",
        ".opencode",
        ".pi",
        ".stitch",
        ".well-known",
        ".zero",
        "_bmad",
        "_bmad-output",
        "mcp_config.json",
        "mcp_servers.json",
        # Live autoresearch loop: consumed by relative path from cron prompts and
        # autoresearch.sh, so it stays at the root (decided in the 2026-08-20 sweep).
        ".autoresearch-off",
        "autoresearch-dashboard.md",
        "autoresearch.ideas.md",
        "autoresearch.md",
        "autoresearch.sh",
        "autoresearch_store.py",
        # Source, tests and supporting code
        "baml_client",
        "baml_src",
        "cloud-vault-mcp",
        "config",
        "deploy",
        "docs",
        "examples",
        "experiments",
        "infrastructure",
        "muttest",
        "notebooks",
        "research",
        "scripts",
        "src",
        "tests",
        # Data, models and run output that code reads by path
        "benchmarks",
        "cache",
        "checkpoints",
        "conductor",
        "data",
        "environment_files",
        "kaggle-dataset",
        "knowledge",
        "memory",
        "references",
        "reports",
        "runs",
        "sandbox",
        "submissions",
        "vaults",
        # Open items from the 2026-11-04 cleanup: each needs an owner decision before it
        # moves (see the audit's "Not moved" table). Do not add new names to this group.
        ".omg",
        ".telemetry",
        ".tmp_kaggle",
        "onnx_models",
        "spdd",
    }
)

# Zero-byte root files that are deliberate (feature flags read by presence).
ROOT_FLAG_FILES: frozenset[str] = frozenset({".autoresearch-off"})


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def index_entries(repo: Path) -> list[tuple[str, str]]:
    """(blob hash, path) for every entry in the git index."""
    entries: list[tuple[str, str]] = []
    for record in _git(repo, "ls-files", "-s", "-z").split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        entries.append((meta.split()[1], path))
    return entries


def unlisted_root_names(paths: list[str], allowlist: frozenset[str]) -> list[str]:
    return sorted({p.split("/", 1)[0] for p in paths} - allowlist)


def zero_byte_root_files(
    entries: list[tuple[str, str]], empty_blob: str, flags: frozenset[str]
) -> list[str]:
    return sorted(
        path
        for blob, path in entries
        if "/" not in path and blob == empty_blob and path not in flags
    )


def case_collisions(paths: list[str]) -> list[list[str]]:
    """Groups of tracked paths that differ only by letter case."""
    groups: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        parts = path.split("/")
        # A collision can sit at any level: two directories differing in case clash too.
        for depth in range(1, len(parts) + 1):
            prefix = "/".join(parts[:depth])
            groups[prefix.lower()].add(prefix)
    return sorted(sorted(g) for g in groups.values() if len(g) > 1)


def scan(
    repo: Path,
    allowlist: frozenset[str] = ROOT_ALLOWLIST,
    flags: frozenset[str] = ROOT_FLAG_FILES,
) -> list[str]:
    entries = index_entries(repo)
    paths = [path for _, path in entries]
    empty_blob = _git(repo, "hash-object", "-t", "blob", "/dev/null").strip()
    findings = [
        f"unlisted root entry: {name} (add it to ROOT_ALLOWLIST in this file, or move it)"
        for name in unlisted_root_names(paths, allowlist)
    ]
    findings += [
        f"zero-byte root file: {path} (likely an accident; flags go in ROOT_FLAG_FILES)"
        for path in zero_byte_root_files(entries, empty_blob, flags)
    ]
    findings += [
        f"case-insensitive collision: {' vs '.join(group)}" for group in case_collisions(paths)
    ]
    return findings


def self_test() -> int:
    """Prove each check can go red on a planted defect before trusting its green."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(repo, "init", "-q")
        blob = subprocess.run(
            ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
            input="content\n",
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        empty = _git(repo, "hash-object", "-w", "-t", "blob", "/dev/null").strip()

        def add(path: str, sha: str) -> None:
            # Index-only entries: works on case-insensitive filesystems too.
            _git(repo, "update-index", "--add", "--cacheinfo", f"100644,{sha},{path}")

        allow = frozenset({"README.md", "docs", "flag"})
        add("README.md", blob)
        add("docs/guide.md", blob)
        add("flag", empty)
        if scan(repo, allow, frozenset({"flag"})):
            print("self-test FAILED: clean tree reported findings")
            return 1

        planted = {
            "unlisted root entry: satus": ("satus/config.json", blob),
            "zero-byte root file: EOF": ("EOF", empty),
            "case-insensitive collision: docs/ARCHITECTURE.md vs docs/architecture.md": (
                "docs/ARCHITECTURE.md",
                blob,
            ),
        }
        add("docs/architecture.md", blob)
        for path, sha in planted.values():
            add(path, sha)
        findings = scan(repo, allow | {"EOF"}, frozenset({"flag"}))
        for expected in planted:
            if not any(f.startswith(expected) for f in findings):
                print(f"self-test FAILED: missed planted defect -> {expected}")
                return 1
    print("self-test OK: every check goes red on its planted defect and green on a clean tree")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    findings = scan(args.repo)
    for finding in findings:
        print(f"ERROR {finding}")
    if findings:
        print(
            f"\nroot health: {len(findings)} problem(s). See docs/audits/ROOT_CLEANUP_2026-11-04.md"
        )
        return 1
    print("root health OK: root matches the allowlist, no stray empty files, no case collisions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
