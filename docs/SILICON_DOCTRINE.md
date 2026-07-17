# Silicon Doctrine — how this box's NPU, iGPU, and CPU are leveraged

One page, measured facts only. Sources: NPU gauntlet (1,400+ verified trials,
2026-07-17), thinking-models playbook, harness N-invariants. If you are code
about to call a model: use `cohezion.inference.gauntlet._call_model` (blessed
path) and pick per this table. Regenerate stale numbers from the gauntlet
leaderboard (`python -m cohezion.inference.npu_gauntlet --report`), never edit
them by hand.

## NPU — XDNA2 via FastFlowLM (~2W; the always-on lane)

- **Single-model slot** (loading evicts the occupant; swap 13–37 s). Serialize
  work per model; conflict = occupant ≠ what YOU last loaded.
- **Champion (measured):** `qwen3-4b-FLM` — 1.000 accuracy / 17.4 TPS on
  exactly-verifiable tasks. Latency fallback: `llama3.2-1b-FLM` (fast, 0.73
  acc). Best tiny: `lfm2.5-it-1.2b-FLM` (0.86 acc, 16.9 TPS).
- **`deepseek-r1-0528-8b-FLM`: hard multi-step reasoning ONLY** — pure
  reasoner, ranked LAST (0.584) on easy tasks; cannot disable thinking, only
  cap it.
- **Never send logprobs/completions-echo requests to FLM** — the backend
  wedges (4h silent hang, 2026-07-17). Generation only.
- **No thermal coupling** (|r| ≤ 0.11, 45–84 °C): run it 24/7 without guilt.
  Version bumps, not heat, are the drift risk — log server version.
- Injection resistance: 1B-class models obey embedded injections — route
  untrusted-input tasks (email/web content) to ≥3B.

## iGPU — RDNA3.5 via llama.cpp/Vulkan GGUF (the heavy lane)

- **Resident workhorse: `Gemma-4-26B-A4B`** (serves both `interactive` and
  `bbq` roles per the 2026-07-17 retarget — ONE heavy tenant, not two; the
  35B-MTP is excluded from role selection).
- **Logprobs + grammar/JSON-schema live here** (FLM has neither). Grammar is
  INACTIVE while thinking is on — structured output = non-think + grammar, or
  two-call (reason free → extract strict).
- Thinking models (26B-A4B, Qwen3.*) burn max_tokens in-think. The fix is NOT
  a bigger cap for its own sake (local tokens are free) — it's `--reasoning-
  budget` at LOAD so the answer channel survives (lemonade ignores per-request
  toggles, #1511). Until the two-profile setup lands: set max_tokens
  GENEROUSLY (2-4k; KV-cache is the only real bound) and read
  reasoning_content.
- MES-hang discipline (harness N3.6): one heavy iGPU job at a time on a quiet
  box; prefer `-b 256`+ small ubatch on heavy models.

## CPU — the overflow lane, rarely optimal

- Unified memory means the iGPU usually wins; CPU hosts sidecars (kokoro TTS)
  and is the escalation hop before cloud. Don't build for it first.

## Cross-cutting law (enforced, not advisory)

0. **Local tokens are effectively unlimited; cloud tokens are the metered
   resource.** Never trim local max_tokens for "cost" — a false truncation
   (empty content, missing think headroom) is the real cost. Local caps exist
   for exactly two reasons: bounded KV-cache/ctx_size (N3 — the OOM crasher)
   and hard wall-clock deadlines (wedge protection). Be generous by default;
   be frugal only on the cloud lane, where escalation must clear the
   feynman-weight bar.
1. **Blessed call path:** all local LLM calls go through
   `cohezion.inference.gauntlet._call_model` (think-strip, reasoning_content
   fallback, hard timeouts). CI gate flags raw urllib/httpx chat calls.
2. **RAM:** 16 GB floor inviolate (K1/N3); NPU swaps charge the DELTA;
   memory-freeing swaps always allowed; idle-eviction sweep unloads ≥8 GB
   models provably idle ≥30 min when < 24 GB.
3. **Escalation order:** NPU → iGPU → CPU → cloud LAST (feynman weight: cloud
   needs ≥2.72× local quality to win). Model-per-role comes from
   `FleetRoster.select(role)` — it reads live gauntlet quality; never
   hardcode a checkpoint.
4. **Thinking by difficulty:** easy/verifiable/categorical → non-think; hard
   multi-step → capped thinking. The gauntlet keeps this table honest.
