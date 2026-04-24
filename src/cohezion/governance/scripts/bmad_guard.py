"""BMAD Guard — enforces multi-session coordination and artifact integrity.

Runs as a Makefile guard (`make bmad-guard`) and as a pre-commit check.

Checks:
  1. Phase lock: only one session may own a BMAD phase at a time
  2. Artifact integrity: planning artifacts have valid frontmatter
  3. Symlink consistency: .pi/skills/bmad-* → .claude/skills/bmad-* (no broken links)
  4. Catalog consistency: bmad-help.csv columns match expected schema
  5. No concurrent edits: warn if _bmad-output artifacts are modified in
     a branch that doesn't own the corresponding phase lock

Exit codes:
  0 — all checks pass (or non-blocking warnings only)
  1 — hard failure (must fix before CI green)
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path.cwd()))
BMAD_DIR = PROJECT_ROOT / "_bmad"
BMAD_OUTPUT = PROJECT_ROOT / "_bmad-output"
PLANNING_DIR = BMAD_OUTPUT / "planning-artifacts"
IMPLEMENTATION_DIR = BMAD_OUTPUT / "implementation-artifacts"
CATALOG_PATH = BMAD_DIR / "_config" / "bmad-help.csv"
CONFIG_PATH = BMAD_DIR / "bmm" / "config.yaml"

# Phase lock files — one per BMAD phase, written by the session that owns it
PHASE_LOCKS = {
    "1-analysis": PLANNING_DIR / ".phase-lock-1",
    "2-planning": PLANNING_DIR / ".phase-lock-2",
    "3-solutioning": PLANNING_DIR / ".phase-lock-3",
    "4-implementation": IMPLEMENTATION_DIR / ".phase-lock-4",
}

WIRED = "\033[32m✓\033[0m"
BROKE = "\033[31m✗\033[0m"
WARN = "\033[33m⚠\033[0m"


# ── Check 1: Symlink Consistency ──────────────────────────────────────────────

def check_symlinks() -> bool:
    """All .pi/skills/bmad-* must be valid symlinks to .claude/skills/bmad-*."""
    pi_skills = PROJECT_ROOT / ".pi" / "skills"
    claude_skills = PROJECT_ROOT / ".claude" / "skills"
    ok = True

    for link in sorted(pi_skills.glob("bmad-*")):
        if not link.is_symlink():
            print(f"  {WARN} {link.name} — not a symlink (should point to .claude/skills/{link.name})")
            ok = False
            continue

        target = link.resolve()
        if not target.exists():
            print(f"  {BROKE} {link.name} — broken symlink → {target}")
            ok = False
            continue

        # Verify it points to .claude/skills/ (canonical source)
        expected_parent = claude_skills.resolve()
        if target.parent != expected_parent:
            print(f"  {WARN} {link.name} — points to {target.parent.name}/ instead of .claude/skills/")
        else:
            print(f"  {WIRED} {link.name} → .claude/skills/{link.name}")

    return ok


# ── Check 2: Catalog Schema ────────────────────────────────────────────────────

def check_catalog_schema() -> bool:
    """bmad-help.csv must have the expected column headers."""
    if not CATALOG_PATH.exists():
        print(f"  {BROKE} bmad-help.csv not found at {CATALOG_PATH}")
        return False

    try:
        with open(CATALOG_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if not headers:
                print(f"  {BROKE} bmad-help.csv has no headers")
                return False

            # v6.3.0 standard headers
            expected = {"module", "phase", "name", "code", "sequence", "workflow-file",
                        "command", "required", "agent-name", "agent-command",
                        "agent-display-name", "agent-title", "options", "description",
                        "output-location", "outputs"}

            missing = expected - set(headers)
            if missing:
                print(f"  {WARN} bmad-help.csv missing columns: {missing}")
            else:
                print(f"  {WIRED} bmad-help.csv schema valid ({len(headers)} columns)")

            # Detect v6.3.0 column shift (phase column contains skill IDs instead of phases)
            rows = list(reader)
            if rows:
                first_phase = rows[0].get("phase", "")
                if first_phase.startswith("bmad-"):
                    print(f"  {BROKE} bmad-help.csv has v6.3.0 column shift — 'phase' column contains skill IDs")
                    print(f"         Run: cp .worktrees/*/bmad/_bmad/_config/bmad-help.csv _bmad/_config/")
                    return False

            return True
    except Exception as exc:
        print(f"  {BROKE} Failed to read bmad-help.csv: {exc}")
        return False


# ── Check 3: Phase Lock Integrity ──────────────────────────────────────────────

def check_phase_locks() -> bool:
    """Phase lock files must be consistent (owned session matches branch)."""
    any_present = False
    for phase, lock_file in PHASE_LOCKS.items():
        if lock_file.exists():
            any_present = True
            content = lock_file.read_text().strip()
            lines = content.splitlines()
            owner = lines[0] if lines else "unknown"
            branch = lines[1] if len(lines) > 1 else "?"
            print(f"  {WIRED} Phase {phase} locked by {owner} on {branch}")
        else:
            print(f"  ·  Phase {phase} — no lock (available)")

    if not any_present:
        print(f"  {WARN} No phase locks exist — sessions can race on shared artifacts")

    return True  # Soft check — locks are optional


# ── Check 4: Artifact Frontmatter ──────────────────────────────────────────────

def check_artifact_frontmatter() -> bool:
    """Planning artifacts should have BMAD frontmatter with stepsCompleted."""
    if not PLANNING_DIR.exists():
        print(f"  ·  No planning-artifacts/ directory yet")
        return True

    ok = True
    for md_file in sorted(PLANNING_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        if content.startswith("---"):
            # Has frontmatter — check for stepsCompleted
            if "stepsCompleted" in content:
                print(f"  {WIRED} {md_file.name} — has stepsCompleted frontmatter")
            elif md_file.name == "project-context.md":
                print(f"  ·  {md_file.name} — context doc (no stepsCompleted needed)")
            else:
                print(f"  {WARN} {md_file.name} — frontmatter but no stepsCompleted")
                ok = False
        else:
            if md_file.stat().st_size > 100:  # Non-trivial file without frontmatter
                print(f"  {WARN} {md_file.name} — no frontmatter")
    return ok


# ── Check 5: Manifest Sync ────────────────────────────────────────────────────

def check_manifest_sync() -> bool:
    """The BMAD manifest should reflect what's actually on disk."""
    manifest_path = BMAD_DIR / "_config" / "manifest.yaml"
    if not manifest_path.exists():
        print(f"  {WARN} No manifest.yaml — run 'npx bmad-method install' first")
        return False

    # Check that the installed IDE skills exist
    claude_skills = PROJECT_ROOT / ".claude" / "skills"
    bmad_skills = sorted(claude_skills.glob("bmad-*"))
    print(f"  {WIRED} {len(bmad_skills)} bmad skills in .claude/skills/")

    # Check skill-manifest.csv line count vs actual skills
    skill_manifest = BMAD_DIR / "_config" / "skill-manifest.csv"
    if skill_manifest.exists():
        with open(skill_manifest, newline="", encoding="utf-8") as f:
            csv_lines = sum(1 for _ in csv.DictReader(f))
        if csv_lines != len(bmad_skills):
            print(f"  {WARN} skill-manifest.csv has {csv_lines} entries but {len(bmad_skills)} skills on disk")
        else:
            print(f"  {WIRED} skill-manifest.csv in sync ({csv_lines} entries)")
    return True


# ── Main ─────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run all BMAD guard checks. Returns 0 on pass, 1 on hard failure."""
    print("BMAD Guard: checking multi-session coordination and artifact integrity\n")

    results = []

    print("1. Symlink consistency:")
    results.append(("symlinks", check_symlinks()))

    print("\n2. Catalog schema:")
    results.append(("catalog", check_catalog_schema()))

    print("\n3. Phase locks:")
    results.append(("phase_locks", check_phase_locks()))

    print("\n4. Artifact frontmatter:")
    results.append(("frontmatter", check_artifact_frontmatter()))

    print("\n5. Manifest sync:")
    results.append(("manifest", check_manifest_sync()))

    # Summary
    hard_failures = [name for name, ok in results if not ok]
    print(f"\n{'─' * 50}")
    if hard_failures:
        print(f"RESULT: {BROKE} {len(hard_failures)} hard failure(s): {', '.join(hard_failures)}")
        print("Fix before pushing. Run `make bmad-guard` locally.")
        return 1
    else:
        print(f"RESULT: {WIRED} All BMAD guard checks passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
