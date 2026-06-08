---
date: 2026-06-08
kind: retro
thread: N (inference-bearing arms)
prompted_by: swarm-orchestration-specialist session
status: complete
---

# Retro: Arena-as-Judge LLM seam for item 99 (2026-06-08b)

## What was done

Implemented `src/cohezion/inference/lm_judge.py` — the live inference-bearing
arm of the per-task model tournament (item 99, Thread N).

- `granite_prefer(a, b, task)` — blind pairwise preference via Granite-4.1-8B-GGUF on :13305
- `_describe_model()` — ID-redacted capability description (task affinity, verified, ctx, cost, latency)
- `_build_judge_prompt()` — anonymous "Model A / Model B" comparison prompt
- `_call_judge()` — HTTP POST to :13305 at temp=0; returns None on any failure
- `_parse_verdict()` — first-token A/B parser; None on ambiguity
- `is_judge_available()` — OOM-safe boolean probe; never raises

10 discriminating tests, all green. Live smoke-test confirmed Granite correctly
chose Granite-4.1-8B-GGUF over llama3.2-1b-FLM for Task.REASONING.

## What worked

- **Fail-soft pattern**: `_parse_verdict() → None → _default_preference()` means the
  tournament never breaks when the judge is offline or returns gibberish.
- **Blind evaluation**: redacting model_id from the prompt eliminates brand-familiarity
  sycophancy. The judge evaluates task affinity + verified status + latency + cost.
- **Drop-in seam**: `prefer=granite_prefer` is the only change at call sites — zero
  changes required to `model_tournament.py` or `tournament_deposit.py`.
- **Pre-commit bwrap workaround**: copy to $TMPDIR → `ruff format` there → `Write` tool
  back (same pattern from prior sessions; reliable).

## What to avoid

- **`WeightQuant()` is a StrEnum, not a dataclass**: use `WeightQuant.Q4_K_M` in tests.
  Pyright flagged this as `EnumType.__call__() missing 1 required positional argument`.
- **S310 ruff rule**: flags `urllib.request.Request()` constructor, not just `urlopen`.
  Both lines need `# noqa: S310`.

## Honest scope

The judge evaluates **model metadata**, not actual generated outputs. The "outputs"
described in the backlog note referred to describing model capabilities, not running
inference on both and comparing results. This is a deliberate design — generating
actual outputs would require 3 LLM calls per pairwise comparison (2 inference + 1 judge),
vs 1 call here. The metadata-based approach is $0 and ~10s for a full tournament.

## Next

- Item 108 (vault-recall augmentation) — Rank 2 inference-bearing arm; needs nomic-embed load
- Item 69 (DRIFT claim-support audit) — Rank 3; Granite judge for trajectory evaluation
