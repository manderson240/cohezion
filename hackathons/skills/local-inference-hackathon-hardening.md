---
name: local-inference-hackathon-hardening
description: |
  Harden an agent/competition submission that runs on the local AMD silicon fleet
  (NPU/iGPU/CPU lemonade) so it is robust, honest, and OOM-safe before a deadline.
  Use when: (1) prepping a hackathon/Kaggle submission whose agents claim to run on
  local inference ("$0/loop", "NPU->iGPU->CPU tiers"), (2) wiring a local-first
  inference path with cloud fallback, (3) a submission artifact looks empty/zero and
  you're about to "fix" it, (4) you need a pre-submit checklist for a local-inference
  entry. Distilled from the Nemotron Kaggle deadline run (2026-06-15) + harness N3.
  Pairs with hermes-local-inference-routing, kaggle-simulations-agent-submission,
  and local-inference-default.md.
---

# Local-Inference Hackathon Hardening

Five hard-won rules for shipping a local-inference submission that works AND is honest.
Each rule has a failure it prevents and a concrete check.

## 1. Verify-before-fail (the "0-byte" trap)

**A freshly-created file at 0 bytes is ambiguous: empty vs. not-yet-written.** Large
artifacts (multi-GB adapters, model downloads, checkpoints) stream in; reading size
mid-stream reports 0. Do NOT diagnose a failure — or launch a "fix" — from an
incomplete artifact.

- **Check:** wait for the writer/downloader process to EXIT (or size to be stable across
  two reads ≥5s apart) before judging. `pgrep -f <downloader>` then `stat -c %s`.
- **Applies to your OWN diagnostics**, not just the model's outputs (systematic-debugging:
  "verify your inputs before investigating output processing"). On the Nemotron run a 3.5GB
  LoRA adapter read as "0 bytes" twice and nearly triggered a needless deadline-day re-run;
  the file was intact once the download finished.

## 2. Bank a working $0-local baseline FIRST, then add ambition

Get a known-good, provenance-clean submission scored/banked EARLY. Leaderboards (Kaggle)
and most hackathon judges keep your best — so a banked floor means every later attempt has
**zero downside**. Only *non-completion* or a *broken artifact* costs you; a slightly lower
score does not. Spend remaining time on upside, not on protecting the floor.

## 3. OOM-safe local routing (harness N3)

The fleet runs on 128GB unified memory; footprint is driven by **ctx_size/KV-cache, not
param count**.

- **Route NPU(13306) -> iGPU(13307) -> CPU(13309) -> cloud** — cheap/fast first, escalate
  only on failure or quality-gate miss.
- **Hit dedicated per-tier ports directly** for agent inference. The unified router `:13305`
  will AUTO-LOAD an uncached/`ctx_size=0` heavy model unattended and can hard-hang the box
  (N3). If you must use `:13305`, pre-load with a **bounded** ctx: `POST :13305/api/v1/load
  {"model_name":..., "ctx_size":16384, "save_options":true}`.
- **Never send a chat request naming an uncached or `ctx_size=0` heavy (>=26B) model to
  :13305.** Treat `ctx_size=0` on a heavy model as a STOP condition.
- Gate any in-process model load on free RAM (a ResourceGuard / `free -h` check, ~16GB
  buffer) so a load escalates to cloud rather than OOM-hanging.

## 3b. Leverage OMNI (multimodal) models — they're free and already loaded

The fleet's most capable local models are **omni / multimodal**: verified via the router
catalog (`GET :13305/api/v1/models/<id>` -> `labels`), `Gemma-4-E4B-it-GGUF` and
`Llama-4-Scout-17B-16E-Instruct-GGUF-Q4_K_M` carry labels `vision` + `tool-calling`
(Gemma-4-31B too). Prefer these over text-only IDs:

- A single local call handles **text AND images** (OpenAI-style `image_url` content block) at
  $0 — useful for Slack image uploads, UI screenshots, document review.
- They are **N3-safe** to request via `:13305`: Gemma-4 carry a bounded `ctx_size` (16384),
  Llama-4-Scout is in the no-KV-risk class. (Confirm `recipe_options.ctx_size` is not 0.)
- **Prefer models that are ALREADY LOADED**, not merely present in the catalog. Query
  `GET :13305/api/v1/health` → `all_models_loaded[].model_name` and pick from that set. The
  router caps concurrent models, so requesting an unloaded one triggers an auto-load that
  evicts a loaded model — thrashing the GPU and disrupting any co-running session. Don't
  hardcode stale text-only IDs (e.g. a `deepseek-*-FLM` not in the catalog).
- Other modalities are separate fleet models: Whisper (audio-in), kokoro (TTS), SD-Turbo /
  Flux (image-out). "Omni" is the *fleet*, not one model — route each modality to its model.

## 4. Empty response = escalation signal, not a bug (L369)

Local SLMs probabilistically return `""` on structured prompts (calibration: declining
to answer rather than hallucinating). Design the CALLER to treat `""` as "escalate to the
next tier / cloud", NOT to retry-loop or force-generate. A fallback chain converts the
non-answer into a zero-cost escalation.

```python
for tier in ("npu", "igpu", "cpu"):
    text = LemonadeClient(tier).complete(prompt, max_tokens=bounded)
    if text.strip():
        return text, tier          # served locally, $0
return cloud_complete(prompt), "cloud"   # honest fallback
```

## 5. Honest backend attribution + standalone artifact (measurement integrity)

- **Report the backend that ACTUALLY served the request**, not what was *reachable*.
  `cohezion_cpu_tier_used = lemonade_available("cpu")` is a LIE if generation went to the
  cloud — it reports a probe, not a fact. Set the flag from the value returned by the
  fallback chain (`backend == "cpu"`), or rename it `local_tiers_available`.
- If the README claims "$0/loop on AMD silicon", generation must actually route local-first
  (rule 4) for the claim to be true. Task-appropriate routing is legitimate: classification
  -> NPU, structured codegen -> cloud. Just don't *claim* local while calling cloud.
- **The submission must be a self-contained artifact**, not notebook globals (Kaggle scores
  a standalone FILE/agent). Verify tooling versions before relying on them: `which -a <cli>`
  (PATH may resolve a different binary than your venv), and confirm the install actually
  bumped (`<cli> --version`).

## Pre-submit checklist

- [ ] Artifact verified COMPLETE (rule 1) — size stable, weights non-zero, loads in runtime.
- [ ] A provenance-clean baseline is already banked (rule 2).
- [ ] Inference routes NPU->iGPU->CPU->cloud; no heavy `ctx_size=0` load via :13305 (rule 3).
- [ ] Empty local responses escalate, never retry-loop (rule 4).
- [ ] Reported backend/cost reflects what actually ran; claims match behavior (rule 5).
- [ ] Submission is a standalone artifact; CLI/tool versions confirmed (`which -a`, `--version`).
