# Strix Halo — Sustained Local Inference Tuning

**Hardware:** AMD Ryzen AI MAX+ 395 · gfx1151 (Radeon 8060S) · 128 GB LPDDR5X unified memory  
**Date:** 2026-05-02  
**Concern:** Multiple concurrent sessions hitting lemond :13307 + FLM :13306

---

## Current State (2026-05-02, post-optimization)

```
iGPU clocks:   high (2900 MHz) ← locked by amdgpu-perf.service  [WAS: auto / 894 MHz]
Backend:       Vulkan (lemond falls back from ROCm — gfx1151 VMM=no causes ROCm rejection)
GTT memory:    ~32 GB used / 128 GB total (2 routing models + opencode session)
lemond config: global_timeout=120s, max_loaded_models=4 [pending restart for Tier B flags]
vm.swappiness: 10 (was 60)
Temp (Tctl):   72–75°C under load   GPU edge: ~32°C
```

## Empirical Benchmarks (2026-05-02, iGPU locked at 2900 MHz, Vulkan backend)

All via llama-bench direct (not through lemond). **See safety note below.**

| Tier | Model | pp512 (t/s) | tg128 (t/s) | Wall (pp+tg) | Notes |
|------|-------|-------------|-------------|---------------|-------|
| REASON | DeepSeek-Qwen3-8B Q4_1 | **1046 ± 5** | **39.8 ± 0.2** | ~44s | |
| iGPU | Qwen3.6-35B-A3B Q4_K_M | **922 ± 25** | **63.6 ± 0.2** | ~29s | MoE, 3B active |
| NPU cold | gemma4-it:e2b (FLM) | — | **20.6 tok/s** | 1.64s total | TTFT 1.13s |
| NPU warm | gemma4-it:e2b (FLM) | — | **22.9 tok/s** | 1.61s total | TTFT 0.86s |
| CPU | Gemma-4-31B Q4_K_M | ~50 (est) | **~9.8** | 64s/621tok | via HTTP, includes thinking |

**Flash Attention on Vulkan:** tested, **do not use**. Results: 953 t/s → 1034 t/s first run, then 927 t/s second run (±14 variance vs ±5 without). Inconsistent — partial CPU fallback. Dropped from Tier B.

**FLM pmode modes available:** `default`, `powersaver`, `balanced`, `performance`, `turbo`. (`latency` is NOT valid — falls back to default silently.)
- `performance` warm TTFT: 0.860s, 22.9 tok/s
- `turbo` warm TTFT: 0.857s, 21.6 tok/s — negligible difference from performance

**Baseline reference (pre-iGPU-lock):** ~884 t/s pp512 on Vulkan per llm-tracker. Post-lock: 922–1046 t/s. iGPU clock lock delivered ~10–18% prompt throughput improvement.

### ⚠️ llama-bench Safety Rule

**Never run llama-bench directly against a model file while lemond has the same model loaded.**
lemond and llama-bench each allocate GTT independently. Running both simultaneously doubles the model's memory footprint:
- 31B model in lemond: ~20 GB GTT
- llama-bench loading same 31B: +20 GB GTT = 40 GB spike
- This exhausted both swap partitions (39 GB total) and caused repeated OOM risk

**Safe benchmarking approach:** use the lemond HTTP API — queries the already-loaded model without extra GTT allocation:
```bash
time curl -s http://127.0.0.1:13307/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"<ID>","messages":[{"role":"user","content":"..."}],"max_tokens":256}'
```

Or unload from lemond first, bench, reload.

---

## Tier A — Applied (no restart, no reboot)

### ✅ iGPU clock lock

Benchmark impact: **73.6 → 140.7 t/s** prompt processing on 35B MoE (sleepingrobots data).

```bash
# Applied live:
echo high > /sys/class/drm/card1/device/power_dpm_force_performance_level

# Persisted via systemd:
sudo systemctl status amdgpu-perf.service

# Revert if needed:
echo auto > /sys/class/drm/card1/device/power_dpm_force_performance_level
sudo systemctl disable amdgpu-perf.service
```

---

## Tier B — Written to daemon config, pending lemond restart

