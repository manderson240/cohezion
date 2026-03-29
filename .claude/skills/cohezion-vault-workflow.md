---
name: cohezion-vault-workflow
description: Vault-first knowledge management workflow for Cohezion. Covers vault_log_decision, vault_log_experiment, vault_extract_pattern API examples, MEMORY.md regeneration, and token savings strategy. Use when logging learnings to vault, extracting patterns, logging decisions or experiments, regenerating MEMORY.md, or when user mentions "vault workflow", "log learnings", "log decision", "log experiment", "extract pattern".
---

# Vault-First Knowledge Management

**CRITICAL**: All session learnings MUST be logged to vault, not MEMORY.md directly.

## How to Log Learnings

```python
# Log architectural decisions
vault_log_decision(
    project="cohezion",
    title="Short decision title",
    context="What led to this decision",
    decision="What was decided",
    rationale="Why this option was chosen"
)

# Log experiments (what was tried & learned)
vault_log_experiment(
    project="cohezion",
    hypothesis="What you expected",
    method="What you did",
    result="What happened",
    learnings="Key takeaways"
)

# Extract reusable patterns
vault_extract_pattern(
    source_path="path/to/source",
    pattern_name="Pattern Name",
    description="When to use this pattern",
    code_example="```python\n# example\n```",
    domain="testing|mcp|compound-engineering|etc"
)
```

## Regenerate MEMORY.md

```bash
# Run weekly or after major learnings
uv run python scripts/compile_memory_from_vault.py
```

## Token Savings

10K+ tokens/session by loading only relevant context via `vault_find_relevant_context(query)` instead of loading all 1177 lines of the old MEMORY.md.
