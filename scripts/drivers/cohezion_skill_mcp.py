from pathlib import Path

from mcp.server.fastmcp import FastMCP


# Initialize FastMCP for Cohezion Skills
mcp = FastMCP("CohezionSkillMCP")

SKILLS_DIR = Path("src/cohezion/skills")


@mcp.tool()
def list_available_skills() -> list[str]:
    """Lists all available skills in the Cohezion registry."""
    if not SKILLS_DIR.exists():
        return []
    return [f.stem for f in SKILLS_DIR.glob("*.md")]


@mcp.tool()
def read_skill_content(skill_name: str) -> str:
    """Reads the full instruction content for a specific skill."""
    skill_path = SKILLS_DIR / f"{skill_name}.md"
    if not skill_path.exists():
        return f"Error: Skill '{skill_name}' not found."
    return skill_path.read_text()


@mcp.tool()
def search_skills_by_concept(concept: str) -> list[str]:
    """Search for skills that contain a specific concept or keyword."""
    if not SKILLS_DIR.exists():
        return []

    matches = []
    for f in SKILLS_DIR.glob("*.md"):
        content = f.read_text().lower()
        if concept.lower() in content:
            matches.append(f.stem)
    return matches


@mcp.tool()
def register_discovered_skill(name: str, description: str, instructions: str) -> str:
    """Registrates a new reasoning pattern discovered during simulation as a persistent skill."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skill_path = SKILLS_DIR / f"{name}.md"

    content = f"""# SKILL: {name}

## DOMAIN EXPERTISE
{description}

## INSTRUCTION
{instructions}

## VERSION
v0.1
"""
    skill_path.write_text(content)
    return f"Successfully registered skill: {name} at {skill_path}"


if __name__ == "__main__":
    mcp.run()