> Config path: `/var/lib/lemonade/.cache/lemonade/config.json` (daemon, runs as `lemonade` user)
> Restart window: when active opencode session ends (zombie PID 972120 clears → GTT drops ~20 GB)

### Daemon config state (written, not yet active)

```json
"llamacpp": {
  "args": "-b 512 -ub 256 --cache-type-k q8_0 --cache-type-v q8_0 -np 2",
  "backend": "vulkan"
},
"global_timeout": 120,
"max_loaded_models": 4
```

| Flag | Effect | Research verdict |
|------|--------|-----------------|
| `-b 512 -ub 256` | Batch/microbatch tuning — avoids Vulkan ubatch cliff on gfx1151 | ✅ Safe on Vulkan |
| `--cache-type-k q8_0 --cache-type-v q8_0` | Halves KV cache memory, negligible quality impact | ✅ Safe on Vulkan |
| `-np 2` | 2 parallel inference slots per model — concurrent multi-session | ✅ Safe |
| `-fa` | Flash Attention | ❌ **DROPPED** — inconsistent on Vulkan (1034→927 t/s between runs, CPU fallback) |
| `ROCBLAS_USE_HIPBLASLT=1` | GEMM speedup | ❌ **DROPPED** — no-op on Vulkan backend |

**Why not ROCm backend?** lemond config says `backend: rocm` but the running binary is always Vulkan.
gfx1151 reports `VMM: no` which causes lemond to fall back to Vulkan silently. The ROCm-preview binary
(b8935) is broken on this system — needs system `libhipblas.so.3` which isn't installed (ROCm 7.1.0
does not ship the hipblas package). ROCm stable binary (b1203) may work but self-identifies as `gfx1150`.

### To apply

```bash
# Pick a quiet window — kills all in-flight lemond sessions
sudo systemctl restart lemond
# Verify new flags took effect
lemonade status --port 13307
ps aux | grep llama-server  # should show -b 512 -ub 256 in args
```

### Branch B: ROCm with hipBLASLt (future evaluation)

