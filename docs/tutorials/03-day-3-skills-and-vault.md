---
title: "Day 3 — Skills and the Vault"
target_audience: contributor who has traced the compound loop end-to-end
estimated_time: 2-3 hours
prerequisites:
  - Tutorial 2 completed (you can name the eleven steps without looking)
  - You understand that the executor is the spine; today you learn what it executes against
prior_tutorials:
  - 01-day-1-setup-and-first-test.md
  - 02-day-2-the-compound-loop.md
next_tutorial: 04-day-7-running-a-campaign.md
---

# Day 3 — Skills and the Vault

Yesterday you traced one execution through `CompoundExecutor.execute_task()`. Today you study the *content* the executor runs against: **skills** (markdown-defined behaviors registered in a JSON registry, invoked by the executor, refined by the SkillRefiner at step 7 of the loop) and **the vault** (the canonical, single-source-of-truth knowledge store under `~/vaults/cohezion-vault/`).

The relationship between the two is the project's "vault-first" architecture. Quoting `CLAUDE.md`:

> **CRITICAL**: All session learnings MUST be logged to vault, not MEMORY.md directly.
>
> MEMORY.md = Compiled Cache (auto-generated weekly): 95 lines (vs 1177 lines old version), recent decisions (last 7 days), most-used patterns (top 10), quick reference only.
>
> Vault = Single Source of Truth: ~/vaults/cohezion-vault/ (150+ decisions, patterns, experiments), searchable via `vault_find_relevant_context(query)`, survives across sessions, compounds knowledge.

