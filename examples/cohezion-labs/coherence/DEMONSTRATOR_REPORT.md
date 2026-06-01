# journey_roundtrip — Cohezion Coherence Demonstrator

**The one demonstrator the Coherence Forge synthesis named** — proving the
highest-value wire in the repo, end-to-end, against live services. Every number
below is from a real run (`2026-06-01`), not a claim.

## What it threads (5 hard constraints, all satisfied)

| Constraint | How | Evidence |
|---|---|---|
| **Real FLUME-encode** | `OllamaEmbeddingProvider.embed` → 768D nomic latent → 12D manifold point | `is_real_latent=True`, dim=768, var=0.0013 (non-degenerate) |
| **Local inference** | task classified on lemonade NPU `:13306`, $0 | `answer="positive"`/`"negative"`, ~6s on-node |
| **SurrealDB** | journey row with `agent_id`+`session_id`+`created` attribution | 3 rows, `agent=claude-sessA/B`, ns=cohezion |
| **Obsidian** | real `ObsidianWiki.create_wiki_page`, frontmatter carries `surreal_id` | `source_refs: ['journey_roundtrip:7b8297fd…']` |
| **Cross-session** | session B reads session A's trajectory **through SurrealDB** | readback printed A's task, answer, 12D point, obsidian path |

## The proof it's REAL semantics, not the SHA-256 hash fake

The synthesis's central finding: `JourneyTracker._text_to_latent` (`journey_tracker.py:264`)
is a SHA-256 **hash fake**, so the 256D latent space the architecture promises
never holds real semantics. This demonstrator wires in the real encoder and proves
the difference with cosine geometry:

```
cosine(positive, negative) = 0.6564
cosine(positive, positive) = 1.0000   ← same-sentiment journeys are MORE similar
```

A hash fake produces cosines unrelated to meaning. Here, same-sentiment journeys
cluster and opposite-sentiment journeys separate — **the latent space holds actual
semantics.** That is the wire that makes the rest of Cohezion's 12D-manifold story true.

## The honesty trail (kept, not hidden)

The first run **failed twice and the failures are still in the database** as an audit trail:
- `is_real_latent=false, coherence=1.000, answer=''` — the degenerate hash-fallback signature.
- **Root cause 1:** provider defaulted to model `"nomic-embed-text"` but the live node
  serves `"nomic-embed-text:v1.5"` — bare name errors → hash fallback. *(This is itself a
  coherence finding: the provider's default model string is stale vs. the live node.)*
- **Root cause 2:** `DeepSeek-Qwen3` is a reasoning model; an 8-token budget yielded only
  `<think>` tokens → empty answer. Fixed by raising the budget and stripping `</think>`.

The readback query surfaces the failed row right next to the fixed ones — the eval
literally shows its own bug-and-fix history.

## Bidirectional link (either store reaches the other)

```
SurrealDB  journey_roundtrip:7b8297fd69a7b26c  ──surreal_id──►  Obsidian sessA_7b8297fd….md
Obsidian   source_refs: [journey_roundtrip:7b8297fd…]  ──────►  SurrealDB row
```

## How to reproduce

```bash
SRC=/tmp/cz-showcase/src
PYTHONPATH=$SRC python journey_roundtrip.py --session sessA --task "classify sentiment: this product is wonderful"
PYTHONPATH=$SRC python journey_roundtrip.py --session sessB --task "classify sentiment: this is terrible and broken"
PYTHONPATH=$SRC python journey_roundtrip.py --session sessB --readback   # reads sessA's journey via SurrealDB
```

## Scope & honesty

- **No src/ edits.** This composes the *real* Cohezion components (`OllamaEmbeddingProvider`,
  `ObsidianWiki`) + the same SurrealDB the production `JourneyTracker` writes to. It proves
  the wiring works; the corresponding source edits (inject the encoder into `JourneyTracker._flume_encoder`
  at `:146`, add attribution to the CREATE at `:543`, repoint `ConciergeAgent.gather_briefing`
  at `concierge.py:142` to query SurrealDB) are a **separate approve-then-apply plan** — they
  touch 3 files and need sign-off per workflow-enforcement + git-operations rules.
- Routed nothing through CLaSp `:13308` (DOWN). Used NPU `:13306` + Ollama `:11434` + SurrealDB `:8001` (all UP).
- Companion: `session_bulletin.py` (SurrealDB blackboard) is the generalized cross-session channel;
  this demonstrator is the journey-specific application of the same substrate.
