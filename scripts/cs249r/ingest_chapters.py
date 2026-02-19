"""CS249R chapter concept ingestion.

Parses concept YAML files from the book and creates vault-compatible markdown notes.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.cs249r.repo_access import CS249RRepo

logger = logging.getLogger(__name__)


# Domain mapping based on chapter names
CHAPTER_DOMAINS = {
    # Systems Foundations
    "introduction": "foundations",
    "ml_systems": "foundations",
    "dl_primer": "foundations",
    "dnn_architectures": "architectures",
    # Design Principles
    "workflow": "foundations",
    "data_engineering": "data-eng",
    "frameworks": "foundations",
    "training": "foundations",
    # Performance Engineering
    "efficient_ai": "performance",
    "optimizations": "performance",
    "hw_acceleration": "performance",
    "benchmarking": "performance",
    # Robust Deployment
    "ops": "deployment",
    "ondevice_learning": "deployment",
    "privacy_security": "deployment",
    "robust_ai": "trustworthy",
    # Trustworthy Systems
    "responsible_ai": "trustworthy",
    "sustainable_ai": "trustworthy",
    "ai_for_good": "trustworthy",
    # Frontiers
    "frontiers": "frontiers",
    "conclusion": "frontiers",
    # Advanced chapters
    "edge_intelligence": "edge",
    "distributed_training": "edge",
    "fault_tolerance": "edge",
    "inference": "edge",
    "communication": "edge",
    "storage": "edge",
    "infrastructure": "edge",
}


def parse_concept_yaml(concepts: dict[str, Any] | None, chapter_name: str) -> dict[str, Any] | None:
    """Parse concept YAML and extract structured data.

    Args:
        concepts: Parsed YAML dict from chapter concepts file
        chapter_name: Name of the chapter (for domain mapping)

    Returns:
        Dict with parsed concept data or None if concepts is None
    """
    if concepts is None:
        return None

    # Extract concept_map if present
    concept_map = concepts.get("concept_map", concepts)

    # Determine domain from chapter name
    domain = CHAPTER_DOMAINS.get(chapter_name, "foundations")

    return {
        "chapter_name": chapter_name,
        "domain": domain,
        "primary_concepts": concept_map.get("primary_concepts", []),
        "secondary_concepts": concept_map.get("secondary_concepts", []),
        "technical_terms": concept_map.get("technical_terms", []),
        "methodologies": concept_map.get("methodologies", []),
        "applications": concept_map.get("applications", []),
    }


def create_vault_note(concept_data: dict[str, Any]) -> str:
    """Create vault-formatted markdown note from concept data.

    Args:
        concept_data: Parsed concept data dict

    Returns:
        Formatted markdown content with YAML frontmatter
    """
    chapter_name = concept_data["chapter_name"]
    chapter_type = concept_data.get("chapter_type", "core")
    domain = concept_data["domain"]
    date = datetime.now().strftime("%Y-%m-%d")

    # Build YAML frontmatter
    frontmatter = f"""---
tags: [concept, ml-systems, cs249r, {domain}]
source: cs249r/{chapter_type}/{chapter_name}
date: {date}
---

"""

    # Build content sections
    content = f"# {chapter_name.replace('_', ' ').title()}\n\n"
    content += f"**Source:** CS249R ML Systems Book - {chapter_type.title()} Chapter\n\n"

    # Primary concepts
    if concept_data.get("primary_concepts"):
        content += "## Primary Concepts\n\n"
        for concept in concept_data["primary_concepts"]:
            content += f"- {concept}\n"
        content += "\n"

    # Secondary concepts
    if concept_data.get("secondary_concepts"):
        content += "## Secondary Concepts\n\n"
        for concept in concept_data["secondary_concepts"]:
            content += f"- {concept}\n"
        content += "\n"

    # Technical terms
    if concept_data.get("technical_terms"):
        content += "## Technical Terms\n\n"
        for term in concept_data["technical_terms"]:
            content += f"- {term}\n"
        content += "\n"

    # Methodologies
    if concept_data.get("methodologies"):
        content += "## Methodologies\n\n"
        for method in concept_data["methodologies"]:
            content += f"- {method}\n"
        content += "\n"

    # Applications
    if concept_data.get("applications"):
        content += "## Applications\n\n"
        for app in concept_data["applications"]:
            content += f"- {app}\n"
        content += "\n"

    return frontmatter + content


def ingest_all_chapters(output_dir: Path | str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Ingest all chapter concepts and create vault notes.

    Args:
        output_dir: Directory to write vault notes. Defaults to standard vault path.
        dry_run: If True, don't write files, just return stats

    Returns:
        Dict with ingestion statistics
    """
    if output_dir is None:
        output_dir = Path.home() / "vaults" / "cohezion-vault" / "concepts" / "cs249r"
    else:
        output_dir = Path(output_dir)

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    repo = CS249RRepo()
    stats = {
        "core_chapters": 0,
        "advanced_chapters": 0,
        "skipped": 0,
        "total": 0,
    }

    # Process all chapters
    for chapter in repo.chapters:
        chapter_name = chapter["name"]
        chapter_type = chapter["type"]

        # Load concepts
        concepts = repo.load_chapter_concepts(chapter_name, chapter_type=chapter_type)

        if concepts is None:
            logger.warning(f"No concepts file for {chapter_type}/{chapter_name}, skipping")
            stats["skipped"] += 1
            continue

        # Parse concepts
        try:
            concept_data = parse_concept_yaml(concepts, chapter_name)
            if concept_data is None:
                stats["skipped"] += 1
                continue

            concept_data["chapter_type"] = chapter_type

            # Create vault note
            note_content = create_vault_note(concept_data)

            # Write to file (if not dry run)
            if not dry_run:
                filename = f"{chapter_name}.md"
                filepath = output_dir / filename
                filepath.write_text(note_content)
                logger.info(f"Created vault note: {filepath}")

            # Update stats
            if chapter_type == "core":
                stats["core_chapters"] += 1
            else:
                stats["advanced_chapters"] += 1
            stats["total"] += 1

        except Exception as e:
            logger.error(f"Error processing {chapter_type}/{chapter_name}: {e}")
            stats["skipped"] += 1

    return stats


if __name__ == "__main__":
    import sys

    # Simple CLI for dry-run testing
    dry_run = "--dry-run" in sys.argv

    logging.basicConfig(level=logging.INFO)
    stats = ingest_all_chapters(dry_run=dry_run)

    print(f"\nIngestion {'DRY RUN ' if dry_run else ''}complete:")
    print(f"  Core chapters: {stats['core_chapters']}")
    print(f"  Advanced chapters: {stats['advanced_chapters']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Total: {stats['total']}")
