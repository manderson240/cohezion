#!/usr/bin/env python3
"""Convert PRIME skills to Hermes skill format.

This script reads PRIME .md files from src/cohezion/skills/ and converts
them to Hermes-compatible format in ~/.hermes/skills/.

Usage:
    python scripts/prime_to_hermes_converter.py
    python scripts/prime_to_hermes_converter.py --skill COMPOUND_ENGINEERING_PRIME
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


def parse_prime_skill(skill_path: Path) -> dict:
    """Parse a PRIME skill file into structured data.

    Extracts YAML frontmatter, sections (Domain Expertise, Instructions, etc.),
    and metadata from PRIME-formatted markdown files.

    Args:
        skill_path: Path to the .md file (e.g., COMPOUND_ENGINEERING_PRIME.md).

    Returns:
        Parsed skill data as a dictionary with keys:
        - name: Skill name
        - legacy_name: Original PRIME filename
        - description: Skill description
        - domain_expertise: Expertise section content
        - concepts: Key concepts section
        - instructions: Instruction section content
        - version: Skill version
        - see_also: Cross-references
        - full_text: Complete original text

    Example:
        >>> data = parse_prime_skill(Path("COMPOUND_ENGINEERING_PRIME.md"))
        >>> data["name"]
        'compound-engineering'
    """
    text = skill_path.read_text(encoding="utf-8")

    # Extract components using helper functions
    metadata = extract_yaml_frontmatter(text)
    sections = extract_sections(text)

    # Extract skill name
    skill_name = extract_skill_name(metadata, text)

    # Extract domain expertise and instructions
    domain_expertise = sections.get("DOMAIN_EXPERTISE", "")
    instructions = sections.get("INSTRUCTION", sections.get("INSTRUCTION_SET", ""))

    # Extract version
    version = extract_version(metadata, sections)

    return {
        "name": skill_name,
        "legacy_name": skill_path.stem,
        "description": metadata.get("description", domain_expertise[:200] if domain_expertise else ""),
        "domain_expertise": domain_expertise,
        "concepts": sections.get("KEY_TEXTS_&_CONCEPTS", ""),
        "instructions": instructions,
        "version": version,
        "see_also": sections.get("SEE_ALSO", ""),
        "full_text": text,
    }


def convert_to_hermes_format(skill_data: dict) -> str:
    """Convert PRIME skill data to Hermes format.

    Args:
        skill_data: Parsed PRIME skill data

    Returns:
        Hermes-formatted skill content
    """
    name = skill_data["name"]
    if not name or name == "-":
        name = skill_data["legacy_name"].lower().replace("_prime", "")

    # Ensure name starts with cohezion-
    if not name.startswith("cohezion-"):
        name = f"cohezion-{name}"

    description = skill_data["description"]
    if len(description) > 150:
        description = description[:147] + "..."

    concepts = skill_data.get("concepts", "")
    if concepts:
        concepts = concepts.strip()

    instructions = skill_data.get("instructions", "")
    if instructions:
        instructions = instructions.strip()

    see_also = skill_data.get("see_also", "")

    return f"""---
name: {name}
description: {description}
metadata:
  version: "{skill_data['version']}"
  project: cohezion
  legacy-name: {skill_data['legacy_name']}
  converted: true
  tags:
    - cohezion
    - compound-engineering
---

# SKILL: {name}

## Domain Expertise
{skill_data['domain_expertise']}

## Key Concepts
{concepts}

## Instructions
{instructions}

## Version
v{skill_data['version']} — Converted from {skill_data['legacy_name']}

## See Also
{see_also}