If ROCm stable binary works, potential gain is significant:
- gfx1151 Tensile hipBLASLt files ARE bundled in lemond ROCm binary (b1203)
- Measured: rocBLAS without hipBLASLt ~5 TFLOPS → with: ~35 TFLOPS (7x GEMM)
- pp512 projection: ~765 t/s → potentially 2000+ t/s (vs current 922–1046 on Vulkan)
- Risk: `gfx1150` detection mismatch, known hang reports (lemonade issue #1149)

Test procedure: set `backend: rocm` in daemon config, restart, run one HTTP inference, check if
`ROCBLAS_USE_HIPBLASLT=1` takes effect without error. Abort if GTT spikes unexpectedly.

---

## Tier C — Requires reboot

### BIOS settings
| Setting | Value | Effect |
|---------|-------|--------|
| UMA Frame Buffer | 512 MB | Minimizes reserved display VRAM — leaves max GTT for models |
| IOMMU | Disabled | ~6% memory read improvement for GPU workloads |
| TDP | 85 W | Optimal performance/efficiency for sustained inference |

> Check current UMA: `cat /sys/class/drm/card1/device/mem_info_vram_total` already shows 0.5 GB — BIOS may already be at 512 MB.

### Kernel parameter

Add to `/etc/default/grub`:
```
amdgpu.gttsize=117760
```
Then `sudo update-grub`. Ensures kernel allocates ~115 GB GTT for models even if firmware defaults lower.

> Current GTT total already shows 128 GB, so this may be a no-op. Verify after reboot.

---

## Tier D — Multi-session Architecture

### The core contention model

```
Session A ──→ lemond :13307 ──→ llamacpp (ROCm) ──→ iGPU
Session B ──→ lemond :13307 ──→ queued (serialized per model)
Session C ──→ FLM    :13306 ──→ NPU (independent lane)
```

Lemond serializes requests to a loaded model. Concurrent sessions to the SAME model queue. Concurrent sessions to DIFFERENT models would require model switching (slow: 5–20s load).

**With 4 hot models (current):**
- NPU: `gemma4-it:e2b` — ack/one-liners — runs **independently** of iGPU
- REASON: `DeepSeek-Qwen3-8B` — stays resident, 8B so fast
- iGPU: `user.Qwen3.6-35B-A3B` — primary bottleneck; sessions queue here
- CPU: `Gemma-4-31B` — loaded but rarely used; available when iGPU busy

**The NPU is the free parallelism lane.** Running short tasks on NPU while iGPU serves a coding session costs only a 5.8% decode penalty (FLM data). The router already exploits this.

### For heavier multi-session scenarios

Consider adding **llama-swap** as a session-aware queue in front of lemond:

```
sessions → LiteLLM :4000 → llama-swap :8080 → lemond :13307
                                              → FLM    :13306
```

llama-swap prioritizes loading hot models, queues requests, and routes by model-ID prefix. Not needed until you have 3+ simultaneous heavy sessions.

---

## NPU Tuning (FLM)

```bash
# Valid --pmode values: default | powersaver | balanced | performance | turbo
# NOTE: 'latency' is NOT valid — FLM rejects it, silently falls back to default

# Empirical results (2026-05-02, Strix Halo, gemma4-it:e2b warm cache):
#   performance → TTFT 0.860s, decode 22.9 tok/s  ← recommended
#   turbo       → TTFT 0.857s, decode 21.6 tok/s  (negligible difference)

flm serve gemma4-it:e2b --port 13306 --quiet --pmode performance

# FLM v0.9.40 available (v0.9.39 installed):
# v0.9.40 adds: gemma4-it:e4b NPU support, chunk prefill for long prompts
# Update: download flm-setup from github.com/FastFlowLM/FastFlowLM/releases/latest
```

NPU cold-start: ~5s to port-ready, TTFT ~1.13s first request (XDNA cache load).  
NPU warm: **TTFT 0.86s, 22.9 tok/s decode** — runs independently of iGPU with zero contention.  
Ack-turn wall clock: **1.6s total** (including HTTP overhead).

---

## CPU Inference (lemond fallback)

For Gemma-4-31B on CPU-heavy paths:

```bash
# Enable AMX (Intel Advanced Matrix Extensions) — N/A on AMD
# AMD uses AVX-512 + AMX-equivalent via "Extended ALU" in Zen 5 cores

# lemond llamacpp CPU threads (add to llamacpp.args):
-t 16      # Use all 16 physical cores (32 logical)
```

Zen 5 has AVX-512 with native BF16 support. llama.cpp's llamafile backend uses this automatically via GGML_CPU_ALL_MATH_VEC. No explicit flags needed beyond `-t 16`.

---

## Memory Budget (128 GB unified pool)

| Consumer | Current | Notes |
|----------|---------|-------|
| OS + processes | ~68 GB | High — other sessions, browser, etc. |
| Loaded model weights (GTT) | ~39 GB | 4 LLMs, Nemotron, etc. |
| KV cache (per session) | 1–4 GB each | Grows with context length |
| Swap used | 34 GB | Warning: indicates memory pressure |

**Safe headroom for new models:** ~14 GB free. One 9 GB model (Granite-4.1-8B) fits.  
**Do not pull:** Qwen3-Coder-30B-A3B (17 GB) — would OOM under multi-session load.

### To reduce swap pressure:
```bash
# Close unused browser tabs / non-essential processes
# Or increase swap-happiness threshold:
sudo sysctl vm.swappiness=10   # default 60 — reduce swap aggression
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.d/99-inference.conf
```

---

## Quick Reference: Optimization Commands

```bash
# Check iGPU clock and performance mode
cat /sys/class/drm/card1/device/power_dpm_force_performance_level
cat /sys/class/drm/card1/device/pp_dpm_sclk

# Check GTT allocation (model memory)
cat /sys/class/drm/card1/device/mem_info_gtt_used
cat /sys/class/drm/card1/device/mem_info_gtt_total

# Lemond loaded models
lemonade status --port 13307

# FLM NPU status  
curl -s http://localhost:13306/v1/models | python3 -m json.tool

# Thermals
sensors | grep -E "Tctl|edge|PPT|fan"

# Swap pressure
free -h && swapon --show
```
