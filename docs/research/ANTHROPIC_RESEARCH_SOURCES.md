---
title: "Anthropic research — standing source for the local-inference research loop"
created: 2026-06-07
owner: "research loop (BLEEDING_EDGE_FEED.md) + daily Anthropic-paper check"
cadence: "daily new-paper check"
discipline: "verify-before-cite, map-to-seam, default needs-experiment — same as the HF/arXiv research loop"
---

# Anthropic research as a standing research-loop source

User directive 2026-06-07: *"part of our local inference research should include all of Anthropic's
research, with daily checks for new papers."* This folds Anthropic's research output into the same
loop that sweeps HuggingFace + arXiv (`BLEEDING_EDGE_FEED.md`), under the SAME discipline.

## Sources (paper-bearing subset of the 11 anthropic-intel sources)

Canonical list lives in `~/.claude/anthropic-intel/sources.json` (single source of truth — do NOT
duplicate the full ecosystem list here). The RESEARCH subset this loop checks for new **papers**:

| id | url | what |
|---|---|---|
| `anthropic-research` | https://www.anthropic.com/research | primary research papers |
| `alignment-science` | https://alignment.anthropic.com | alignment / safety research |
| `transformer-circuits` | https://transformer-circuits.pub | interpretability (NOT in the 11 — added here) |
| `system-cards` | https://www.anthropic.com/system-cards | model cards / capability+safety evals |
| `project-glasswing` | https://red.anthropic.com | red-team / frontier-risk research |
| `anthropic-institute` | https://www.anthropic.com/institute | policy/position (e.g. RSI piece, FEED Round 32) |

(Ecosystem sources — CLI/API release-notes, deprecations — stay with `/anthropic-scan`, NOT this
research loop. This loop is PAPERS only.)

## Daily-check protocol (one focused round, throttle-gated)

1. **Throttle FIRST** (doctrine bullet 5): `python scripts/loop_usage_guard.py` — obey proceed/throttle/halt.
2. For each source, find papers/posts newer than the last check (the FEED's last Anthropic round date).
3. **VERIFY before citing**: every arXiv id via `WebFetch arxiv.org/abs/<id>`; every claim against the
   primary page. NEVER cite from a search summary or pop-sci framing. Unverifiable → omit + log.
4. **Map to a cohezion seam** (CostAwareRouter / FleetRegistry / triune_orchestrator / semantic_cache /
   resource_manager / compound-loop / governance) and classify NEW / grounded / needs-experiment /
   regression-risk. Anthropic safety/governance pieces usually map to **safeguard grounding**
   (loop doctrine), NOT a $0 fleet lever — classify honestly (the RSI piece, Round 32, is the model).
5. **Append** a date-stamped row to `BLEEDING_EDGE_FEED.md`. A finding is a backlog TODO only if
   VERIFIED + fleet-runnable + additive + high-value (respect invariants A3/A4/A5/CA1/CC2/LM6 + K1/rule-5;
   default needs-experiment, never confirmed). Most Anthropic research → insight/grounding, not a lever.
6. **Honest empty round**: if nothing new/verifiable, append a one-line "no new verified Anthropic
   papers" note. NO fabricated ids, NO hype rows. A couple of verified items beat a list.
7. Commit docs surgically (`git --no-verify`, explicit paths). NO `src/` edits — the build loop owns code.

## Cadence + durability

- Daily local durable cron (fires when a session is idle that day). Recurring crons auto-expire after
  7 days → renew weekly, or promote to a cloud `/schedule` routine for session-independent daily runs
  (caveat: a cloud routine reports to claude.ai and cannot write this local feed — a local session
  would then ingest it).
- `~/.claude/anthropic-intel/.last-scan-date` tracks the ecosystem scan; this paper loop uses the
  FEED's latest Anthropic round date as its "since" watermark.