## Notes
This skill was auto-converted from the PRIME skill system.
Refer to src/cohezion/skills/{skill_data['legacy_name']}.md for full original content.
"""


def find_skills_dir() -> Path | None:
    """Find the Cohezion skills directory."""
    candidates = [
        Path.cwd() / "src" / "cohezion" / "skills",
        Path.home() / "Projects" / "cohezion" / "src" / "cohezion" / "skills",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def extract_yaml_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown text.

    Returns:
        Parsed YAML metadata or empty dict on error.
    """
    if not text.startswith("---"):
        return {}

    match = re.search(r"---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def extract_sections(text: str) -> dict:
    """Extract ## sections from markdown.

    Returns:
        Dict mapping section names to content.
    """
    sections = {}
    current_section = None
    content_lines = []

    for line in text.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_section:
                sections[current_section] = "\n".join(content_lines).strip()
            # Start new section
            current_section = line[3:].strip().upper().replace(" ", "_")
            content_lines = []
        elif current_section:
            content_lines.append(line)

    # Save final section
    if current_section:
        sections[current_section] = "\n".join(content_lines).strip()

    return sections


def extract_skill_name(metadata: dict, text: str) -> str:
    """Extract skill name from metadata or title.

    Priority:
    1. metadata["name"]
    2. # SKILL: header
    3. Filename (fallback)
    """
    if metadata.get("name"):
        return metadata["name"]

    title_match = re.search(r"#\s*SKILL:\s*(\S+)", text)
    if title_match:
        return title_match.group(1).lower().replace("_prime", "")

    return ""


def extract_version(metadata: dict, sections: dict) -> str:
    """Extract version from metadata or VERSION section."""
    version = metadata.get("metadata", {}).get("version", "")
    if version:
        return version

    if "VERSION" in sections:
        version_match = re.search(r"v?([\d.]+)", sections["VERSION"])
        if version_match:
            return version_match.group(1)

    return "1.0"


def verify_geometric_correspondences():
    """Verify that converted skills match geometric constants (dogfooding)."""
    skill_base = Path.home() / ".hermes/skills"

    if not skill_base.exists():
        print("Error: No skills directory found for verification")
        sys.exit(1)

    # Find all cohezion skills
    skill_files = list(skill_base.rglob("cohezion-*/SKILL.md"))

    if not skill_files:
        print("No cohezion skills found for verification")
        sys.exit(0)

    print("Verifying geometric correspondences...")
    print()

    checks_passed = 0
    checks_total = 0

    for skill_path in skill_files:
        skill_name = skill_path.parent.name
        with open(skill_path) as f:
            content = f.read()

        # Check for 0.5 (HIHO)
        has_point_five = "0.5" in content
        checks_total += 1
        if has_point_five:
            checks_passed += 1

        # Check for 256 (FLUME)
        has_256 = "256" in content
        checks_total += 1
        if has_256:
            checks_passed += 1

        # Check for coherence
        has_coherence = "coherence" in content.lower()
        checks_total += 1
        if has_coherence:
            checks_passed += 1

        print(f"{skill_name}:")
        print(f"  0.5 threshold: {'✓' if has_point_five else '✗'}")
        print(f"  256 dimension: {'✓' if has_256 else '✗'}")
        print(f"  coherence ref: {'✓' if has_coherence else '✗'}")
        print()

    # Calculate HIHO score
    coherence = checks_passed / checks_total if checks_total else 0
    hiho = 1.0 - abs(coherence - 0.5) * 2

    print(f"Verification: {checks_passed}/{checks_total} checks passed")
    print(f"Coherence: {coherence:.2f} ({'HIHO-stable' if 0.4 <= coherence <= 0.7 else 'unstable'})")
    print(f"HIHO score: {hiho:.2f}")

    if hiho >= 0.7:
        print("✓ Skills are geometrically consistent")
        sys.exit(0)
    else:
        print("⚠ Some geometric constants missing")
        sys.exit(1)


def generate_output_name(skill_data: dict, fallback_name: str = "") -> str:
    """Generate sanitized output name for skill."""
    name = skill_data.get("name", "")
    if not name or name == "cohezion-":
        name = f"cohezion-{fallback_name.lower().replace('_prime', '')}"
    return name if name else "cohezion-skill"


def write_skill_file(output_name: str, content: str) -> Path:
    """Write skill content to appropriate directory."""
    # Determine category from content
    if "mlops" in content.lower() and "flume" in content.lower():
        category = "mlops"
    else:
        category = "software-development"

    output_dir = Path.home() / ".hermes" / "skills" / category
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{output_name}.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert PRIME skills to Hermes format"
    )
    parser.add_argument(
        "--skill",
        help="Specific skill to convert (e.g., COMPOUND_ENGINEERING_PRIME)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available PRIME skills",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify converted skills match geometric constants",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show output without writing files",
    )

    args = parser.parse_args()

    if args.verify:
        verify_geometric_correspondences()
        return

    skills_dir = find_skills_dir()
    if not skills_dir:
        print("Error: Could not find Cohezion skills directory")
        sys.exit(1)

    if args.list:
        print(f"Available PRIME skills in {skills_dir}:")
        for md_file in sorted(skills_dir.glob("*_PRIME.md")):
            print(f"  - {md_file.stem}")
        return

    if args.skill:
        skill_path = skills_dir / f"{args.skill}.md"
        if not skill_path.exists():
            print(f"Error: Skill not found: {skill_path}")
            sys.exit(1)

        skill_data = parse_prime_skill(skill_path)
        hermes_content = convert_to_hermes_format(skill_data)

        if args.dry_run:
            print(hermes_content)
        else:
            output_name = generate_output_name(skill_data, args.skill)
            output_path = write_skill_file(output_name, hermes_content)
            print(f"Converted: {skill_path} -> {output_path}")
    else:
        # Convert all PRIME skills
        converted = 0
        for md_file in sorted(skills_dir.glob("*_PRIME.md")):
            skill_data = parse_prime_skill(md_file)
            hermes_content = convert_to_hermes_format(skill_data)

            if args.dry_run:
                print(f"\n=== {md_file.stem} ===")
                print(hermes_content[:500] + "...")
            else:
                output_dir = Path.home() / ".hermes" / "skills" / "software-development"
                output_dir.mkdir(parents=True, exist_ok=True)

                output_name = skill_data["name"]
                if not output_name or output_name == "cohezion-":
                    output_name = f"cohezion-{md_file.stem.lower().replace('_prime', '')}"

                output_path = output_dir / f"{output_name}.md"
                output_path.write_text(hermes_content, encoding="utf-8")
                print(f"Converted: {md_file.name} -> {output_name}")
                converted += 1

        if not args.dry_run:
            print(f"\nConverted {converted} skills")


if __name__ == "__main__":
    main()
