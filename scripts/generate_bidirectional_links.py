#!/usr/bin/env python3
"""Generate bidirectional links for Cohezion documentation and code.

This script scans the codebase and creates bidirectional links between:
- Documentation files (DESIGN.md ↔ CLAUDE.md ↔ GEMINI.md ↔ AGENTS.md)
- Documentation ↔ Code (DESIGN.md ↔ tip_of_spear_router.py)
- PRIME Skills ↔ Implementations (SMALL_MODEL_SPECIALIST_PRIME.md ↔ router.py)
- Vault Decisions ↔ Code (decision/*.md ↔ code files)

Usage:
    uv run python scripts/generate_bidirectional_links.py

    # Dry run (don't persist)
    uv run python scripts/generate_bidirectional_links.py --dry-run

    # Specific linking patterns only
    uv run python scripts/generate_bidirectional_links.py --only-docs
    uv run python scripts/generate_bidirectional_links.py --only-skills
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_doc_to_doc_links(kg: Any, project_root: Path, dry_run: bool) -> int:
    """Generate links between documentation files."""
    docs = {
        "DESIGN.md": project_root / "DESIGN.md",
        "CLAUDE.md": project_root / "CLAUDE.md",
        "GEMINI.md": project_root / "GEMINI.md",
        "AGENTS.md": project_root / "AGENTS.md",
        ".agent/CONSTITUTION.md": project_root / ".agent" / "CONSTITUTION.md",
        ".agent/COHEZION_CHARTER.md": project_root / ".agent" / "COHEZION_CHARTER.md",
    }

    # Define relationships
    relationships = [
        # DESIGN.md ↔ Other docs
        (
            "DESIGN.md",
            "CLAUDE.md",
            "DESIGN.md provides theoretical foundation for CLAUDE.md operational patterns",
        ),
        (
            "DESIGN.md",
            "GEMINI.md",
            "DESIGN.md provides architecture overview for GEMINI.md workflows",
        ),
        (
            "DESIGN.md",
            "AGENTS.md",
            "DESIGN.md explains design principles for AGENTS.md coding guidelines",
        ),
        ("DESIGN.md", ".agent/CONSTITUTION.md", "DESIGN.md references constitutional hard lines"),
        ("DESIGN.md", ".agent/COHEZION_CHARTER.md", "DESIGN.md builds on 400-year physics lineage"),
        # CLAUDE.md ↔ Other docs
        (
            "CLAUDE.md",
            "GEMINI.md",
            "Cross-agent coherence: Claude and Gemini share provider architecture",
        ),
        (
            "CLAUDE.md",
            "AGENTS.md",
            "CLAUDE.md provides Claude-specific patterns, AGENTS.md provides agent-agnostic patterns",
        ),
        # GEMINI.md ↔ Other docs
        (
            "GEMINI.md",
            "AGENTS.md",
            "GEMINI.md provides Gemini-specific patterns, AGENTS.md provides agent-agnostic patterns",
        ),
        # Constitutional docs
        (
            ".agent/CONSTITUTION.md",
            ".agent/COHEZION_CHARTER.md",
            "Constitution enforces Charter principles",
        ),
    ]

    count = 0
    for source_key, target_key, reason in relationships:
        source = docs.get(source_key)
        target = docs.get(target_key)

        if source and source.exists() and target and target.exists():
            logger.info(f"Linking: {source_key} ↔ {target_key}")
            if not dry_run:
                from cohezion.knowledge_graph import link_doc_to_doc

                await link_doc_to_doc(str(source), str(target), reason)
            count += 1

    return count


async def generate_doc_to_code_links(kg: Any, project_root: Path, dry_run: bool) -> int:
    """Generate links from documentation to code implementations."""
    # Scan DESIGN.md for code references
    design_md = project_root / "DESIGN.md"
    if not design_md.exists():
        return 0

    content = design_md.read_text()

    # Extract code file references (e.g., `src/cohezion/swarm/tip_of_spear_router.py`)
    code_file_pattern = r"`(src/cohezion/[^`]+\.py)`"
    matches = re.findall(code_file_pattern, content)

    count = 0
    for code_file_rel in set(matches):  # Unique files only
        code_file = project_root / code_file_rel

        if code_file.exists():
            logger.info(f"Linking: DESIGN.md → {code_file_rel}")
            if not dry_run:
                from cohezion.knowledge_graph import link_doc_to_code

                # Find section that references this file
                section = _find_section_for_code(content, code_file_rel)
                await link_doc_to_code(str(design_md), str(code_file), section)
            count += 1

    # Similarly for CLAUDE.md
    claude_md = project_root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text()
        matches = re.findall(code_file_pattern, content)

        for code_file_rel in set(matches):
            code_file = project_root / code_file_rel

            if code_file.exists():
                logger.info(f"Linking: CLAUDE.md → {code_file_rel}")
                if not dry_run:
                    from cohezion.knowledge_graph import link_doc_to_code

                    section = _find_section_for_code(content, code_file_rel)
                    await link_doc_to_code(str(claude_md), str(code_file), section)
                count += 1

    return count


async def generate_skill_to_code_links(kg: Any, project_root: Path, dry_run: bool) -> int:
    """Generate links from PRIME skills to implementations."""
    skills_dir = project_root / "src" / "cohezion" / "skills"
    if not skills_dir.exists():
        return 0

    # Find all PRIME skill files
    skill_files = list(skills_dir.glob("*_PRIME.md"))

    count = 0
    for skill_file in skill_files:
        skill_name = skill_file.stem.replace("_PRIME", "")

        # Find corresponding implementation
        # Example: SMALL_MODEL_SPECIALIST_PRIME.md → tip_of_spear_router.py
        impl_mapping = {
            "SMALL_MODEL_SPECIALIST": "src/cohezion/swarm/tip_of_spear_router.py",
            "AGENT_SOVEREIGNTY_ETHICS": "src/cohezion/security/pipeline.py",
            # Add more mappings as needed
        }

        impl_path_rel = impl_mapping.get(skill_name)
        if impl_path_rel:
            impl_path = project_root / impl_path_rel

            if impl_path.exists():
                logger.info(f"Linking: {skill_file.name} → {impl_path_rel}")
                if not dry_run:
                    from cohezion.knowledge_graph import link_skill_to_code

                    await link_skill_to_code(str(skill_file), str(impl_path))
                count += 1

    return count


async def generate_vault_to_code_links(
    kg: Any, vault_root: Path, project_root: Path, dry_run: bool
) -> int:
    """Generate links from vault decisions/patterns to code."""
    if not vault_root.exists():
        logger.warning(f"Vault not found at {vault_root}")
        return 0

    count = 0

    # Link decisions to code
    decisions_dir = vault_root / "decisions"
    if decisions_dir.exists():
        for decision_file in decisions_dir.glob("*.md"):
            # Parse decision file for code references
            content = decision_file.read_text()
            code_file_pattern = r"`(src/cohezion/[^`]+\.py)`"
            matches = re.findall(code_file_pattern, content)

            for code_file_rel in set(matches):
                code_file = project_root / code_file_rel

                if code_file.exists():
                    logger.info(f"Linking: vault/{decision_file.name} → {code_file_rel}")
                    if not dry_run:
                        from cohezion.knowledge_graph import link_decision_to_code

                        await link_decision_to_code(
                            str(decision_file),
                            str(code_file),
                            f"Decision documented in {decision_file.name}",
                        )
                    count += 1

    # Link patterns to code
    patterns_dir = vault_root / "patterns"
    if patterns_dir.exists():
        for pattern_file in patterns_dir.glob("*.md"):
            content = pattern_file.read_text()
            code_file_pattern = r"`(src/cohezion/[^`]+\.py)`"
            matches = re.findall(code_file_pattern, content)

            for code_file_rel in set(matches):
                code_file = project_root / code_file_rel

                if code_file.exists():
                    logger.info(f"Linking: vault/{pattern_file.name} → {code_file_rel}")
                    if not dry_run:
                        from cohezion.knowledge_graph import link_pattern_to_code

                        await link_pattern_to_code(str(pattern_file), str(code_file))
                    count += 1

    return count


def _find_section_for_code(content: str, code_file: str) -> str:
    """Find the section (heading) that references this code file."""
    lines = content.split("\n")
    current_section = "General"

    for line in lines:
        # Track headings (## Section Name)
        if line.startswith("##"):
            current_section = line.strip("# ").strip()

        # Check if this line references the code file
        if code_file in line:
            return current_section

    return "General"


async def main():
    """Generate all bidirectional links."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate bidirectional links for Cohezion")
    parser.add_argument("--dry-run", action="store_true", help="Don't persist links, just print")
    parser.add_argument("--only-docs", action="store_true", help="Only link documentation")
    parser.add_argument("--only-skills", action="store_true", help="Only link skills")
    parser.add_argument("--only-vault", action="store_true", help="Only link vault")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    vault_root = Path.home() / "vaults" / "cohezion-vault"

    logger.info(f"Project root: {project_root}")
    logger.info(f"Vault root: {vault_root}")

    if args.dry_run:
        logger.info("DRY RUN: Not persisting links")

    # Initialize knowledge graph
    from cohezion.knowledge_graph import get_knowledge_graph

    kg = get_knowledge_graph()

    if not args.dry_run:
        try:
            await kg.connect()
            await kg.load_from_vault()
            logger.info("Connected to knowledge graph")
        except Exception as e:
            logger.error(f"Failed to connect to knowledge graph: {e}")
            logger.info("Proceeding with in-memory links only")

    # Generate links
    total_links = 0

    if args.only_docs or not (args.only_skills or args.only_vault):
        logger.info("\n=== Generating DOC ↔ DOC links ===")
        count = await generate_doc_to_doc_links(kg, project_root, args.dry_run)
        logger.info(f"Generated {count} doc-to-doc links\n")
        total_links += count

        logger.info("\n=== Generating DOC → CODE links ===")
        count = await generate_doc_to_code_links(kg, project_root, args.dry_run)
        logger.info(f"Generated {count} doc-to-code links\n")
        total_links += count

    if args.only_skills or not (args.only_docs or args.only_vault):
        logger.info("\n=== Generating SKILL → CODE links ===")
        count = await generate_skill_to_code_links(kg, project_root, args.dry_run)
        logger.info(f"Generated {count} skill-to-code links\n")
        total_links += count

    if args.only_vault or not (args.only_docs or args.only_skills):
        logger.info("\n=== Generating VAULT → CODE links ===")
        count = await generate_vault_to_code_links(kg, vault_root, project_root, args.dry_run)
        logger.info(f"Generated {count} vault-to-code links\n")
        total_links += count

    logger.info(f"\n✅ Total bidirectional links generated: {total_links}")

    if not args.dry_run:
        logger.info("Links persisted to:")
        logger.info(f"  - SurrealDB: {kg.surreal_url}")
        logger.info(f"  - Vault: {vault_root}/links/")


if __name__ == "__main__":
    asyncio.run(main())
