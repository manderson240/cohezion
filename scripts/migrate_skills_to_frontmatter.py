"""One-shot migration: add Agent Skills spec-compliant YAML frontmatter to
every PRIME skill file in `src/cohezion/skills/`.

Closes Sprint B Phase 3 from patterns/deferred-sprints-consolidation-and-skills-migration.md.
Rec 1 of patterns/skills-sh-agent-skills-spec-review.md — LOW risk migration
that unlocks `npx skills add <owner/repo>` distribution via skills.sh.

Source of truth for metadata:
  * `name` — derived from filename: `ADVERSARIAL_TESTING_PRIME.md` →
    `adversarial-testing-prime` (spec requires `[a-z0-9-]`, 1-64 chars,
    matching parent dir; we honor the name constraint but not the
    parent-dir-match constraint since files are still flat in skills/).
  * `description` — extracted from the first `## DOMAIN EXPERTISE`
    paragraph, bounded to 512 chars (spec allows up to 1024 but shorter
    is cheaper to preload).
  * `metadata.{version, concepts, see_also}` — mirrored verbatim from
    `skill_registry.json` — that file remains the compiled cache, this
    frontmatter becomes the source of truth (same pattern as MEMORY.md
    vs. vault: frontmatter wins, JSON is regenerable).

Idempotent: skips any file whose first non-blank line is `---` (already has
frontmatter). Running twice is a no-op.

Usage:
    # Preview without writing (default)
    uv run python scripts/migrate_skills_to_frontmatter.py

    # Apply — writes frontmatter + backs up originals
    uv run python scripts/migrate_skills_to_frontmatter.py --apply

    # Apply in a different skills dir (for testing)
    uv run python scripts/migrate_skills_to_frontmatter.py --apply --skills-dir /tmp/test-skills

Exit codes:
    0  success (dry-run or apply)
    1  partial failure (some files couldn't be migrated; summary on stderr)
    2  CLI arg error / skills_dir missing
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SKILLS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "cohezion" / "skills"
)
DEFAULT_REGISTRY = "skill_registry.json"


def filename_to_spec_name(stem: str) -> str:
    """`ADVERSARIAL_TESTING_PRIME` → `adversarial-testing-prime`.

    Spec constraints: `[a-z0-9-]`, 1-64 chars. We lowercase + replace
    underscores with dashes, then strip any remaining invalid chars.
    """
    name = stem.lower().replace("_", "-")
    name = re.sub(r"[^a-z0-9-]", "", name)
    # Collapse runs of dashes, strip leading/trailing
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:64]


def extract_description(body: str, max_chars: int = 512) -> str:
    """Pull the first paragraph under `## DOMAIN EXPERTISE`.

    Returns a single-line description bounded to ``max_chars``. Strips
    markdown bold/italic markers so the result is plain text suitable for
    spec `description` field (which is keyword-dense prose for routing).

    Fallbacks:
      * If no DOMAIN EXPERTISE section, take the first ## section's first paragraph.
      * If no ## sections at all, take the first 2 lines after `# SKILL:`.
      * If the file is truly empty or malformed, return a placeholder.
    """
    # Primary: ## DOMAIN EXPERTISE paragraph
    match = re.search(
        r"^##\s+DOMAIN\s+EXPERTISE\s*\n+(.+?)(?=\n\s*\n|\n##|\Z)",
        body,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if match:
        paragraph = match.group(1).strip()
    else:
        # Fallback 1: first ## section's first paragraph
        match = re.search(
            r"^##\s+\S.*?\n+(.+?)(?=\n\s*\n|\n##|\Z)",
            body,
            re.MULTILINE | re.DOTALL,
        )
        paragraph = match.group(1).strip() if match else ""

    if not paragraph:
        # Fallback 2: first 2 non-header lines
        lines = [
            line
            for line in body.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        paragraph = " ".join(lines[:2]) if lines else "Cohezion PRIME skill (description pending)."

    # Strip markdown formatting for plain description
    paragraph = re.sub(r"\*\*([^*]+)\*\*", r"\1", paragraph)  # bold
    paragraph = re.sub(r"\*([^*]+)\*", r"\1", paragraph)  # italic
    paragraph = re.sub(r"`([^`]+)`", r"\1", paragraph)  # inline code
    paragraph = re.sub(r"\s+", " ", paragraph).strip()  # collapse whitespace

    if len(paragraph) > max_chars:
        # Truncate at the last sentence boundary within limit
        cut = paragraph[: max_chars - 1].rsplit(".", 1)
        paragraph = (cut[0] + ".") if len(cut) == 2 and cut[0] else paragraph[:max_chars]
    return paragraph


def has_frontmatter(content: str) -> bool:
    """Return True if the file already starts with YAML frontmatter.

    Tolerates a BOM or leading whitespace but requires `---` as the first
    non-blank content.
    """
    stripped = content.lstrip("﻿").lstrip()
    return stripped.startswith("---\n") or stripped.startswith("---\r\n")


def yaml_scalar(value: str) -> str:
    """Minimal YAML string quoting. We use double quotes + escape backslashes
    and inner quotes. Avoids depending on PyYAML for the migration script."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def yaml_list(items: list[str]) -> str:
    """Render a list of strings as a YAML flow-style array."""
    if not items:
        return "[]"
    return "[" + ", ".join(yaml_scalar(i) for i in items) + "]"


