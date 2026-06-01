# cohezion-labs

Durable home for the Cohezion demonstrators built across sessions. Everything
here runs against the **live main checkout** at `/home/mike-anderson/dev/cohezion/src`
(set in `env.sh`) — no vendored copy of `src`, so the demos always test the real code.

## Quick start

```bash
./run.sh showcase            # one showcase cycle: 13 live capability probes + report
./run.sh eval 20             # agentic eval on ManifoldEnv, 20 seeds, + report
./run.sh journey sessX "classify sentiment: this works"   # capture a journey
./run.sh readback sessY      # read OTHER sessions' journeys via SurrealDB
./run.sh roster              # who's alive on the cross-session bulletin
./run.sh post sessX status "hello peers"
```

## What's here

| Dir | Artifact | What it proves |
|---|---|---|
| `showcase/` | `showcase_engine.py`, `run_showcase.sh`, `showcase_report.py` | 13 Cohezion capabilities exercised live ($0, K1-safe); every probe provenance-stamped VERIFIED/SIMULATED/FAILED. Output history + atlas in `showcase_output/`. |
| `eval/` | `eval_harness.py`, `eval_report.py` | Rigorous agentic eval: a reward-hack beats a capable agent on scalar reward; the eval catches it via behavioral metrics. Env hardened so passive can't win by physics. |
| `coherence/` | `journey_roundtrip.py` | Real 768D-nomic journey → SurrealDB + Obsidian (bidirectional link) → cross-session read-back. Proof of real semantics: cosine(pos,neg)=0.66 vs cosine(pos,pos)=1.00. |
| `coherence/` | `session_bulletin.py` | SurrealDB-backed blackboard so concurrent Claude sessions coordinate (presence roster + addressed/broadcast messages). |
| `coherence/` | `COHERENCE_MAP.md`, `DEMONSTRATOR_REPORT.md` | The Coherence Forge wiring plan (52 components, orphan edges) + the demonstrator writeup. |

## Live substrate this depends on (verify before running)

- lemonade nodes: NPU `:13306`, iGPU `:13307`, CPU `:13309`, router `:13305`, Ollama `:11434` (nomic-embed-text:v1.5) — CLaSp `:13308` is usually DOWN, not used.
- SurrealDB `:8001` (ns=cohezion, db=main, root:root).
- Obsidian vault `~/vaults/cohezion-vault/`.

If a node is down a probe reports FAILED honestly — that's expected, not a regression.

## Honesty contract

No `src/` edits were made to produce these — they compose the real Cohezion
components + live services. The corresponding source edits (e.g. wiring the real
encoder into `JourneyTracker._flume_encoder`) are a separate approve-then-apply
plan; see `coherence/DEMONSTRATOR_REPORT.md`.
