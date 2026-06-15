# Submission Hardening — Kaggriculture capstone (Google AI Agents, capstone ~Jun 19–30)

Lessons from the Nemotron Kaggle deadline run (2026-06-15), shaped for a Kaggle **simulations**
agent (this is `kaggle_environments`, not a training-notebook or a bridge-based service). See
the global skills `local-inference-hackathon-hardening` and `kaggle-simulations-agent-submission`.

## Current state

`submission.py` is a standalone heuristic `agent(observation, configuration)` (ConnectX-style
reference). The competitive farming-sim capstone agent opens ~Jun 19; no local-inference call
exists yet, so there is no bridge to harden here — the hardening is the **sim-agent discipline**
below, to apply when the real agent is built.

## Sim-agent rules (apply when building the capstone agent)

1. **Standalone FILE, not notebook globals.** Kaggle scores the submitted `submission.py` agent
   function in isolation — anything defined only in notebook scope is invisible at scoring time.
2. **Per-tick deadline + heuristic fallback.** The harness KILLS slow/erroring agents. Wrap any
   model call in a hard per-tick timeout and ALWAYS have a fast deterministic fallback move, so a
   slow/empty/erroring inference never forfeits the tick. (This is the sim-agent analog of the
   "$0-baseline banked first" rule — the heuristic IS your banked floor.)
3. **If using local inference**, follow the doctrine: classify→NPU, generation→iGPU/omni, with a
   strict timeout; treat an empty local reply as "use the heuristic this tick" (escalation /
   fallback, never a retry-loop). Prefer the OMNI models (`Gemma-4-E4B` / `Llama-4-Scout` on
   `:13305`, bounded-ctx, N3-safe) if any visual/board state benefits from a vision model.
   Remember: the scoring sandbox likely has **no GPU and no network** — a local-inference agent
   must degrade to the heuristic when the fleet is unreachable, which is the common case at scoring.
4. **Verify-before-fail.** When testing locally, confirm the agent file actually loaded and ran a
   full episode before concluding it "scored 0" — a packaging/import error reads identically to a
   bad strategy.

## Pre-submit checklist

- [ ] Agent is a self-contained `submission.py` (`env.run` works from the file alone).
- [ ] Every tick has a deterministic fallback within the time budget; no unguarded model call.
- [ ] Tested through a full `kaggle_environments` episode locally before submitting.
- [ ] If local inference is used: strict timeout + heuristic fallback when fleet/GPU/network absent.