def build_frontmatter(
    name: str,
    description: str,
    registry_entry: dict | None,
) -> str:
    """Render the YAML frontmatter block including trailing `---\\n\\n`."""
    lines = [
        "---",
        f"name: {name}",
        f"description: {yaml_scalar(description)}",
    ]

    # Metadata section — mirror registry fields when present
    if registry_entry:
        lines.append("metadata:")
        if "version" in registry_entry:
            lines.append(f"  version: {yaml_scalar(registry_entry['version'])}")
        concepts = registry_entry.get("concepts") or []
        if concepts:
            lines.append(f"  concepts: {yaml_list(concepts)}")
        see_also = registry_entry.get("see_also") or []
        if see_also:
            lines.append(f"  see_also: {yaml_list(see_also)}")
        if "source" in registry_entry:
            lines.append(f"  source: {yaml_scalar(registry_entry['source'])}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + "\n"


def migrate_file(
    md_path: Path,
    registry: dict,
    *,
    apply: bool,
) -> tuple[str, str]:
    """Migrate a single skill file. Returns (status, detail).

    status: "migrated" | "already-has-frontmatter" | "skipped-not-prime" | "error"
    """
    content = md_path.read_text(encoding="utf-8")

    if has_frontmatter(content):
        return ("already-has-frontmatter", "skipping (idempotent)")

    stem = md_path.stem
    if not stem.endswith("_PRIME"):
        # Only migrate PRIME files in this pass. Non-PRIME skill docs (like
        # README.md if any) are not part of the Agent Skills spec migration.
        return ("skipped-not-prime", f"filename {stem} does not match *_PRIME")

    name = filename_to_spec_name(stem)
    description = extract_description(content)
    registry_entry = registry.get(stem)
    frontmatter = build_frontmatter(name, description, registry_entry)

    new_content = frontmatter + content
    if apply:
        md_path.write_text(new_content, encoding="utf-8")
    return ("migrated", f"name={name}, desc_len={len(description)}")


def snapshot_backup(skills_dir: Path, backup_root: Path) -> Path:
    """Copy every *.md file (not JSON) into a timestamped backup dir."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    target = backup_root / f"skills-pre-migration-{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    for md in skills_dir.glob("*.md"):
        shutil.copy2(md, target / md.name)
    # Also back up the registry so we can round-trip if needed
    reg = skills_dir / DEFAULT_REGISTRY
    if reg.exists():
        shutil.copy2(reg, target / DEFAULT_REGISTRY)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write frontmatter to files. Default is dry-run (preview only).",
    )
    parser.add_argument(
        "--skills-dir",
        default=str(DEFAULT_SKILLS_DIR),
        help=f"Override skills directory (default: {DEFAULT_SKILLS_DIR}).",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Path to skill_registry.json (default: <skills_dir>/skill_registry.json).",
    )
    parser.add_argument(
        "--backup-root",
        default=str(Path(__file__).resolve().parents[1] / "archives"),
        help="Where to write pre-migration backups when --apply is set.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the pre-migration backup (not recommended; --apply only).",
    )
    args = parser.parse_args(argv)

    skills_dir = Path(args.skills_dir).resolve()
    if not skills_dir.is_dir():
        print(f"migrate_skills: skills dir not found: {skills_dir}", file=sys.stderr)
        return 2

    registry_path = Path(args.registry) if args.registry else skills_dir / DEFAULT_REGISTRY
    registry: dict = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"migrate_skills: could not parse {registry_path}: {exc}", file=sys.stderr)
            return 2
    else:
        print(f"migrate_skills: no registry at {registry_path}; metadata will be sparse.", file=sys.stderr)

    md_files = sorted(skills_dir.glob("*.md"))
    if not md_files:
        print(f"migrate_skills: no .md files in {skills_dir}", file=sys.stderr)
        return 2

    # Backup before any writes
    if args.apply and not args.no_backup:
        backup_path = snapshot_backup(skills_dir, Path(args.backup_root))
        print(f"[migrate_skills] backup written to {backup_path}", file=sys.stderr)

    counts = {
        "migrated": 0,
        "already-has-frontmatter": 0,
        "skipped-not-prime": 0,
        "error": 0,
    }
    errors: list[str] = []

    for md in md_files:
        try:
            status, detail = migrate_file(md, registry, apply=args.apply)
        except Exception as exc:  # noqa: BLE001 — best-effort migration; collect failures
            status = "error"
            detail = f"exception: {exc}"
            errors.append(f"{md.name}: {detail}")
        counts[status] = counts.get(status, 0) + 1
        marker = "✓" if args.apply else "·"
        print(f"  {marker} {md.name}: {status} ({detail})")

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(
        f"\n[migrate_skills] {mode}: "
        f"migrated={counts['migrated']} "
        f"already={counts['already-has-frontmatter']} "
        f"skipped={counts['skipped-not-prime']} "
        f"errors={counts['error']}",
        file=sys.stderr,
    )
    if errors:
        print("\n[migrate_skills] errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
