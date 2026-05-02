# Pi Agent + Lemonade Hardware Routing

**Platform:** AMD Ryzen AI MAX+ 395 (Strix Halo) — 128 GB LPDDR5X unified memory
**Tested:** 2026-05-01 · **Updated:** 2026-05-01 (Qwen3.6 + reason tier)

Pi agent routes automatically between three Gemma 4 hardware tiers via the Lemonade inference server. Routing decisions happen per-turn before the LLM request is dispatched.

---

## Architecture

```
Pi agent
  │
  ├─ lemonade-router.ts extension
  │    ├─ session_start  → health-check endpoints + set default model
  │    ├─ input event    → score message → setModel()
  │    ├─ turn_end       → fire-and-forget Mycelium turn log → cohezion :8080
  │    └─ /lemonade      → manual control
  │
  ├─ ~/.pi/agent/models.json  (provider registration at startup)
  │    └─ provider: "lemonade"
  │         ├─ user.Qwen3.6-35B-A3B-GGUF-Strix-Q4_K_M → :13307  iGPU ROCm (default)
  │         ├─ DeepSeek-Qwen3-8B-GGUF                  → :13307  iGPU ROCm (reason tier)
  │         ├─ Gemma-4-31B-it-GGUF                     → :13307  iGPU/CPU ROCm
  │         ├─ gemma4-it:e2b                            → :13306  NPU XDNA 2 (FLM)
  │         ├─ Gemma-4-26B-A4B-it-GGUF                 → :13307  iGPU ROCm [legacy]
  │         └─ Gemma-4-E4B-it-GGUF                     → :13307  iGPU ROCm
  │
  ├─ lemond (systemd)    :13307  ROCm — iGPU + CPU models
  ├─ flm serve           :13306  FLM  — NPU (XDNA 2) Gemma 4 E2B
  └─ cohezion API        :8080   Mycelium turn logging (optional, graceful fallback)
```

---

## Hardware Tiers

| Tier | Port | Model | Backend | Context | Best for |
|------|------|-------|---------|---------|----------|
| **NPU** | `:13306` | `gemma4-it:e2b` (2B) | FLM (XDNA 2) | 8K | Ack turns, yes/no, <60 char replies |
| **REASON** | `:13307` | `DeepSeek-Qwen3-8B-GGUF` (8B) | ROCm | 32K | Debug, explain why, step-by-step trace |
| **iGPU** | `:13307` | `user.Qwen3.6-35B-A3B-GGUF-Strix` (35B MoE, 3B active) | ROCm | 128K | Code, refactor, agentic tasks — **default** |
| **CPU** | `:13307` | `Gemma-4-31B-it-GGUF` (31B dense) | ROCm | 32K | Long analysis, architecture review |

> **Qwen3.6-35B-A3B** is a Mixture-of-Experts model: 35B total parameters, ~3B active per token.
> Released 2026-04-16 (MoE) / 2026-04-22 (27B dense). The Strix-optimized Q4_K_M quantization
> fits comfortably in 128GB unified memory with ~18GB active. Benchmarks show it outperforms
> 397B MoE models on agentic coding tasks.
>
> **DeepSeek-R1-0528 distilled to Qwen3-8B** (REASON tier): reasoning model with extended
> `<think>` chain-of-thought. Released ~2026-04-28. Ideal for debugging and trace tasks
> where chain-of-thought beats brute parameter count.

---

## Setup

### 1. Start backends

```bash
# lemond (manages iGPU/CPU models) — usually already running
sudo systemctl status lemond   # check
sudo systemctl start lemond    # start if needed

# NPU — only needed if you want the NPU tier
flm serve gemma4-it:e2b --port 13306 --quiet &
```

### 2. Verify endpoints

```bash
for p in 13306 13307; do
  curl -s -o /dev/null -w ":$p %{http_code}\n" --max-time 1 http://localhost:$p/v1/models
done
# :13306 200   (NPU — only if you started FLM)
# :13307 200   (iGPU/CPU — lemond)
```

### 3. Confirm Pi sees the models

```bash
pi --provider lemonade --list-models
# provider  model                    context  max-out  thinking  images
# lemonade  Gemma-4-26B-A4B-it-GGUF  32.8K    4.1K     yes       yes
# lemonade  Gemma-4-31B-it-GGUF      32.8K    8.2K     yes       yes
# lemonade  Gemma-4-E4B-it-GGUF      16.4K    2.0K     yes       yes
# lemonade  gemma4-it:e2b            8.2K     512      no        no
```

### 4. Launch Pi

```bash
# Default: iGPU 26B (best for coding)
lemonade-launch-pi

# With NPU server already running
lemonade-launch-pi --npu

# Specific model
lemonade-launch-pi -m Gemma-4-31B-it-GGUF
```

---

## Routing Logic

The extension's `input` handler runs before every turn and calls `pi.setModel()`.

