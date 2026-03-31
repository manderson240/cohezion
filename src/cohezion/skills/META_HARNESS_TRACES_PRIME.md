# SKILL: META_HARNESS_TRACES_PRIME

## DOMAIN EXPERTISE
You are a Compound Engineering Architect specializing in execution trace management, filesystem-as-interface patterns, and Meta-Harness optimization loops.

## KEY TEXTS & CONCEPTS
* **Meta-Harness (arXiv:2603.28052):** Stanford/KRAFTON automated search in "harness space" — discovers optimal code for what info LLMs access and how it's presented. +7.7 points text classification (4x fewer tokens), +4.7 IMO math accuracy.
* **Filesystem > Prompt (L225):** Exposing execution traces as browsable files (grep/cat) outperforms cramming them into prompts. Agents should browse history, not ingest it.
* **Vault-First Architecture:** `~/vaults/cohezion-vault/` already implements this pattern via brain-region directories (prefrontal/decisions, cerebellum/patterns, hippocampus/experiments).

## INSTRUCTION
1. **Trace Directory:** Create `execution_traces/` alongside vault. CompoundExecutor logs traces to filesystem after each execution:
   ```
   execution_traces/
   ├── {skill_name}/
   │   ├── {timestamp}_{operation}.json   # Full execution context
   │   ├── {timestamp}_{operation}.metrics # Metrics snapshot
   │   └── {timestamp}_{operation}.output  # Raw output
   ```
2. **Trace Format:** Each trace file includes: task description, guidance used, execution result, metrics, token usage, anomaly detection, alignment analysis. JSON for structured data, plain text for output.
3. **SkillRefiner Integration:** Instead of passing execution summaries in prompts, SkillRefiner browses `execution_traces/{skill_name}/` via grep/cat to find relevant prior executions.
4. **Pruning:** Keep last 100 traces per skill. Older traces compress to single-line summaries in an index file.
5. **Meta-Harness Loop:** Proposer agent has full filesystem access to traces + scores. It proposes harness modifications (prompt templates, context selection, output formatting). Score on held-out tasks. Accept improvements, reject regressions.

## ANTI-PATTERNS
- ❌ Cramming full execution history into prompts (token explosion)
- ❌ Storing traces only in memory (lost across sessions)
- ❌ Keeping all traces forever (disk bloat, noise)

## VERSION
v1.0.0
