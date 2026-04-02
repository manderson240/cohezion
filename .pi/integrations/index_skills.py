#!/usr/bin/env python3
"""
Index Cohezion's 195 PRIME skills for pi integration.

Creates:
- .pi/integrations/skill_index.json: Queryable skill metadata
- .pi/integrations/skill_embeddings.jsonl: Semantic vectors for fuzzy search
- .pi/integrations/skill_graph.json: Dependency graph between skills

Usage:
    uv run python .pi/integrations/index_skills.py

Non-destructive: Only reads skills/, writes index files to .pi/integrations/
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SKILLS_DIR = Path("src/cohezion/skills")
OUTPUT_DIR = Path(".pi/integrations")


@dataclass
class SkillGenome:
    """A PRIME skill as a living genome."""

    content_hash: str
    file_path: Path
    name: str
    description: str
    version: str
    frontmatter: dict[str, Any]
    instructions: list[str]
    patterns: list[str]
    citations: list[str]
    see_also: list[str]
    fitness: float = 0.0  # Calculated from version/refinement count


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract simple YAML-like frontmatter from markdown (no external deps)."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1].strip()
            body = parts[2]
            
            # Simple line-by-line parsing
            frontmatter = {}
            current_key = None
            for line in frontmatter_text.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Key: value
                if ':' in line and not line.startswith('-'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    frontmatter[key] = value
                    current_key = key
                # Continuation of multi-line
                elif current_key and line:
                    frontmatter[current_key] = frontmatter.get(current_key, '') + ' ' + line
            
            return frontmatter, body
    return {}, content


def extract_sections(body: str) -> dict[str, Any]:
    """Extract ## sections from markdown body."""
    sections = {}
    current_section = None
    current_content = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def calculate_fitness(file_path: Path, sections: dict) -> float:
    """Calculate skill fitness from refinement evidence."""
    fitness = 0.5  # Base

    # More citations = more battle-tested = higher fitness
    if "CITATIONS" in sections:
        citations = sections["CITATIONS"].split("\n")
        fitness += min(len(citations) * 0.05, 0.2)

    # SEE ALSO indicates ecosystem integration
    if "SEE ALSO" in sections:
        see_alsos = sections["SEE ALSO"].split("\n")
        fitness += min(len(see_alsos) * 0.02, 0.1)

    # Version implies evolution
    version_match = re.search(r"version[\"']?\s*[:=]\s*[\"']?(\d+\.\d+)", str(file_path))
    if version_match:
        major, minor = map(int, version_match.group(1).split("."))
        fitness += major * 0.1 + minor * 0.01

    return min(fitness, 1.0)


def parse_skill_file(md_file: Path) -> SkillGenome | None:
    """Parse a PRIME skill markdown file into a genome."""
    try:
        content = md_file.read_text()
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        frontmatter, body = parse_frontmatter(content)
        sections = extract_sections(body)

        name = frontmatter.get("name", md_file.stem.replace("_PRIME", ""))
        description = frontmatter.get("description", "")
        
        # Extract version from metadata string or frontmatter directly
        version = "0.1"
        if "version" in frontmatter:
            version = frontmatter["version"].strip('"')
        elif "metadata" in str(frontmatter):
            # Try to extract from metadata string
            meta_match = re.search(r'version:\s*["\']?(\d+\.\d+)', str(frontmatter))
            if meta_match:
                version = meta_match.group(1)

        instructions = sections.get("INSTRUCTION", "")
        # Extract numbered steps
        steps = re.findall(r"^\d+\.\s+(.+)$", instructions, re.MULTILINE)

        patterns = sections.get("PATTERNS", "")
        pattern_list = [
            p.strip() for p in patterns.split("\n") if p.strip().startswith("-")
        ]

        citations = [
            c.strip("-")
            for c in sections.get("CITATIONS", "").split("\n")
            if c.strip().startswith("-") or ".md" in c
        ]

        see_also = [
            s.strip("-")
            for s in sections.get("SEE ALSO", "").split("\n")
            if s.strip().startswith("-") or ".md" in s
        ]

        fitness = calculate_fitness(md_file, sections)

        return SkillGenome(
            content_hash=content_hash,
            file_path=Path("src/cohezion/skills") / md_file.name,
            name=name,
            description=description,
            version=version,
            frontmatter=frontmatter,
            instructions=steps,
            patterns=pattern_list,
            citations=citations,
            see_also=see_also,
            fitness=fitness,
        )
    except Exception as e:
        logger.error(f"Failed to parse {md_file}: {e}")
        return None


