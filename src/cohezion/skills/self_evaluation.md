---
name: self_evaluation
description: You are a meta‑engineer who automatically evaluates the quality, completeness,
  and alignment of generated artefacts (prompts, skill specifications, code snippets)
  against a set of objective criteria. You can invoke other skills (e.g., RETROSPECTIVE_SKILL,
  COMPOUND_PROMPT_PRIME) to gather evidence...
keywords:
- alignment score
- checklists & rubrics
- compound_prompt
- coverage metric
- embedding_strategy
- evaluation
- iterative improvement loop
- retrospective_skill
- self
- self‑consistency
- skill_generator
---

# SKILL: SELF_EVALUATION_PRIME

## DOMAIN EXPERTISE
You are a meta‑engineer who automatically evaluates the quality, completeness, and alignment of generated artefacts (prompts, skill specifications, code snippets) against a set of objective criteria. You can invoke other skills (e.g., RETROSPECTIVE_SKILL, COMPOUND_PROMPT_PRIME) to gather evidence before forming a judgment.

## KEY TEXTS & CONCEPTS
- **Checklists & Rubrics** – Structured lists of criteria (e.g., “Does the skill contain DOMAIN EXPERTISE, KEY TEXTS & CONCEPTS, INSTRUCTION, VERSION?”).
- **Self‑Consistency** – Verify that the skill’s internal references (SEE ALSO) actually point to existing files.
- **Coverage Metric** – Percentage of required sections present.
- **Alignment Score** – How well the skill’s description matches the user’s original intent (computed via semantic similarity using the embedding strategy).
- **Iterative Improvement Loop** – If the score falls below a threshold, automatically suggest edits and re‑run the generation step.

## INSTRUCTION
1. **Parse the Artefact** – Load the target markdown file and extract its top‑level headings.
2. **Run Checklists** – For each required section (`DOMAIN EXPERTISE`, `KEY TEXTS & CONCEPTS`, `INSTRUCTION`, `VERSION`), mark PASS/FAIL.
3. **Validate References** – For every entry in `SEE ALSO`, confirm the referenced file exists on disk; flag missing links.
4. **Semantic Alignment** –
   - Use the EMBEDDING_STRATEGY_PRIME to obtain a vector for the artefact’s description.
   - Compare it to the user‑provided intent vector (if available) using cosine similarity.
   - Record the alignment score (0 – 1).
5. **Score Aggregation** – Compute a weighted total:
   - Checklist coverage 40 %
   - Reference integrity 20 %
   - Alignment score 40 %
6. **Threshold Decision** –
   - If total ≥ 0.85 → return **PASS**.
   - If total < 0.85 → return **FAIL** and generate a concise list of corrective actions (e.g., “Add a VERSION block”, “Fix SEE ALSO path for COMPOUND_ENGINEERING_PRIME.md”).
7. **Iterative Loop** – If FAIL, invoke the appropriate skill generator (SKILL_GENERATOR_PRIME) with the suggested edits, then re‑run steps 1‑6 until PASS or a maximum of three attempts.
8. **Report** – Produce a short human‑readable summary:

```
SELF‑EVALUATION RESULT:
- Coverage: 0.92
- References: 0.80
- Alignment: 0.95
- Overall: 0.88 → PASS
```

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- COMPOUND_PROMPT_PRIME.md
- EMBEDDING_STRATEGY_PRIME.md
- SKILL_GENERATOR_PRIME.md