```
message.length ≤ 60 chars AND matches ack pattern
    → NPU    (gemma4-it:e2b, :13306)          2B  FLM

matches debug/explain/trace pattern
    → REASON (DeepSeek-Qwen3-8B-GGUF, :13307) 8B  chain-of-thought

message.length > 200 chars OR matches deep analysis keywords
    → CPU    (Gemma-4-31B-it-GGUF, :13307)   31B  dense

everything else (code tasks, the default)
    → iGPU   (user.Qwen3.6-35B-A3B-..., :13307) 35B MoE (3B active)
```

Ack pattern: `ok`, `yes`, `done`, `lgtm`, `looks good`, `continue`, `thanks`, `great`, etc.

Reason pattern: `debug`, `explain how/why/what`, `why is/does/did`, `step by step`, `walk me through`, `trace`, `root cause`, `diagnose`, etc.

Analysis keywords: `review all`, `audit`, `analyze the entire`, `architecture`, `deep dive`, `end-to-end`, `trace through`, etc.

If an endpoint is down, the router degrades gracefully toward iGPU.

---

## Test Results (2026-05-01)

All tests used `pi --no-tools --no-session -p "<prompt>"` in print mode.

### iGPU 26B — coding task

```
Prompt:   "Write a Python one-liner that prints numbers 1 to 5."
Response: print(*range(1, 6), sep='\n')
Time:     24.5s total (includes Pi startup + session summary)
Model:    Gemma-4-26B-A4B-it-GGUF (26B MoE, ROCm on gfx1151)
Port:     :13307
```

### CPU 31B — same prompt

```
Prompt:   "Write a Python one-liner that prints numbers 1 to 5."
Response: print(*range(1, 6))
Time:     34.2s total
Model:    Gemma-4-31B-it-GGUF (31B dense, ROCm on gfx1151)
Port:     :13307
```

### iGPU E4B — quick question

```
Prompt:   "What is 2+2? Answer with just the number."
Response: 4
Time:     30.9s total (E4B was cold-loading on first call)
Model:    Gemma-4-E4B-it-GGUF (4B, ROCm)
Port:     :13307
```

### NPU — Gemma 4 E2B via FLM (XDNA 2)

```
Prompt:         "What is 2+2? Just the number."
Response:       4
Time (total):   18.9s
FLM startup:    ~10s (cold NPU model load into XDNA cache)
TTFT (1st req): 6.1s  (prefill_duration_ttft from FLM usage chunk)
TTFT (2nd req): 1.6s  (warm — XDNA cache hot)
Decoding speed: 15.5 tok/s  (2nd request)
Model:          gemma4-it:e2b (2B, FLM on XDNA 2)
Port:           :13306
NPU lock log:   🟢 NPU Locked! / 🔵 NPU Lock Released!
```

Ground truth that requests hit the NPU: `[🟢 NPU Locked!]` in FLM's log.

---

## Manual Control

In any Pi session with the extension loaded:

```
/lemonade status        — show current tier + endpoint health
/lemonade pin npu       — lock to NPU (gemma4-it:e2b, 2B)
/lemonade pin reason    — lock to REASON (DeepSeek-Qwen3-8B, chain-of-thought)
/lemonade pin igpu      — lock to iGPU (Qwen3.6-35B-A3B, default)
/lemonade pin cpu       — lock to CPU (Gemma-4-31B, 31B dense)
/lemonade auto          — resume automatic routing
/lemonade off           — disable router (Ctrl+P takes over)
```

Ctrl+P model cycling in Pi also works — selecting a Lemonade model from the picker pins that tier; selecting any non-Lemonade model disables the router.

---

## Files

| File | Purpose |
|------|---------|
| `~/.local/bin/lemonade-launch-pi` | Launch script (checks endpoints, starts FLM if needed, execs Pi) |
| `~/.pi/agent/models.json` | Provider + model registration (read at Pi startup) |
| `.pi/extensions/lemonade-router.ts` | Per-turn routing extension |

---

## Known Issues

### Reasoning model token budget
All Gemma 4 models are reasoning-mode models — they emit internal `<think>` tokens before visible content. Short `max_tokens` budgets (< 128) will produce empty visible output as the thinking block consumes the entire budget.
- The NPU model is configured with `maxTokens: 512` which is the reliable floor.
- The iGPU models use 2048–8192 depending on tier.

### FLM verbose logging
`flm serve` prints connection-level debug output to stdout. Redirect if noisy:
```bash
flm serve gemma4-it:e2b --port 13306 --quiet > /tmp/flm-npu.log 2>&1 &
```

### lemond pull for Gemma 4 E2B
`lemonade pull gemma4-it-e2b-FLM` fails with a websocket timeout while downloading the 4.4 GB `model.q4nx`. The model is already present in FLM's own cache (`~/.config/flm/models/Gemma4-E2B-IT-NPU2/`). Use `flm serve` directly instead of going through lemond for the NPU lane.

### pi-autoresearch extension stale context
An unrelated installed extension (`pi-autoresearch`) logs a stale-context error at session end in print mode. This is a bug in that extension, not the router. It does not affect routing behavior.
