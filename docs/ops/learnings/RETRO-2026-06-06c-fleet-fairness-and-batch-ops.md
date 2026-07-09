---
title: "Retro — background fleet jobs starve the live bot; batch-ops traps"
date: 2026-06-06
tags: [retro, fleet, hermes-bot, operations, batch, incident]
---

# Retro 2026-06-06c — fleet fairness & batch-ops

Covers items 64/65 (simplicity audits) + the tutorial-distillation pipeline run (431 tutorials,
local inference) and the incident it caused: the live Hermes Telegram bot went to empty-response.

## Incident: my background job broke the user's live bot
The 431-tutorial distillation fired 71+ back-to-back Granite calls at the shared `:13305` lemonade
fleet. That saturated the iGPU, so the bot's interactive requests timed out and its empty-content
guard exhausted after retries — the user got "No reply: model returned empty content." The model
itself was FINE (a bare curl returned clean content); the failure was **fleet contention**, not the
empty-response/thinking trap. Fix: killed the distillation procs → bot served clean replies again.

**Lesson (→ backlog item 113):** the shared local fleet has NO fairness between batch and interactive
work. A heavy local-inference batch MUST yield to the live bot. Before launching a fleet-heavy
background job, either (a) throttle it (sleep between calls / cap in-flight), or (b) gate it on
interactive-latency staying low. "$0 local" does not mean "free of contention" — GPU time is the
scarce resource, and the interactive bot is the priority tenant.

## Reusable operational traps hit this session
1. **`pkill -f <pattern>` self-match.** `pkill -f "distill_tutorials.py"` matched its OWN command line
   (which contains the pattern) → killed my own shell (exit 137). ALWAYS kill by PID:
   `ps -eo pid,args | grep <pat> | grep -v grep | awk '{print $1}'` then `kill`, or use a pattern the
   killer's own cmdline can't match. Same class as a `grep` counting itself.
2. **`nohup … &` inside a `run_in_background` Bash command is self-defeating.** The wrapper exits
   immediately (firing a false "completed"), and the bwrap sandbox's `--die-with-parent` reaps the
   detached child. Let the Bash tool's own `run_in_background` own the long command directly — one
   lifecycle owner, no inner `&`.
3. **Bulk external fetch needs rate-limit tolerance + resume.** 431×2 `gh api` calls hit GitHub's
   rate limit; 356/431 fetch-failed. One bad fetch (an error-JSON, not a URL) had crashed the whole
   batch via `urlopen`. Fix: skip non-`http` results + catch per-file errors (one failure costs one
   item, not the batch) + a resume marker (`$DISTILL_DONE_FILE` skips done names) so a relaunch
   continues. The results file IS the checkpoint.

## Tutorial-distillation outcome (the actual deliverable)
431 tutorials, 71 real distillations (356 rate-limited → re-run after reset via resume). The local
SLM flagged 13 gaps; my filter found **0 genuine new levers** beyond batch-1's recency-decay (item
109) — every gap mapped to existing cohezion machinery (swarm/SCP, EvaluationHarness, OCR_DOC,
deep_research, ConstitutionalEnforcer, autoresearch-K-Search-Tree=UCT) or was off-fleet (NVIDIA FP8).
That 0 is the filter WORKING: a mature platform's "gaps" mostly aren't.

## Persisted
- Items 109 (recency-decay), 111 (storage index), 112 (memory-pressure GC), 113 (fleet-fairness).
- `scripts/research/distill_tutorials.py` (resumable, transient-failure-tolerant) for re-running the 356.
