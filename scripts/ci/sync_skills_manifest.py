#!/usr/bin/env python3
"""Skills-sync manifest for Cohezion's three agent harnesses.

Reads the canonical skills directory (default: .agents/skills/) and
compares it against each harness's local skills directory
(.claude/skills/, .pi/skills/, ~/.hermes/skills/).

For each (canonical, target) pair, emits:
  - present_in_both: skills in canonical that also exist in target
  - missing_in_target: skills in canonical that target should have
  - extra_in_target: skills in target that are not in canonical
                    (per-harness customizations; normally not synced)

Usage:
    # Print a JSON manifest to stdout (default; read-only)
    python scripts/ci/sync_skills_manifest.py

    # Also print a human-readable summary
    python scripts/ci/sync_skills_manifest.py --summary

    # Write the manifest to a file (for CI artifact)
    python scripts/ci/sync_skills_manifest.py --output manifest.json

    # Actually copy missing skills from canonical to each target
    # (overwrites target files; do not use for skills that have
    # per-harness customizations — review the diff first)
    python scripts/ci/sync_skills_manifest.py --apply

    # Custom canonical + custom targets
    python scripts/ci/sync_skills_manifest.py --canonical .agents/skills \\
        --target .claude/skills --target .pi/skills \\
        --target $HOME/.hermes/skills

Design notes:
- Skills are identified by their directory name (e.g. bmad-create-prd).
- A skill is "present" if the target directory contains a file (any file).
  We don't compare content because the targets are expected to evolve
  independently for harness-specific needs; this script only ensures
  *coverage* (no skill silently dropped from a harness).
- The --apply flag is intentionally a separate mode that requires
  explicit invocation. It does not delete extras; only copies missing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CANONICAL = PROJECT_ROOT / ".agents" / "skills"
DEFAULT_TARGETS = [
    PROJECT_ROOT / ".claude" / "skills",
    PROJECT_ROOT / ".pi" / "skills",
    Path.home() / ".hermes" / "skills",
]


def discover_skill_names(skills_dir: Path) -> set[str]:
    """Return the set of skill directory names in *skills_dir*.

    A "skill" is any immediate subdirectory of *skills_dir* that contains
    at least one file (a SKILL.md, a workflow.md, or anything else). Top-
    level files at *skills_dir* itself are ignored.
    """
    if not skills_dir.is_dir():
        return set()
    out: set[str] = set()
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if any(entry.iterdir()):
            out.add(entry.name)
    return out


def build_manifest(canonical: Path, targets: list[Path]) -> dict:
    canonical_names = discover_skill_names(canonical)
    manifest: dict = {
        "canonical": str(canonical),
        "canonical_skill_count": len(canonical_names),
        "canonical_skills": sorted(canonical_names),
        "targets": {},
    }
    for target in targets:
        target_names = discover_skill_names(target)
        present = canonical_names & target_names
        missing = canonical_names - target_names
        extra = target_names - canonical_names
        manifest["targets"][str(target)] = {
            "present_count": len(present),
            "missing_count": len(missing),
            "extra_count": len(extra),
            "missing_skills": sorted(missing),
            "extra_skills": sorted(extra),
            "present_skills": sorted(present),
        }
    return manifest


def apply_sync(canonical: Path, manifest: dict, *, dry_run: bool) -> dict:
    """Copy missing skills from canonical to each target.

    Returns a per-target action log.
    """
    actions: dict = {}
    for target_str, info in manifest["targets"].items():
        target = Path(target_str)
        log: list[dict] = []
        for skill in info["missing_skills"]:
            src = canonical / skill
            dst = target / skill
            entry = {"skill": skill, "src": str(src), "dst": str(dst), "action": "copy"}
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.is_symlink():
                    real_target = os.path.realpath(dst)
                    if real_target and Path(real_target).exists():
                        entry["action"] = "skip (live symlink — leave as-is)"
                    else:
                        entry["action"] = "skip (dangling symlink — manual review required)"
                elif dst.exists():
                    entry["action"] = "skip (exists)"
                else:
                    shutil.copytree(src, dst)
                    entry["action"] = "copied"
            log.append(entry)
        actions[target_str] = log
    return actions


def print_summary(manifest: dict) -> None:
    print(f"Canonical: {manifest['canonical']} ({manifest['canonical_skill_count']} skills)")
    print()
    for target_str, info in manifest["targets"].items():
        print(f"Target: {target_str}")
        print(f"  present: {info['present_count']}")
        print(f"  missing: {info['missing_count']}")
        print(f"  extras : {info['extra_count']} (per-harness customizations)")
        if info["missing_skills"]:
            print(f"  missing list: {', '.join(info['missing_skills'])}")
        if info["extra_skills"]:
            print(f"  extras  list: {', '.join(info['extra_skills'])}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync skills manifest across Cohezion agent harnesses",
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=DEFAULT_CANONICAL,
        help=f"Canonical skills directory (default: {DEFAULT_CANONICAL})",
    )
    parser.add_argument(
        "--target",
        type=Path,
        action="append",
        help="Target skills directory (repeatable; default: .claude/, .pi/, ~/.hermes/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON manifest to this path (in addition to stdout)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a human-readable summary in addition to the JSON",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy missing skills from canonical to each target (default: dry-run)",
    )
    args = parser.parse_args()

    if not args.canonical.is_dir():
        print(f"ERROR: canonical directory does not exist: {args.canonical}", file=sys.stderr)
        return 2

    targets = args.target if args.target else DEFAULT_TARGETS

    manifest = build_manifest(args.canonical, targets)

    if args.apply:
        manifest["sync_actions"] = apply_sync(args.canonical, manifest, dry_run=False)
    else:
        manifest["sync_actions"] = apply_sync(args.canonical, manifest, dry_run=True)
        manifest["dry_run"] = True

    output_json = json.dumps(manifest, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_json)
    print(output_json)

    if args.summary:
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print_summary(manifest)
        if manifest.get("dry_run"):
            print("(dry-run mode — re-run with --apply to copy missing skills)")

    total_missing = sum(t["missing_count"] for t in manifest["targets"].values())
    return 0 if total_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
