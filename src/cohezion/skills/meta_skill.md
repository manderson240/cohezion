---
name: meta_skill
description: Self-Evolution and Automated Knowledge Codification.
keywords:
- automated registry
- meta
- pattern abstraction
- recursive self-improvement (rsi)
- semantic deduplication
---

# SKILL: META_SKILL_PRIME

## DOMAIN EXPERTISE
Self-Evolution and Automated Knowledge Codification.
This skill enables an agent to identify successful behavioral patterns, abstract them into reusable instructions, and persist them as new skills in the Cohezion registry, effectively allowing the system to "learn to learn."

## KEY TEXTS & CONCEPTS
- **Recursive Self-Improvement (RSI)**: The process of a system improving its own code or capabilities.
- **Pattern Abstraction**: Converting specific instance success into generalizable rules.
- **Semantic Deduplication**: Using vector embeddings to ensure new skills are novel (not duplicates).
- **Automated Registry**: Programmatic updating of the skill index.

## INSTRUCTION

### 1. Pattern Recognition
When a complex task is completed successfully (Success Rate > 0.9), analyze the `walkthrough.md` or execution logs:
- Identify the sequence of tool calls.
- Extract the decision logic (Why did we do X?).
- Generalize specific filenames/variables to placeholders (`<TARGET_FILE>`).

### 2. Skill Generation
Generate a markdown content following the Standard Skill Template:
```markdown
# SKILL: <NAME>_PRIME

## DOMAIN EXPERTISE
[One paragraph definition]

## KEY TEXTS & CONCEPTS
- [Concept 1]
- [Concept 2]

## INSTRUCTION
1. [Step 1]
2. [Step 2]
```

### 3. Semantic Validation
Before saving:
1. Encode the new skill description using `FlumeEncoder`.
2. Compare similarity with all existing skills in `skill_registry.json`.
3. If `similarity > 0.85`, REJECT as duplicate.
4. If `similarity < 0.85`, APPROVE.

### 4. Registration
1. Save file to `src/cohezion/skills/<NAME>_PRIME.md`.
2. Update `src/cohezion/registry/skill_registry.json` with new entry.
3. Commit changes.

## VERSION
v1.0