Skills are the same architecture in miniature: the canonical copy lives in the vault (or the user's `~/.claude/skills/` directory for global skills); the project's `src/cohezion/skills/` is a derived mirror; the JSON registry is a metadata-only index that lets the executor find the right markdown file without parsing every skill at import time.

## What you will do today

1. Read `src/cohezion/skills/skill_registry.json` and understand its shape.
2. Pick one PRIME skill, read its markdown definition, and trace how it would be invoked from the compound loop.
3. Walk the vault directory tree (`~/vaults/cohezion-vault/`) and identify the four canonical knowledge categories.
4. If a Wave 4A `INDEX.md` was produced by the synthetic-sniffing-panda campaign, read it.
5. Write a small "Hello, Cohezion" PRIME skill, register it in the JSON, and confirm the registry sync.
6. Invoke your skill through the executor (or a stand-in) and observe it appear in the journey log.

By the end you will be able to answer: where does a skill *actually live*, who reads it, what does the registry guarantee, and why is the vault the truth source rather than the project tree?

## Step A — Read the skill registry

Start in the project tree:

```bash
wc -l src/cohezion/skills/skill_registry.json
head -40 src/cohezion/skills/skill_registry.json
```

The file is approximately 1,652 lines on the synthetic-sniffing-panda baseline and contains roughly 235 skill entries (215 of which are PRIME-format; the rest are simpler `.md` skill definitions). Each entry has the same shape:

```json
"ADAPTIVE_TEMPLATE_PRIME": {
  "concepts": [
    "Structural Drift",
    "Template Patching",
    "Atomic Blueprints",
    "Recursive Consistency"
  ],
  "see_also": [
    "TEMPLATE_DRIVEN_DEVELOPMENT_PRIME",
    "RETROSPECTIVE_SKILL",
    "SKILL_GENERATOR_PRIME",
    "COMPOUND_ENGINEERING_PRIME"
  ],
  "source": "src/cohezion/skills/ADAPTIVE_TEMPLATE_PRIME.md",
  "version": "v1.0"
}
```

Note what the registry **does not** contain: the skill's actual instructions, its prompt body, its examples. Only the *metadata*: the skill's key concepts, related skills (`see_also`), the source file path, and a version string. This is the **metadata-only pattern** — the registry is small, fast to parse, and stable across skill-content changes. Updating a skill's body does not modify the registry; renaming or relating a skill does.

> **Why this matters.** A naive design would inline each skill's full markdown into the registry. That fails for two reasons. First, every skill change becomes a registry diff, which makes the JSON noisy and merge-conflict-prone. Second, parsing all 235 skills at import time would be slow and would tie the executor's startup to the size of the skill library. The metadata-only pattern keeps the registry as a small, stable index and defers actual skill loading to the call site that needs it.

## Step B — Pick one PRIME skill and read it

PRIME-format skills follow a fixed markdown structure. Pick one whose name matches your interest. A good first read is `ADAPTIVE_TEMPLATE_PRIME.md` because it describes the very pattern by which skills evolve:

```bash
cat src/cohezion/skills/ADAPTIVE_TEMPLATE_PRIME.md
```

You will see five sections, in this order:

1. `# SKILL: <NAME>` — title.
2. `## DOMAIN EXPERTISE` — what role the LLM is taking on when this skill is invoked.
3. `## KEY TEXTS & CONCEPTS` — the named concepts that justify the skill's existence (these match the `concepts` array in the registry).
4. `## INSTRUCTION` — numbered procedural steps the LLM should execute when the skill fires.
5. `## VERSION` and `## SEE ALSO` — book-keeping that matches the registry fields.

The PRIME format is the project's convention for skills that will be invoked from the compound loop. Non-PRIME skills (the ones whose registry key is lowercase, e.g. `3d_rendering`) have looser structure — they predate the convention or come from upstream sources. The `CONSOLIDATION_REPORT.md` produced by the synthetic-sniffing-panda Wave 4C campaign (`skills/CONSOLIDATION_REPORT.md` if present) catalogs the keep/merge/delete decisions.

> **Why this matters.** PRIME skills are the format that the `SkillRefiner` (step 7 of the compound loop) reads and updates. A skill that does not follow the PRIME structure cannot be safely refined automatically — the refiner's prompt template assumes the five-section shape. When you write a new skill, follow the PRIME format unless you have a specific reason not to.

## Step C — Trace the invocation path

How does a skill named `ADAPTIVE_TEMPLATE_PRIME` actually get called? Walk the chain backward from `CompoundExecutor.execute_task()`:

1. The caller invokes `executor.execute_task(task_description, skill_name="ADAPTIVE_TEMPLATE_PRIME", operation_type="generate", execute_fn=<callable>, ...)`.
2. Step 1 of the loop calls `self.get_experience_guidance(task_description, project, operation_type)` — this consults the vault (and the trajectory store) for prior runs *of this skill on similar tasks*. The skill name is the key.
3. The `execute_fn` callable is what actually runs the skill. The executor is *not* opinionated about how the skill body is loaded — that is the caller's responsibility. In production, the caller is typically `SkillRegistry.load(skill_name).render(context)` or equivalent, which reads the markdown source from the path in the registry and prepares an LLM prompt.
4. Step 7 (`SkillRefiner.refine()`) writes back into the registry's source file when the gating condition (a non-trivial pattern set from step 6) is satisfied.

The key insight: **the registry is read at skill-resolution time; the markdown is read at skill-invocation time; the source-of-truth is whichever copy the registry's `source` path points to**. In production, that is the project tree (`src/cohezion/skills/...`). The vault holds the canonical copy of any skill that has been *promoted* — the project tree's copy is treated as derived. Wave 4 of the synthetic-sniffing-panda campaign produced `vault-dedup-audit.md` documenting where the canonicality differs.

## Step D — Walk the vault

The vault is a standalone Obsidian-compatible directory at `~/vaults/cohezion-vault/`. List the top-level entries:

```bash
ls ~/vaults/cohezion-vault/ | head -30
```

You will see a large number of directories. The four categories that matter for Day 3 are:

| Vault directory | What it stores |
|---|---|
| `decisions/` | One markdown per architectural decision, dated. The synthetic-sniffing-panda campaign added several here. |
| `patterns/` | Reusable code/process patterns extracted from successful sessions. |
| `learnings/` (and `01-Learnings/INDEX.md`) | Numbered learning entries (L233, L368, L369, etc.) — the project's most-cited cross-reference. |
| `retrospectives/` | One markdown per completed campaign or major milestone. The Wave-Ω5 retrospective for synthetic-sniffing-panda lives here at `2026-04-23-synthetic-sniffing-panda.md`. |

The other directories are domain-specific (`competition_intelligence`, `model_capabilities`, `cerebellum/`, `prefrontal/` — yes, the vault uses brain-region naming for some functional areas). For Day 3 you care about the four above.

> **Checkpoint.** Open `~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md` and read the "Numeric deltas" table. This is the single most useful demonstration of how the vault accumulates compound value: a campaign concluded yesterday left a structured, queryable artifact that the next campaign will read as `experience guidance` at step 1 of the loop. That is the vault-first architecture working end-to-end.

## Step E — Read the Wave 4A INDEX

If the synthetic-sniffing-panda Wave 4A learnings INDEX exists at `~/vaults/cohezion-vault/01-Learnings/INDEX.md`, open it. The campaign consolidated 167 documented learnings (L1 through L376-ish) across multiple source files into a single index. If the file is empty or missing, the structure can be reconstructed from `ls ~/vaults/cohezion-vault/01-Learnings/` plus `grep -rn "^L[0-9]\+" ~/vaults/cohezion-vault/`.

The learnings are referenced from `CLAUDE.md`'s coding-standards section (Learnings 359, 363, 367, 368, 369), from the global rules under `~/.claude/rules/`, and from individual skill bodies. They are the project's accumulated knowledge — the structural counterpart to the executor's accumulated trajectories.

## Step F — Write a "Hello, Cohezion" PRIME skill

Now you will add a small skill yourself. Create the file `src/cohezion/skills/HELLO_COHEZION_PRIME.md`:

```markdown
# SKILL: HELLO_COHEZION_PRIME

## DOMAIN EXPERTISE
You are a friendly orientation guide for new Cohezion contributors. When invoked, you respond with a single sentence acknowledging the contributor's first skill invocation and pointing them at one next-step file.

## KEY TEXTS & CONCEPTS
- **Onboarding loop**: the day-1 → day-30 tutorial sequence under `docs/tutorials/`.
- **Vault-first knowledge**: the canonical knowledge store under `~/vaults/cohezion-vault/`.
- **Metadata-only registry**: the `skill_registry.json` lookup pattern.

## INSTRUCTION

### 1. Acknowledge
Respond with: "Welcome — your first skill invocation has been recorded."

### 2. Next-step pointer
Append exactly one of:
  - "Read `docs/tutorials/04-day-7-running-a-campaign.md` for your next milestone." (if the contributor is on day 3-6)
  - "Read `docs/tutorials/05-day-30-contributing-an-architectural-change.md` for your next milestone." (if day 7-29)

### 3. Do not elaborate
Do not add additional context, examples, or explanation. Single-sentence acknowledgement plus single-sentence pointer.

## VERSION
v1.0

## SEE ALSO
- ADAPTIVE_TEMPLATE_PRIME
- COMPOUND_ENGINEERING_PRIME
```

Then add the corresponding entry to `src/cohezion/skills/skill_registry.json`. Find an alphabetically-appropriate spot (between `HARDWARE_PROFILE_PRIME` and `IMAGE_GENERATION` if those exist, or just append before the closing `}` if you prefer simplicity for the exercise) and insert:

```json
"HELLO_COHEZION_PRIME": {
  "concepts": [
    "Onboarding loop",
    "Vault-first knowledge",
    "Metadata-only registry"
  ],
  "see_also": [
    "ADAPTIVE_TEMPLATE_PRIME",
    "COMPOUND_ENGINEERING_PRIME"
  ],
  "source": "src/cohezion/skills/HELLO_COHEZION_PRIME.md",
  "version": "v1.0"
},
```

(Mind the trailing comma: required if your entry is followed by another entry, omitted if it is the last.)

> **Checkpoint.** Validate the JSON did not break:
>
> ```bash
> python -c "import json; print(len(json.load(open('src/cohezion/skills/skill_registry.json'))))"
> ```
>
> The output should be a number greater than the prior count by one (e.g. 235 → 236). If you get a `json.decoder.JSONDecodeError`, fix the trailing-comma situation and re-run.

## Step G — Invoke your skill (or simulate the invocation)

In production, your skill would be invoked via:

```python
from cohezion.compound.executor import CompoundExecutor
# (constructor with mcp_client and other collaborators omitted)
result = executor.execute_task(
    task_description="Greet a new contributor",
    skill_name="HELLO_COHEZION_PRIME",
    operation_type="generate",
    execute_fn=lambda ctx: ("Welcome — your first skill invocation has been recorded. "
                            "Read docs/tutorials/04-day-7-running-a-campaign.md for your next milestone.",
                            {"tokens_used": 0}),
    project="cohezion",
)
print(result.success, result.output)
```

Standing this up requires an `mcp_client`, optional collaborators, and a vault you can write to. For Day 3, the simpler check is: confirm the registry resolves your skill's source path and the file exists.

```bash
uv run python -c "
import json
from pathlib import Path
reg = json.load(open('src/cohezion/skills/skill_registry.json'))
entry = reg['HELLO_COHEZION_PRIME']
src = Path(entry['source'])
print(f'Registry resolved: {src}')
print(f'File exists: {src.exists()}')
print(f'Concepts: {entry[\"concepts\"]}')
"
```

> **Checkpoint.** All three lines should print non-empty. If `File exists` is `False`, your `source` path in the registry does not match where you actually wrote the markdown — fix one to match the other.

## Step H — Run the test suite to make sure you did not break anything

```bash
uv run pytest tests/ -q --co -k "skill" 2>&1 | tail -20
```

The `--co` flag collects but does not run. You should see a list of skill-related tests. If collection itself errors, your registry edit broke the JSON structure for some test that loads it. Fix and re-run.

If collection succeeds, run the focused suite:

```bash
uv run pytest tests/ -q -k "skill_registry" 2>&1 | tail -10
```

The pass count should match the baseline (or be one greater if a "registry contains N skills" test now sees N+1).

> **Why this matters.** Adding a skill is the simplest possible vault-touching change. Every additional skill, learning, or pattern follows the same pattern: write the canonical markdown (in vault or project tree, depending on scope), update the metadata-only index that lets it be found, run the small test suite that validates the index. If you can do this for `HELLO_COHEZION_PRIME_PRIME`, you can do it for any future skill you write.

## (Optional) Step I — Promote your skill to the vault

If you intend your skill to be available across all your Cohezion sessions (not just this checkout), copy it into `~/vaults/cohezion-vault/` under whichever subdirectory matches your taxonomy (most likely `patterns/` for a usage pattern or a project-internal `skills/` directory if you keep one). The project's mirror script `cohezion-vault-workflow` (a separate skill) handles the dedup. For Day 3 you do not need to perform the promotion; just be aware that the vault would be the canonical home if you did.

## What you just learned

1. **The metadata-only registry is the index, not the content.** `skill_registry.json` holds concepts, related skills, source path, version. It does not hold instructions or prompts. That separation is what allows the registry to stay small and stable while the skills evolve.
2. **PRIME-format is the contract for refinable skills.** Five sections in fixed order: title, domain expertise, key texts & concepts, instruction, version + see-also. The `SkillRefiner` at step 7 of the compound loop assumes this shape.
3. **Vault is canonical; project tree is derived.** When the same skill exists in both, the vault wins. The dedup audit (`research/vault-dedup-audit.md`) tracks where they have drifted and which side should be reconciled.
4. **The registry sync is a write-and-validate step.** Add the markdown, add the JSON entry, parse the JSON, run the registry tests. Two artifacts must agree; the parse + test confirms they do.
5. **The vault accumulates compound value through structured artifacts.** Decisions, patterns, learnings, retrospectives. Each campaign's retrospective becomes the next campaign's experience guidance. That is the vault-first thesis in one sentence.

## What you will do on Day 7

You have now seen the executor (Day 2) and the skills + vault (Day 3). On Day 7 you will combine them: run a small polish campaign using the `polish-campaign-orchestrator` skill, dispatch parallel agents across waves, and produce a real retrospective in the vault. Today's `HELLO_COHEZION_PRIME` is a single-sentence skill; Day 7's campaign will be five waves of two-to-six agents each, gated by verification, ending with a written retrospective. The mechanics are the same — markdown definitions, registry indexing, executor invocation, vault persistence — only the scale changes.

→ Continue to [Tutorial 4 — Day 7: Running a Campaign](./04-day-7-running-a-campaign.md).

→ Back to [Tutorial 2 — Day 2: The Compound Loop](./02-day-2-the-compound-loop.md).
