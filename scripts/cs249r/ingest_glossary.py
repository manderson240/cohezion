"""CS249R glossary ingestion.

Parses the global glossary and creates vault note + SurrealDB JSON.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.cs249r.repo_access import CS249RRepo

logger = logging.getLogger(__name__)


def parse_glossary_terms(glossary_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse glossary data and extract terms.

    Args:
        glossary_data: Parsed global glossary JSON

    Returns:
        List of term dicts with term, definition, etc.
    """
    # Glossary structure: {"metadata": {...}, "terms": [...]}
    if isinstance(glossary_data, dict):
        terms = glossary_data.get("terms", [])
    else:
        terms = glossary_data

    return terms


def create_glossary_vault_note(terms: list[dict[str, Any]]) -> str:
    """Create vault-formatted glossary markdown.

    Args:
        terms: List of glossary term dicts

    Returns:
        Formatted markdown with frontmatter
    """
    date = datetime.now().strftime("%Y-%m-%d")

    frontmatter = f"""---
tags: [glossary, ml-systems, cs249r]
source: cs249r/global_glossary
date: {date}
term_count: {len(terms)}
---

"""

    content = "# ML Systems Glossary\n\n"
    content += f"**Source:** CS249R ML Systems Book - Global Glossary\n"
    content += f"**Terms:** {len(terms)}\n\n"

    # Group terms alphabetically
    terms_by_letter: dict[str, list[dict]] = {}
    for term in terms:
        term_name = term.get("term", "Unknown")
        first_letter = term_name[0].upper() if term_name else "?"

        if first_letter not in terms_by_letter:
            terms_by_letter[first_letter] = []

        terms_by_letter[first_letter].append(term)

    # Write grouped terms
    for letter in sorted(terms_by_letter.keys()):
        content += f"## {letter}\n\n"

        for term_dict in sorted(terms_by_letter[letter], key=lambda t: t.get("term", "")):
            term_name = term_dict.get("term", "")
            definition = term_dict.get("definition", "No definition available")

            content += f"**{term_name}**: {definition}\n\n"

    return frontmatter + content


def create_surreal_json(terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create SurrealDB-compatible JSON from glossary terms.

    Args:
        terms: List of glossary term dicts

    Returns:
        List of SurrealDB-ready term records
    """
    surreal_records = []

    for term_dict in terms:
        term_name = term_dict.get("term", "")
        # Create slug for ID
        slug = re.sub(r"[^a-z0-9]+", "-", term_name.lower()).strip("-")

        record = {
            "id": f"glossary:{slug}",
            "term": term_name,
            "definition": term_dict.get("definition", ""),
            "tags": ["glossary", "cs249r", "ml-systems"],
        }

        # Add optional fields if present
        if "chapter" in term_dict:
            record["chapter"] = term_dict["chapter"]

        surreal_records.append(record)

    return surreal_records


def ingest_glossary(output_dir: Path | str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Ingest glossary and create vault note + SurrealDB JSON.

    Args:
        output_dir: Directory to write files. Defaults to vault concepts/cs249r/
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

    # Load glossary from repo
    repo = CS249RRepo()
    glossary_data = repo.load_global_glossary()

    # Parse terms
    terms = parse_glossary_terms(glossary_data)

    # Create vault note
    vault_note = create_glossary_vault_note(terms)

    # Create SurrealDB JSON
    surreal_data = create_surreal_json(terms)

    # Write files
    if not dry_run:
        # Write vault note
        vault_file = output_dir / "ml-systems-glossary.md"
        vault_file.write_text(vault_note)
        logger.info(f"Created glossary vault note: {vault_file}")

        # Write SurrealDB JSON (in data/ directory)
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        surreal_file = data_dir / "cs249r_glossary_surreal.json"
        surreal_file.write_text(json.dumps(surreal_data, indent=2))
        logger.info(f"Created SurrealDB glossary JSON: {surreal_file}")

    stats = {
        "term_count": len(terms),
        "vault_file": "ml-systems-glossary.md",
        "surreal_file": "data/cs249r_glossary_surreal.json",
    }

    return stats


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv

    logging.basicConfig(level=logging.INFO)
    stats = ingest_glossary(dry_run=dry_run)

    print(f"\nGlossary ingestion {'DRY RUN ' if dry_run else ''}complete:")
    print(f"  Terms: {stats['term_count']}")
    print(f"  Vault file: {stats['vault_file']}")
    print(f"  SurrealDB JSON: {stats['surreal_file']}")
