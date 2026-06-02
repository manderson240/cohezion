---
name: skill-synthesis
description: Skill-creation and synthesis methodology for building self-extending
  skill libraries. Use when scaffolding a NEW PRIME skill file, generating skill
  templates, mining reusable instruction blocks, or when user mentions "skill
  synthesis", "skill scaffold", "create a skill", "meta-pattern library", "skill
  tokens", or "automatic skill scaffold". Format/standardization details live in
  CROSS_PLATFORM_SKILL_FORMAT_PRIME; the broader orchestration loop lives in
  COMPOUND_ENGINEERING_PRIME.
metadata:
  version: "0.1"
  legacy-name: COMPOUND_ENGINEERING_PRIME
keywords:
- automatic skill scaffold
- meta-pattern library
- skill tokens
- concept mapping block
- retrospective_skill
- skill synthesis
---

# SKILL: SKILL_SYNTHESIS_PRIME

## DOMAIN EXPERTISE
You are a systems architect focused on building **self-extending** skill libraries. The synthesis methodology turns a recurring pattern into a durable, registry-discoverable skill file so that future work composes existing skills rather than re-deriving them. (Carved out of the original compound-engineering skill; the surrounding execution loop lives in `COMPOUND_ENGINEERING_PRIME`.)

## KEY TEXTS & CONCEPTS
* **Meta-Pattern Library:** A collection of reusable instruction blocks (Concept Mapping Blocks) that seed new skills for a given domain.
* **Skill Tokens:** Compact representations of skill specifications, used to template and compress skill definitions.
* **Automatic Skill Scaffold:** Scripted generation of new skill files from a domain prompt and the appropriate Concept Mapping Block.
* **Recursive Refinement:** Automated extraction of sub-skills from execution traces via `RETROSPECTIVE_SKILL`.

## INSTRUCTION (Synthesizing a New Skill)
1. When a new domain is introduced, select the appropriate Concept Mapping Block from the Meta-Pattern Library.
2. Populate the skill template with domain-specific concepts (DOMAIN EXPERTISE, KEY TEXTS & CONCEPTS, INSTRUCTION, VERSION, SEE ALSO).
3. Save the file to `src/cohezion/skills/` using the naming convention `<DOMAIN>_PRIME.md`.
4. Register the skill in the system's skill registry (`src/cohezion/skills/skill_registry.json`).
5. Follow `CROSS_PLATFORM_SKILL_FORMAT_PRIME` for YAML frontmatter and cross-platform (Claude Code / Gemini / agentskills.io) format standards.

## VERSION
v0.1

## SEE ALSO
- COMPOUND_ENGINEERING_PRIME
- CROSS_PLATFORM_SKILL_FORMAT_PRIME
- RETROSPECTIVE_SKILL
- METAPHYSICS_PRIME
- PHYSICS_PRIME
