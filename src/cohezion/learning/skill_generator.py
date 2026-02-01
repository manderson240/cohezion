"""
Skill Generator - Automatically create skills from learned patterns.

Based on:
- HuggingFace CLIN: Continually Learning Language Agent
- Knowledge mining from session logs
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_PATH = Path(__file__).parent.parent / "skills"
PATTERNS_PATH = Path(__file__).parent.parent / "knowledge_graph" / "patterns.json"


@dataclass
class Pattern:
    """A detected pattern that can become a skill."""

    name: str
    description: str
    occurrences: int
    examples: list[str]
    keywords: list[str]
    first_seen: str
    last_seen: str


class PatternDetector:
    """Detect recurring patterns in session logs."""

    def __init__(self):
        self._patterns: dict[str, Pattern] = {}
        self._load()

    def _load(self) -> None:
        if PATTERNS_PATH.exists():
            data = json.loads(PATTERNS_PATH.read_text())
            for name, p in data.get("patterns", {}).items():
                self._patterns[name] = Pattern(**p)

    def _save(self) -> None:
        PATTERNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"patterns": {n: vars(p) for n, p in self._patterns.items()}}
        PATTERNS_PATH.write_text(json.dumps(data, indent=2))

    def record(
        self, pattern_name: str, description: str, example: str, keywords: list[str]
    ) -> Pattern:
        """Record a pattern occurrence."""
        now = datetime.now().isoformat()

        if pattern_name not in self._patterns:
            self._patterns[pattern_name] = Pattern(
                name=pattern_name,
                description=description,
                occurrences=0,
                examples=[],
                keywords=keywords,
                first_seen=now,
                last_seen=now,
            )

        pattern = self._patterns[pattern_name]
        pattern.occurrences += 1
        pattern.last_seen = now
        if example not in pattern.examples:
            pattern.examples.append(example)
            if len(pattern.examples) > 5:
                pattern.examples = pattern.examples[-5:]

        self._save()
        return pattern

    def get_mature_patterns(self, min_occurrences: int = 3) -> list[Pattern]:
        """Get patterns with enough occurrences to become skills."""
        return [p for p in self._patterns.values() if p.occurrences >= min_occurrences]


class SkillGenerator:
    """Generate skills from mature patterns."""

    def __init__(self):
        self.detector = PatternDetector()

    def generate_skill(self, pattern: Pattern) -> Path:
        """Generate a skill file from a pattern."""
        skill_name = pattern.name.upper().replace(" ", "_") + "_PRIME"
        skill_path = SKILLS_PATH / f"{skill_name}.md"

        # Skip if already exists
        if skill_path.exists():
            logger.info(f"Skill {skill_name} already exists")
            return skill_path

        content = f"""# SKILL: {skill_name}

## DOMAIN EXPERTISE
Auto-generated skill from detected pattern: **{pattern.name}**

## DESCRIPTION
{pattern.description}

## INSTRUCTION
Based on {pattern.occurrences} observed occurrences:

### Examples
"""
        for i, ex in enumerate(pattern.examples[:3], 1):
            content += f"\n{i}. {ex}\n"

        content += f"""
## KEYWORDS
{', '.join(pattern.keywords)}

## METADATA
- First observed: {pattern.first_seen}
- Last observed: {pattern.last_seen}
- Occurrences: {pattern.occurrences}
- Auto-generated: {datetime.now().isoformat()}

## VERSION
v0.1 (auto-generated)
"""

        skill_path.write_text(content)
        logger.info(f"Generated skill: {skill_name}")
        return skill_path

    def auto_generate(self, min_occurrences: int = 3) -> list[Path]:
        """Auto-generate skills from all mature patterns."""
        generated = []
        for pattern in self.detector.get_mature_patterns(min_occurrences):
            path = self.generate_skill(pattern)
            generated.append(path)
        return generated


# Singleton
_generator: SkillGenerator | None = None


def get_skill_generator() -> SkillGenerator:
    global _generator
    if _generator is None:
        _generator = SkillGenerator()
    return _generator
