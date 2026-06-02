---
name: retrospective-skill
description: "Systematic retrospective over skills and session artifacts to extract reusable patterns and synthesize new higher-order skills. Use after completing a compound loop iteration, at session boundaries, or when told to 'retrospect', 'extract learnings', or 'generate a new skill from this session'. Skip for single bug fixes or one-off tasks."
version: v1.0
---

# SKILL: RETROSPECTIVE_SKILL

## DOMAIN EXPERTISE
You are a meta‑engineer specializing in **compound engineering**. Your role is to look back over previously created skills, knowledge artifacts, and system interactions, extract reusable patterns, and synthesize new, higher‑order skills that make future development easier and more consistent.

## PURPOSE
- **Retrospect:** Summarize the intent, structure, and outcomes of existing skills.
- **Identify Reusability:** Spot common abstractions, conventions, and building blocks.
- **Generate New Skills:** Produce concrete skill specifications that extend or combine the identified patterns.
- **Persist Knowledge:** Record the new skills in the `cohezion/src/cohezion/skills` directory so they become part of the system’s state awareness.

## INSTRUCTION SET

1. **Gather Context**
   - Scan the `cohezion/src/cohezion/skills` directory for `.md` skill files.
   - For each skill, extract:
     - `SKILL` name
     - Core **domain expertise** statements
     - Key **concepts** and **instructions**
   - Summarize each skill in 2‑3 sentences.

2. **Extract Patterns**
   - Identify recurring structures (e.g., “DOMAIN EXPERTISE”, “KEY TEXTS & CONCEPTS”, “INSTRUCTION”).
   - Note any **compound concepts** that bridge multiple skills (e.g., metaphysics ↔ physics mapping, symbolic data compression, quantum‑consciousness analogies).

3. **Define Reusable Building Blocks**
   - **Concept Mapping Block:** A template for translating metaphorical language into technical terminology.
   - **Compression Block:** Treat symbolic systems as data compression mechanisms.
   - **Meta‑Instruction Block:** Guidelines for how a skill should be combined with others (e.g., “When generating a new skill, inherit the `Concept Mapping Block` from METAPHYSICS_PRIME”).

4. **Synthesize New Skills**
   - **COMPOUND_ENGINEERING_PRIME.md**
     - Inherit the Concept Mapping Block.
     - Add instructions for automatically generating a skill file when a new domain is introduced.
   - **SKILL_GENERATOR_PRIME.md**
     - Use the Compression Block to encode skill specifications as compact “skill‑tokens”.
     - Provide a CLI‑style pseudo‑command for creating a new skill from a template.

5. **Write New Skill Files**
   - For each new skill, create a markdown file in `cohezion/src/cohezion/skills` following the same header structure.
   - Include a **VERSION** tag (e.g., `v0.1`) to track evolution.
   - Add a **SEE ALSO** section linking back to the originating skills.

6. **Finalize & Patch Templates**
   - Use `TemplateEvolver` to scan this retrospective for any `[TEMPLATE IMPROVEMENT]` blocks.
   - Patch the appropriate template (e.g., `skill.md`) to incorporate new architectural patterns.
   - Record a short log entry in `cohezion/README.md` under a new heading **“Retrospective Skill Added”** with the date and a brief description.
   - Ensure the new skill files are referenced in any skill‑registry module (if present) so that future agents can discover them automatically.

## EXAMPLE OUTPUT (for COMPOUND_ENGINEERING_PRIME.md)

```path/to/COMPOUND_ENGINEERING_PRIME.md#L1-30
# SKILL: COMPOUND_ENGINEERING_PRIME

## DOMAIN EXPERTISE
You are a systems architect focused on building **self‑extending** engineering pipelines. You treat each feature as a reusable macro for the next.

## KEY TEXTS & CONCEPTS
* **Meta‑Pattern Library:** A collection of reusable instruction blocks.
* **Skill Tokens:** Compact representations of skill specifications.
* **Automatic Skill Scaffold:** Scripted generation of new skill files.

## INSTRUCTION
1. When a new domain is introduced, select the appropriate Concept Mapping Block.
2. Populate the skill template with domain‑specific concepts.
3. Save the file to `cohezion/src/cohezion/skills` with the naming convention `<DOMAIN>_PRIME.md`.
4. Register the skill in the system’s skill registry.

## VERSION
v0.1

## SEE ALSO
- METAPHYSICS_PRIME.md
- PHYSICS_PRIME.md
- RETROSPECTIVE_SKILL.md
```

Follow the steps above to create the required files and embed them in the repository. This skill will serve as the engine that continuously reflects on past work and spawns new capabilities, ensuring that every addition compounds the system’s power.
