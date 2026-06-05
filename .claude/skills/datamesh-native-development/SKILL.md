---
name: datamesh-native-development
description: Use when integrating new code into the Cohezion local fleet / inference / daily-researcher stack. The pattern: every new code path is a WRITER or READER of the PrecipitationBus + vault + SurrealDB. Discovered in PRs #223-#226 (the WS1+WS2+PR1-4 build) where 4 PRs delivered the compound × token × card-aligned stack with 5 datamesh connections wired end-to-end.
when_to_use: |
  - Adding a new function, lane, or path that touches the local fleet
  - Building a new verifier, monitor, or skill refiner
  - Wiring an existing component into the daily researcher
  - Adding telemetry, observability, or feedback signals
when_not_to_use: |
  - The new code is pure UI / CLI / config (no fleet interaction)
  - The new code is a standalone script (use the bus only at boundaries)
  - You're building a brand-new module with no datamesh yet — seed
    the bus first via the existing patterns, don't invent new ones
the_5_surfaces:
  FLUME_VAE:
    role: 256D semantic embeddings; cosine-similarity L2 cache
    file: src/cohezion/flume/vae_encoder.py
    pattern: encode (prompt, card_signature) jointly so the
      embedding carries the card
    use_when: cache keying, semantic similarity, 12D witness point
  OUROBOROS:
    role: coherence surveillance, anomaly detection, auto-healing
    file: src/cohezion/ouroboros/{recorder,detector,healer}.py
    pattern: emit HEALING_EVENT when card_alignment_rate drops
    use_when: monitoring regressions, on threshold breach
  MYCELIUM:
    role: subscribes to WITNESS_MARK on the bus, clusters by 12D
    file: src/cohezion/mycelium/registry.py
    pattern: emits MYCELIUM_PATTERN when cluster size crosses threshold
    use_when: cross-agent pattern detection, validation boost
  OBSIDIAN_VAULT:
    role: human-facing markdown files in ~/vaults/.../01-Learnings/
    file: src/cohezion/persistence/obsidian_mcp.py
    pattern: write per-execution EXEC-<ts>-<slug>.md notes; per-day
      directory; per-cluster MYCELIUM-PATTERN-<id>.md notes
    use_when: leaving a human-readable trail of every action
  SURREALDB:
    role: knowledge graph on port 8001 (cohezion ns, main db)
    file: src/cohezion/persistence/genesis_persistence.py
    pattern: UPSERT (not UPDATE) — UPSERT is no-op for new records
    use_when: persisting executions, syntheses, cache entries,
      healing events as RELATE'd rows
the_spine:
  bus: src/cohezion/precipitation/bus.py (PrecipitationBus)
  kinds:
    - WITNESS_MARK: agent artifact (commit/vault/decision)
    - COSMOGONY_PHASE: symmetry breaks
    - COHERENCE_PEAK: HIHO attractor reached
    - CONSENSUS_RATIFIED: ≥ 0.85 vote
    - HEALING_EVENT: Ouroboros remediation fired
    - MYCELIUM_PATTERN: cross-agent convergence detected
    - TRAINING_CHECKPOINT: fine-tune checkpoint saved
    - GENERATION_SPAWN: next-generation universe launched
  sinks:
    - VaultSink: writes events to markdown in the vault
    - SurrealSink: writes events to SurrealDB
    - LedgerSink: appends events to autoresearch.jsonl
writer_pattern: |
  Every new code path that PRODUCES a result should:
    1. Construct a PrecipitationEvent with kind, coherence, twelve_d, payload
    2. Apply a 1/hour per-(task, model) cooldown to prevent bus flooding
    3. bus.emit(event) — sinks are subscribed automatically
    4. ALSO write a SurrealDB row (UPSERT) for queryability
    5. ALSO write a vault note for the human
  Example (from PR 1's execute_fn_aligned):
    # Connection A: WITNESS_MARK emission
    twelve_d = _twelve_d_from_card(family=family, task=task, ...)
    event = PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id="cohezion_compound_executor",
        coherence=0.6,  # 0.4 escalation, 0.3 error, 0.7 cache hit, 0.8 prefix
        twelve_d=twelve_d,
        payload={...},
    )
    bus.emit(event)
    # Connection D: SurrealDB upsert, fire-and-forget
    asyncio.create_task(_upsert_surreal_execution(...))
    # Connection E: vault note
    _write_vault_note(...)

