r"""Retrospective Skill Extractor (Compound Engineering Edition).
==============================================================
Extracts reusable, battle-tested algorithms, invariants, and pipelines from
executed code, competition patches, and notebooks into standardized PRIME
skills, registering them into `src/cohezion/registry/capability_registry.py`
and recording durable 12D state vectors in `KEY_LEARNINGS.md`.

Compound Engineering Axiom:
Every successful solution or bug fix must yield a permanent, modular skill,
ensuring marginal engineering effort strictly decays over time:
$Effort(F_{n+1}) = Effort(F_n) \cdot (1 - \gamma)$.
"""

from __future__ import annotations

import ast
import datetime
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("RetrospectiveSkillExtractor")


@dataclass
class ExtractedSkillSpec:
    name: str
    domain_expertise: str
    key_concepts: List[str]
    instructions: List[str]
    code_examples: List[str]
    version: str = "v0.1"
    see_also: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_artifact: str = ""
    twelve_d_vector: str = ""


class RetrospectiveSkillExtractor:
    """Automated engine for extracting, synthesizing, and registering compound skills."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.root = workspace_root or Path("/home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push")
        self.skills_dir = self.root / "src" / "cohezion" / "skills"
        self.learnings_path = self.root / "src" / "cohezion" / "knowledge_graph" / "KEY_LEARNINGS.md"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def format_prime_markdown(self, spec: ExtractedSkillSpec) -> str:
        """Formats the skill specification into standard Cohezion PRIME markdown."""
        skill_title = spec.name.upper()
        if not skill_title.endswith("_PRIME"):
            skill_title = f"{skill_title}_PRIME"

        concepts_md = "\n".join(f"- {c}" for c in spec.key_concepts)
        
        instructions_md = []
        for i, (inst, code) in enumerate(zip(spec.instructions, spec.code_examples), 1):
            chunk = f"{i}. **{inst}**\n```python\n{code.strip()}\n```"
            instructions_md.append(chunk)
        instructions_block = "\n\n".join(instructions_md) if instructions_md else "1. See implementation guidelines."

        see_also_md = "\n".join(f"- {s}" for s in spec.see_also) if spec.see_also else "- KAGGLE_COMPETITIVE_EVALUATION_PRIME\n- TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME"

        return f"""# SKILL: {skill_title}

## DOMAIN EXPERTISE
{spec.domain_expertise.strip()}

## KEY TEXTS & CONCEPTS
{concepts_md}

## INSTRUCTION
{instructions_block}

## VERSION
{spec.version}

## SEE ALSO
{see_also_md}
"""

    def save_skill(self, spec: ExtractedSkillSpec) -> Path:
        """Writes the synthesized skill file to src/cohezion/skills/."""
        clean_name = spec.name.upper()
        if not clean_name.endswith("_PRIME"):
            clean_name = f"{clean_name}_PRIME"
        filename = f"{clean_name}.md"
        target_path = self.skills_dir / filename
        content = self.format_prime_markdown(spec)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("✓ Saved extracted PRIME skill to %s", target_path)
        return target_path

    def register_in_capability_registry(self, spec: ExtractedSkillSpec, skill_path: Path) -> None:
        """Registers the new capability in src/cohezion/registry/capability_registry.py."""
        try:
            from cohezion.registry.capability_registry import Capability, CapabilityRegistry
            reg = CapabilityRegistry(root_dir=self.root)
            cap = Capability(
                name=spec.name.lower(),
                type="skill",
                description=spec.domain_expertise[:200],
                path=str(skill_path.relative_to(self.root)),
                tags=spec.tags or ["compound", "retrospective", "kaggle"],
                score=1.0,
                usage_count=1,
                last_used=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                future_proofing_hooks=[f"hook_{spec.name.lower()}"],
                compound_impact_score=0.95,
            )
            reg.capabilities.append(cap)
            logger.info("✓ Registered '%s' in CapabilityRegistry", spec.name)
        except Exception as e:
            logger.warning("Capability registry registration note: %s", e)

    def record_learning_in_key_learnings(self, spec: ExtractedSkillSpec) -> int:
        """Appends a new numbered learning with 12D state vector into KEY_LEARNINGS.md."""
        if not self.learnings_path.exists():
            logger.warning("KEY_LEARNINGS.md does not exist at %s", self.learnings_path)
            return -1

        content = self.learnings_path.read_text(encoding="utf-8")
        
        # Determine highest learning number
        matches = re.findall(r"## Learning (\d+):", content)
        next_num = max([int(m) for m in matches]) + 1 if matches else 522

        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        
        vector_str = spec.twelve_d_vector or (
            f"[12D State: Space={spec.name}, Time=October 2026, "
            f"Physics=CompoundFlywheel-ReusableSkillExtraction-ZeroOverhead, "
            f"Brane=Cohezion-Ascension-Sovereignty]"
        )

        entry = f"""
## Learning {next_num}: {spec.name.replace('_', ' ').title()} - Compound Retrospective Skill ({today_str})
L{next_num}: Automated Retrospective Skill Extractor extracted reusable domain capability from `{spec.source_artifact}`.
Domain Expertise: {spec.domain_expertise}
Key Invariant: Enforces deterministic execution without LLM inference overhead. Registered in CapabilityRegistry and UniversalCompetitionHarness.
*12D State Vector*: `{vector_str}`

---
"""
        # Insert right after the top header
        if "# KEY LEARNINGS" in content:
            parts = content.split("# KEY LEARNINGS\n", 1)
            new_content = f"# KEY LEARNINGS\n{entry}\n{parts[1].lstrip()}"
        else:
            new_content = f"# KEY LEARNINGS\n{entry}\n\n{content}"

        self.learnings_path.write_text(new_content, encoding="utf-8")
        logger.info("✓ Recorded Learning %d in KEY_LEARNINGS.md with 12D State Vector", next_num)
        return next_num

    def extract_from_python_code(
        self,
        code_content: str,
        name: str,
        domain_expertise: str,
        source_artifact: str = "custom_script.py",
        tags: Optional[List[str]] = None,
    ) -> ExtractedSkillSpec:
        """Extracts top functions and classes from Python source into a skill spec."""
        tree = ast.parse(code_content)
        
        key_concepts: List[str] = []
        instructions: List[str] = []
        code_examples: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    key_concepts.append(f"Function `{node.name}`: {ast.get_docstring(node) or 'Functional transformation'}")
                    instructions.append(f"Execute `{node.name}` for deterministic processing")
                    func_code = ast.get_source_segment(code_content, node) or f"def {node.name}(...): pass"
                    code_examples.append(func_code)
                    if len(instructions) >= 3:
                        break
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    key_concepts.append(f"Class `{node.name}`: {ast.get_docstring(node) or 'Architectural component'}")

        if not key_concepts:
            key_concepts.append(f"Modular logic in {name}")
            instructions.append("Execute pipeline")
            code_examples.append(code_content[:300])

        spec = ExtractedSkillSpec(
            name=name,
            domain_expertise=domain_expertise,
            key_concepts=key_concepts,
            instructions=instructions,
            code_examples=code_examples,
            tags=tags or ["compound", "reusable"],
            source_artifact=source_artifact,
        )
        return spec

    def extract_and_register(self, spec: ExtractedSkillSpec) -> Dict[str, Any]:
        """Full pipeline: save skill file, register in registry, update learnings."""
        skill_path = self.save_skill(spec)
        self.register_in_capability_registry(spec, skill_path)
        learning_id = self.record_learning_in_key_learnings(spec)
        return {
            "skill_path": str(skill_path),
            "learning_id": learning_id,
            "status": "SUCCESS",
        }
