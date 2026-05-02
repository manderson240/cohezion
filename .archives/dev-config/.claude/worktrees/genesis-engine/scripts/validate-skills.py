#!/usr/bin/env python3
"""Validate skill registry and frontmatter."""

import json
import re
import sys
from pathlib import Path


def validate_skills_json(skills_file: Path) -> list[str]:
    """Validate the skills.json file."""
    errors = []

    if not skills_file.exists():
        return ["skills.json not found"]

    try:
        data = json.loads(skills_file.read_text())
    except json.JSONDecodeError as e:
        return [f"Invalid JSON in skills.json: {e}"]

    if not isinstance(data, dict):
        errors.append("skills.json must be a dictionary")
        return errors

    if "skills" not in data:
        errors.append("skills.json must have a 'skills' key")
        return errors

    skills = data["skills"]
    if not isinstance(skills, list):
        errors.append("skills must be a list")
        return errors

    required_fields = ["name", "description"]
    skill_names = []

    for i, skill in enumerate(skills):
        for field in required_fields:
            if field not in skill:
                errors.append(f"Skill {i}: missing required field '{field}'")

        name = skill.get("name")
        if name:
            skill_names.append(name)
            if skill_names.count(name) > 1:
                errors.append(f"Skill {i}: duplicate name '{name}'")

    return errors


def validate_skill_frontmatter(skill_file: Path) -> list[str]:
    """Validate a skill markdown file frontmatter."""
    errors = []
    content = skill_file.read_text()

    if not content.startswith("---"):
        errors.append(f"{skill_file}: Missing frontmatter")
        return errors

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        errors.append(f"{skill_file}: Invalid frontmatter format")
        return errors

    frontmatter = match.group(1)
    required = ["name", "description"]

    for field in required:
        if f"{field}:" not in frontmatter:
            errors.append(f"{skill_file}: Missing '{field}' in frontmatter")

    return errors


def main():
    """Run skill validation."""
    repo_root = Path.cwd()
    skills_file = repo_root / ".claude" / "skills.json"

    all_errors = []

    # Validate skills.json if it exists
    if skills_file.exists():
        all_errors.extend(validate_skills_json(skills_file))

    # Validate skill files
    skills_dir = repo_root / ".claude"
    if skills_dir.exists():
        for skill_file in skills_dir.rglob("*.md"):
            if skill_file.name == "README.md":
                continue
            all_errors.extend(validate_skill_frontmatter(skill_file))

    if all_errors:
        print("Skill validation errors:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("Skill validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