reader_pattern: |
  Every new code path that CONSUMES a result should:
    1. Query SurrealDB first (it's the queryable substrate)
    2. Fall back to vault (markdown is human-facing but parseable)
    3. Subscribe to the bus for live events
  Example (from PR 4's verify_evolve):
    # Connection D: query for execution evidence
    executions = await self._query_surreal_executions(target_model)
    # Connection C: query for healing events
    healing_events = await self._query_ouroboros_healing_events(target_model)

the_5_connections:
  A_12D_witness_marks:
    what: every aligned call emits a WITNESS_MARK with a 12D point
    why: Mycelium clusters these by proximity
    recipe: family → dim, task → dim, outcome → coherence
  B_FLUME_VAE_cache_key:
    what: the L2 cache uses the joint (prompt, card_signature) embedding
    why: two consumers with different cards for the same prompt miss
    recipe: sha256(prompt + system + model + <<CARD:...>>)
  C_Ouroboros_card_alignment:
    what: card_alignment_rate drop → HEALING_EVENT
    why: verify_evolve disputes syntheses for affected models
    recipe: windowed rate, latch on emit, recovery re-arms
  D_SurrealDB_evidence:
    what: every aligned execution lands as a row in fleet_research:execution
    why: quantitative verifiability (≥ 3 backings → verified)
    recipe: UPSERT (not UPDATE) + 1-hour TTL
  E_vault_notes:
    what: EXEC-<ts>-<slug>.md per execution; MYCELIUM-PATTERN-<id>.md per cluster
    why: thin waist between agentic loop and human
    recipe: per-day directory; markdown with model + task + metrics

decision_tree: |
  Are you adding new code to the local fleet / inference / researcher?
  ├─ NO (pure UI/CLI) → you don't need this skill
  └─ YES → Does your path produce a result that should be observable?
            ├─ NO (pure stateless helper) → write tests, no datamesh hook
            └─ YES → Apply the writer pattern. WITNESS_MARK + SurrealDB
                      row + vault note (per-day directory).
            Does your path consume existing datamesh evidence?
            ├─ NO → you don't need a reader
            └─ YES → Apply the reader pattern. SurrealDB query first,
                       vault fallback, bus subscription for live events.
worked_example: |
  The 4-PR WS1+WS2+PR1-4 build (commits 4bc2f9c8f, 808a9f03c, 4e782ebfa,
  76de2dc23) delivered 4 sub-PRs each adding 1-2 of the 5 connections:
    PR 1 (execute_fn_aligned): A (12D), D (SurrealDB), E (vault)
    PR 2 (semantic_cache_wiring): B (FLUME VAE cache key), A (cache hit)
    PR 3 (token_efficient_aligned): A (prefix hit, coherence 0.8)
    PR 4 (researcher_crosslink): A (Mycelium boost), C (Ouroboros veto),
                                       D (SurrealDB ≥ 3 threshold)
  Total: 28 tests, ~2,400 LOC, 0 regressions, 5 connections wired.

anti_patterns:
  - Adding a feature that touches the local fleet WITHOUT emitting
    a WITNESS_MARK. The Mycelium cluster misses your work.
  - Writing directly to SurrealDB without UPSERT. UPDATE no-ops on
    new records; you lose the row.
  - Putting vault notes in the wrong directory. The thin waist is
    per-day (`01-Learnings/EXEC-YYYY-MM-DD/`); per-week breaks the
    pattern.
  - Using a custom Prometheus-style counter instead of the bus. The
    sink infrastructure is already in place; reuse it.
  - Setting coherence to 0.5 (the baseline) for non-trivial events.
    The 12D point + coherence value is the data Ouroboros consumes.
  - Reading the bus via `asyncio.create_task` polling. The bus has
    subscribe() — use it.
  - Emitting a WITNESS_MARK for every cache hit. Use the per-(task,
    model) 1/hour cooldown. Without it, the bus is a firehose.
related_skills:
  - cohezion-extend-availability (recursive-forge sweep that found
    zero callers; the *motivation* for this skill)
  - cohezion-semantic-cache-api (Connection B; cache key contract)
  - cohezion-dynamic-modularity (module-level additive composition)
  - compound-build (the build ritual that surfaced this pattern)
  - autoharness-skill (auto-harness for testing this pattern)
verification:
  before_landing:
    - Every new code path that produces a result has a WITNESS_MARK
      emission (or an explicit "stateless, no emission" comment).
    - Every new code path that consumes datamesh evidence queries
      SurrealDB (not just the bus; the bus is for live events only).
    - The vault note path is per-day (`EXEC-YYYY-MM-DD/`).
  after_landing:
    - `git grep "PrecipitationEvent(" src/` shows the writer pattern
      is in use.
    - `git grep "asyncio.create_task(_upsert_surreal" src/` shows the
      fire-and-forget SurrealDB pattern is in use.
    - `git grep "bus.subscribe" src/` shows readers use the bus.
honest_residuals:
  - The 5 surfaces aren't all equally instrumented. Mycelium is
    best-effort (subscribes to the bus but the verify_evolve query
    is a no-op stub). SurrealDB is fire-and-forget (bus outage
    doesn't block). The Ouroboros HEALING_EVENT consumer side
    (HealerAgent) is unwired.
  - The 4 lane scripts in `scripts/lanes/` only prove out at 04:00.
    Their deep paths aren't covered by the mocked tests.
  - "Latest card wins on conflict" is the WS1 policy; the bus
    doesn't yet invalidate cache rows when a card's `read_at`
    changes. That's a follow-up.
version: 1
captured: 2026-06-04
captured_from: cohezion-internal PRs #223-#226 (WS1+WS2 datamesh build)