def create_index(skills: list[SkillGenome]) -> dict[str, Any]:
    """Create queryable skill index."""
    index = {
        "meta": {
            "count": len(skills),
            "generated_at": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", None, None)),
        },
        "by_name": {},
        "by_category": {},
        "by_version": {},
        "high_fitness": [],  # Fitness > 0.8
        "dependencies": {},
    }

    for skill in skills:
        entry = {
            "hash": skill.content_hash,
            "file": str(skill.file_path),
            "description": skill.description[:200] + "..." if len(skill.description) > 200 else skill.description,
            "version": skill.version,
            "fitness": skill.fitness,
            "patterns": len(skill.patterns),
            "citations": len(skill.citations),
        }

        # By name
        index["by_name"][skill.name] = entry

        # By category (from filename prefix)
        category = skill.file_path.stem.split("_")[0]
        if category not in index["by_category"]:
            index["by_category"][category] = []
        index["by_category"][category].append(skill.name)

        # By version
        if skill.version not in index["by_version"]:
            index["by_version"][skill.version] = []
        index["by_version"][skill.version].append(skill.name)

        # High fitness
        if skill.fitness > 0.8:
            index["high_fitness"].append(skill.name)

        # Dependencies (SEE ALSO links)
        deps = []
        for s in skill.see_also:
            # Extract skill name from "- SKILL_NAME_PRIME.md" or similar
            match = re.search(r"(\w+)_PRIME", s)
            if match:
                deps.append(match.group(1))
        if deps:
            index["dependencies"][skill.name] = deps

    return index


def create_embeddings(skills: list[SkillGenome]) -> list[dict]:
    """Create simple keyword-based embeddings for fuzzy search."""
    embeddings = []

    for skill in skills:
        # Simple TF-like keyword extraction
        text = f"{skill.name} {skill.description} {' '.join(skill.instructions)}"
        words = set(re.findall(r"\b\w+\b", text.lower()))

        embeddings.append({
            "hash": skill.content_hash,
            "name": skill.name,
            "keywords": list(words),
            "fitness": skill.fitness,
        })

    return embeddings


def create_skill_graph(skills: list[SkillGenome]) -> dict[str, Any]:
    """Create dependency graph between skills."""
    nodes = []
    edges = []

    for skill in skills:
        nodes.append({
            "id": skill.name,
            "label": skill.name,
            "fitness": skill.fitness,
            "version": skill.version,
        })

        for dep in skill.see_also:
            match = re.search(r"(\w+)_PRIME", dep)
            if match:
                edges.append({
                    "source": skill.name,
                    "target": match.group(1),
                    "type": "see_also",
                })

        for citation in skill.citations:
            match = re.search(r"(\w+)_PRIME", citation)
            if match:
                edges.append({
                    "source": skill.name,
                    "target": match.group(1),
                    "type": "cites",
                })

    return {"nodes": nodes, "edges": edges}


def main():
    """Main entry point."""
    logger.info(f"Indexing skills from {SKILLS_DIR}...")

    md_files = list(SKILLS_DIR.glob("*.md"))
    logger.info(f"Found {len(md_files)} skill files")

    skills = []
    for md_file in md_files:
        skill = parse_skill_file(md_file)
        if skill:
            skills.append(skill)

    logger.info(f"Successfully parsed {len(skills)} skills")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write index
    index = create_index(skills)
    index_path = OUTPUT_DIR / "skill_index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    logger.info(f"Wrote index: {index_path}")

    # Write embeddings
    embeddings = create_embeddings(skills)
    embeddings_path = OUTPUT_DIR / "skill_embeddings.jsonl"
    with open(embeddings_path, "w") as f:
        for e in embeddings:
            f.write(json.dumps(e) + "\n")
    logger.info(f"Wrote embeddings: {embeddings_path}")

    # Write graph
    graph = create_skill_graph(skills)
    graph_path = OUTPUT_DIR / "skill_graph.json"
    with open(graph_path, "w") as f:
        json.dump(graph, f, indent=2)
    logger.info(f"Wrote graph: {graph_path}")

    # Write human-readable stats
    stats = {
        "total_skills": len(skills),
        "high_fitness": len([s for s in skills if s.fitness > 0.8]),
        "categories": len(set(s.file_path.stem.split("_")[0] for s in skills)),
        "avg_patterns": sum(len(s.patterns) for s in skills) / len(skills) if skills else 0,
        "avg_citations": sum(len(s.citations) for s in skills) / len(skills) if skills else 0,
        "top_skills": sorted(skills, key=lambda s: s.fitness, reverse=True)[:10],
    }

    print("\n" + "=" * 50)
    print("SKILL INDEX COMPLETE")
    print("=" * 50)
    print(f"Total skills indexed: {stats['total_skills']}")
    print(f"High fitness (≥0.8): {stats['high_fitness']}")
    print(f"Categories: {stats['categories']}")
    print(f"Avg patterns per skill: {stats['avg_patterns']:.1f}")
    print(f"Avg citations per skill: {stats['avg_citations']:.1f}")
    print("\nTop 10 skills by fitness:")
    for s in stats["top_skills"]:
        print(f"  - {s.name}: {s.fitness:.2f} (v{s.version})")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
