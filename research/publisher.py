"""Vault publisher module — generates inbox notes and daily digest."""

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

from research.pipeline import Finding

logger = logging.getLogger(__name__)

AREA_DISPLAY_NAMES = {
    "compound_engineering": "Compound Engineering",
    "token_efficiency": "Token Efficiency",
    "context_awareness": "Context Awareness",
    "app_creation": "App Creation",
}

VAULT_TARGET_MAP = {
    "compound_engineering": "patterns",
    "token_efficiency": "concepts",
    "context_awareness": "concepts",
    "app_creation": "patterns",
}


def _slugify(text: str, max_len: int = 60) -> str:
    """Convert text to URL-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug).strip("-")
    return slug[:max_len]


def create_inbox_notes(
    findings: list[Finding],
    skill_results: list[dict[str, Any]],
    config: dict[str, Any],
    seen_urls: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Create inbox note content for each finding."""
    pub_config = config.get("publishing", {})
    max_notes = pub_config.get("max_inbox_notes", 40)
    today = date.today().isoformat()
    seen = seen_urls or {}

    # Build skill lookup by URL
    skill_lookup: dict[str, dict] = {}
    for sr in skill_results:
        f = sr["finding"]
        skill_lookup[f.url] = sr

    notes = []
    for finding in findings[:max_notes]:
        if finding.url in seen:
            continue

        slug = _slugify(finding.title)
        filename = f"research-{today}-{slug}.md"

        skill_info = skill_lookup.get(finding.url, {})
        is_skill = skill_info.get("skill_candidate", False)
        skill_type = skill_info.get("skill_type")
        vault_target = VAULT_TARGET_MAP.get(finding.category, "concepts")
        area_display = AREA_DISPLAY_NAMES.get(finding.category, finding.category)

        tags = f"[research, {finding.category}, {finding.source}]"

        content = f"""---
title: "Finding: {finding.title}"
date: {today}
status: new
triage_status: new
tags: {tags}
source_url: {finding.url}
relevance_score: {finding.raw_score:.1f}
skill_candidate: {str(is_skill).lower()}
skill_type: {skill_type or 'null'}
vault_target: {vault_target}
---

## Summary
{finding.snippet}

## Source
[{finding.title}]({finding.url}) — via {finding.source}

## Relevance to Cohezion
- **{area_display}**: Score {finding.raw_score:.1f}/10
"""

        if is_skill:
            content += f"""
## Skill Integration Path
- **Type:** {skill_type}
- **Action:** Review finding → `/learn` to extract skill → `/vault` to share
"""

        content += """
## Potential Integration
<!-- Triage: How might this be integrated into Cohezion? -->
"""

        notes.append({
            "filename": filename,
            "content": content,
            "url": finding.url,
            "category": finding.category,
        })

    return notes


def create_digest(
    findings: list[Finding],
    skill_results: list[dict[str, Any]],
    metadata: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Create the daily digest note."""
    today = date.today().isoformat()

    # Group findings by category
    by_category: dict[str, list[Finding]] = {}
    for f in findings:
        by_category.setdefault(f.category, []).append(f)

    # Build skill candidates table
    skill_rows = []
    for sr in skill_results:
        if sr.get("skill_candidate"):
            f = sr["finding"]
            slug = _slugify(f.title)
            note_ref = f"research-{today}-{slug}"
            skill_rows.append(
                f"| [[{note_ref}]] | {sr.get('skill_type', 'unknown')} "
                f"| {AREA_DISPLAY_NAMES.get(f.category, f.category)} "
                f"| {f.raw_score:.1f}/10 | /learn to extract |"
            )

    # Build per-area sections
    area_sections = ""
    for area_name, display_name in AREA_DISPLAY_NAMES.items():
        area_findings = by_category.get(area_name, [])
        if not area_findings:
            continue
        area_sections += f"\n#### {display_name}\n"
        for i, f in enumerate(area_findings[:10], 1):
            slug = _slugify(f.title)
            note_ref = f"research-{today}-{slug}"
            area_sections += f"{i}. [[{note_ref}]] — Score {f.raw_score:.1f}/10 — {f.snippet[:80]}\n"

    # Build full findings table
    findings_table = "| # | Title | Source | Score | Focus Area |\n|---|-------|--------|-------|------------|\n"
    for i, f in enumerate(findings, 1):
        findings_table += f"| {i} | {f.title[:50]} | {f.source} | {f.raw_score:.1f} | {f.category} |\n"

    skill_section = ""
    if skill_rows:
        skill_section = (
            "\n### Skill Candidates (Ready for /learn → /vault)\n"
            "| Finding | Type | Focus Area | Score | Action |\n"
            "|---------|------|------------|-------|--------|\n"
            + "\n".join(skill_rows)
            + "\n"
        )

    content = f"""---
title: "Research Digest: {today}"
date: {today}
tags: [research, digest, daily]
---

## Research Digest — {today}

**Raw findings:** {metadata.get('total_findings', 0)}
**After scoring:** {metadata.get('top_n_selected', len(findings))}
**Inbox notes created:** {len(findings)}
{skill_section}
### Top Findings by Focus Area
{area_sections}
### All Findings (Scored)
{findings_table}
"""

    filename = f"{today}-research-digest.md"
    return {"filename": filename, "content": content}


def load_seen_urls(path: Path) -> dict[str, str]:
    """Load the seen URLs index."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_seen_urls(path: Path, seen: dict[str, str]) -> None:
    """Save the seen URLs index."""
    existing = load_seen_urls(path)
    existing.update(seen)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)


def publish(
    findings: list[Finding],
    skill_results: list[dict[str, Any]],
    metadata: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Write inbox notes and digest to vault directories."""
    pub_config = config.get("publishing", {})
    vault_path = Path(pub_config.get("vault_path", "."))
    inbox_dir = vault_path / "inbox"
    daily_dir = vault_path / "daily"

    # Load dedup index
    seen_file = vault_path / "research" / "seen_urls.json"
    seen = load_seen_urls(seen_file) if seen_file.exists() else {}

    # Create inbox notes
    notes = create_inbox_notes(findings, skill_results, config, seen_urls=seen)
    for note in notes:
        note_path = inbox_dir / note["filename"]
        note_path.write_text(note["content"])
        seen[note["url"]] = note["filename"]

    # Save updated dedup index
    if notes:
        seen_file.parent.mkdir(parents=True, exist_ok=True)
        save_seen_urls(seen_file, seen)

    # Create digest
    digest = create_digest(findings, skill_results, metadata, config)
    digest_path = daily_dir / digest["filename"]
    digest_path.write_text(digest["content"])

    result = {
        "inbox_notes_created": len(notes),
        "digest_created": True,
        "digest_path": str(digest_path),
    }
    logger.info("Published %d inbox notes and digest to %s", len(notes), vault_path)
    return result
