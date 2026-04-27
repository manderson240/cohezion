---
adr_number: 004
title: Vault-First Knowledge — Markdown as Source of Truth, MEMORY.md as Compiled Cache
date: 2026-04-23
status: ACCEPTED
deciders: cohezion-project
consulted: [vault-keeper specialist, all session-history consumers, retrospection engine]
informed: [compound executor step 1 / step 7, MCP servers, all agent specialists]
authored_by: synthetic-sniffing-panda Wave Ω10 retroactive ADR
---

# ADR-004: Vault-First Knowledge — Markdown as Source of Truth, MEMORY.md as Compiled Cache

## Status

ACCEPTED, 2026-04-23. Documented explicitly in CLAUDE.md (Session 56, "Vault-First Knowledge Management"); this ADR formalises the framing and records the alternatives that were rejected.

## Context

A compound-engineering system that persists nothing across sessions cannot compound. Earlier session-history strategies all failed in characteristic ways: a monolithic `MEMORY.md` grew to 1,177 lines and became unreadable for both humans and LLMs (it consumed too much context to load, and humans couldn't navigate it); scattered per-session notes lost cross-session linkage; pure SurrealDB persistence lost human readability and required tooling for any inspection. Each failure produced the same operational symptom: agents redoing investigation that had been completed weeks earlier because the prior result was either inaccessible or not discoverable in time.

The constraints the persistence layer must satisfy: (a) human-readable canonical representation — engineers must be able to grep, edit, and review knowledge without a viewer tool; (b) AI-searchable surface so that an agent can retrieve relevant prior context within a single tool call; (c) survives across sessions — knowledge persists when an agent's context window is reset or the process exits; (d) the writer surface must be append-only friendly, since most session writes are atomic decision/lesson/experiment records; (e) cross-references between records must be cheap to maintain and follow.

A secondary constraint is workflow: the vault is read by *every* compound execution at step 1 and written to at step 7 (ADR-001), so the read latency and write semantics are load-bearing for the entire executor pipeline.

## Decision

We commit to a vault-first knowledge model: the canonical source of truth is `~/vaults/cohezion-vault/`, an Obsidian-style markdown vault with YAML frontmatter, organised into `decisions/`, `lessons/`, `experiments/`, `patterns/`, and `papers/` subdirectories with bidirectional wiki-links. All session learnings — decisions, lessons, retrospectives, experiments — are written to the vault as atomic markdown files. `MEMORY.md` (in the cohezion repo) is a *compiled cache* automatically regenerated weekly: ~95 lines containing recent decisions (last 7 days), the top-10 most-used patterns, and quick-reference scaffolding. Agents query the vault via `vault_find_relevant_context(query)` (returning ranked matches), and the compound executor's step 1 (`get_experience_guidance`) routes through this same surface.

## Rationale

The split between *canonical markdown* (vault) and *compiled cache* (MEMORY.md) resolves the tension between human readability and LLM context budget. Markdown is the lowest-common-denominator format that is simultaneously human-editable (any text editor), version-controllable (git-friendly diffs), search-tool-friendly (ripgrep, grep), and LLM-readable (no parser required). YAML frontmatter gives structured metadata without sacrificing the readability of the body. Wiki-link bidirectionality is supplied by Obsidian's resolver and is fast enough to traverse at agent-query time.

The compiled-cache role of MEMORY.md is the discipline that prevents the file from drifting back into a 1,177-line monolith. Because it is *compiled* (regenerated weekly from vault contents by an explicit script), edits to MEMORY.md are non-canonical by construction — they would be overwritten on the next compile. This means agents and humans both know that the vault is where to write, and MEMORY.md is where to read for fast-context. The 95-line budget keeps MEMORY.md small enough to load into every session without burning context.

The vault-search surface (`vault_find_relevant_context`) is the integration point with the compound executor. Step 1 of the loop retrieves prior coherent context by calling this function; step 7 persists new context back via the same MCP server. Because both reads and writes route through one well-defined interface, the underlying storage layer can evolve (today: markdown + Obsidian; future: markdown + SurrealDB index; future: markdown + embedding store) without the executor having to change. This is the architectural reason the vault is "first": it is the *read/write contract*, not the *storage technology*.

## Alternatives considered

### Option A: MEMORY.md-first (single monolithic memory file)
- Pros: One file, no indirection; trivial to load.
- Cons: Grows unboundedly (1,177 lines empirically); becomes unreadable; no atomic per-decision records; merge conflicts on every session.
- Why rejected: Failed in production; the 1,177-line incident is the evidence.

### Option B: SurrealDB-first (database as source of truth)
- Pros: Native graph queries; structured types; good performance.
- Cons: Loses human readability — every inspection requires a query tool; markdown becomes a derivative output rather than a source; review and PR workflows degrade.
- Why rejected: The "engineer can grep and edit knowledge directly" property is more valuable than the structured-query gain. SurrealDB lives in the project as the journey-tracking and metrics store, but is *not* the authoritative knowledge store.

### Option C: Scattered docs (per-project READMEs and CLAUDE.md fragments)
- Pros: Co-located with the code they describe; no separate system to maintain.
- Cons: No cross-project search; no canonical place for cross-cutting decisions; lessons disappear into project subdirs and are not retrievable by agents working elsewhere.
- Why rejected: Defeats the cross-session compounding thesis. A lesson learned in cohezion's compound module should be retrievable when working in the swarm module.

### Option D (chosen): Vault-first markdown + compiled MEMORY.md cache + wiki-link cross-references
- Pros: Human-readable and AI-searchable; survives sessions; cross-references are cheap; the read/write contract is stable while the storage can evolve.
- Cons: Discoverability depends on vault hygiene (orphan detection, frontmatter enforcement); the weekly compile cadence has lag; two-surface model (vault + compiled cache) requires teaching new agents.
- Why chosen: The only option that satisfies all five constraints simultaneously.

## Consequences

### Positive
- Knowledge compounds across sessions because every decision/lesson/experiment is retrievable.
- Humans can grep, edit, and PR-review knowledge without bespoke tooling.
- The read/write surface (`vault_find_relevant_context`) is stable; storage can evolve.
- 95% cache hit rate (CLAUDE.md) on `SemanticCache` queries is achievable because the vault provides a rich similarity surface.

### Negative
- Vault hygiene is now a first-class operational concern (orphan detection, frontmatter validation, broken wiki-link audit) — handled by the `vault-keeper` specialist.
- The weekly compile cadence means MEMORY.md can lag fresh vault writes by up to 7 days.
- New agents must learn the two-surface model (vault canonical, MEMORY.md cached); incorrect writes to MEMORY.md are silently lost on next compile.

### Neutral
- The vault lives outside the cohezion repo (`~/vaults/cohezion-vault/`); cross-machine portability requires a sync strategy.
- SurrealDB is still used for journey tracking and metrics but is no longer the authoritative knowledge store.

## Implementation

- Primary files:
  - `~/vaults/cohezion-vault/` (canonical knowledge store; ~150 decisions/patterns/experiments at snapshot 2026-04-23).
  - `MEMORY.md` (compiled cache, ~95 lines, regenerated weekly).
  - `src/cohezion/compound/exp_persistence/vault.py` (`VaultLogger` — write surface used by executor step 7).
  - `src/cohezion/skills/cohezion_vault_workflow.md` (vault API documentation: log decision/experiment/pattern; MEMORY.md regeneration).
  - `src/cohezion/core/mcp_client.py` (read surface: `vault_find_relevant_context` and friends).
- Test files: `tests/compound/exp_persistence/test_vault.py`, `tests/integration/test_vault_compound_loop.py`.
- Documentation: CLAUDE.md "Vault-First Knowledge Management (NEW: Session 56)" section; this ADR; the `cohezion-vault-workflow` skill.

## Verification

- Static check: `ls ~/vaults/cohezion-vault/decisions/ | wc -l` — confirms vault is populated (≥ 100 records expected at steady state).
- Static check: `wc -l MEMORY.md` — should be ≤ 200 lines (compiled-cache discipline).
- Runtime check: `uv run python -c "from cohezion.core.mcp_client import MCPClient; ..."` — exercises `vault_find_relevant_context` against a real query.
- Test: `uv run pytest tests/compound/exp_persistence/test_vault.py -q` — confirms write semantics; integration test confirms read-after-write consistency.

## Reversal cost

**HIGH.** The vault is the substrate of cross-session compounding for the entire project. ~150 atomic records exist as of 2026-04-23, with bidirectional wiki-links and frontmatter conventions that downstream tools (vault-keeper, surreal-dba, compound executor step 1, retrospection engine) all depend on. Reversing to a different model would require migrating the corpus, rewriting the read/write contract (`vault_find_relevant_context` and `VaultLogger`), and re-baselining the semantic cache that warms off vault content. Estimated effort: 4-8 person-weeks plus a multi-month operational risk window during which the compounding surface is degraded.

## Related ADRs

- Depends on: none — this ADR is foundational.
- Informs: ADR-001 (the eleven-step loop's steps 1 and 7 both route through the vault); ADR-005 (FLUME encodes vault content into the latent space).
- Tension with: none currently identified; SurrealDB's role is complementary (journey + metrics, not knowledge).

## References

- CLAUDE.md, "Vault-First Knowledge Management (NEW: Session 56)" section (lines 98-113).
- `research/distillates/2026-04-23-vault-decisions-distillate.md` (top-20 vault decisions; Decisions #2, #8, #20 cover vault topology and conventions).
- `research/distillates/2026-04-23-vault-decisions-distillate.md` Decision #20: "Obsidian Best Practices for AI Agents" — atomic notes, bidirectional linking, frontmatter standards.
- Skill: `cohezion-vault-workflow` (in `src/cohezion/skills/`).
