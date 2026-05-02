# Strix Halo — Sustained Local Inference Tuning

**Hardware:** AMD Ryzen AI MAX+ 395 · gfx1151 (Radeon 8060S) · 128 GB LPDDR5X unified memory  
**Date:** 2026-05-02  
**Concern:** Multiple concurrent sessions hitting lemond :13307 + FLM :13306

---

## Current State

```
iGPU clocks:   high (2900 MHz) ← locked by amdgpu-perf.service  [WAS: auto / 894 MHz]
GTT memory:    39.4 GB used / 128 GB total
Models loaded: 4 LLMs (lemond Max Models/Type: 4)
RAM:           108 GB used / 122 GB · 14 GB free · 34 GB swap used
Temp (Tctl):   ~75°C under load   GPU edge: ~36°C
PPT:           56 W (avg)
```

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

## Tier B — Requires lemond restart (kicks in-flight sessions)

> Coordinate: warn other sessions, pick a low-traffic window.

### 1. llamacpp inference flags

Edit `~/.cache/lemonade/config.json`:

```json
"llamacpp": {
  "args": "--no-mmap -fa -b 512 -ub 256 --cache-type-k q8_0 --cache-type-v q8_0",
  "backend": "rocm"
}
```

| Flag | Effect |
|------|--------|
| `--no-mmap` | Already set. Critical for unified memory — avoids mmap overhead |
| `-fa` | Flash Attention — faster long-context (>2K), less memory for KV cache |
| `-b 512 -ub 256` | Batch/microbatch tuning. Avoids Vulkan ubatch cliff on gfx1151 |
| `--cache-type-k q8_0 --cache-type-v q8_0` | Halves KV cache memory — negligible quality impact |

**Expected improvement:** 20–40% throughput on long sessions; KV cache ~2× smaller = more context without OOM.

### 2. hipBLASLt environment

Add to `/etc/systemd/system/lemond.service` (or lemond's env file):

```
ROCBLAS_USE_HIPBLASLT=1
```

Provides **2–3× speedup** in GEMM operations on gfx1151. Requires `hipblaslt` package:

```bash
sudo apt install hipblaslt  # or: rocm-hipblaslt
rocblas-bench -f gemm_ex -m 1024 -n 1024 -k 1024 \
  --a_type f16_r --b_type f16_r --d_type f16_r --compute_type f16_r | grep -i "BLASLT"
```

### 3. Context size per model

Global `ctx_size: 16384` in lemond config. Qwen3.6-35B-A3B supports 131072. To unlock:
- Either override per-model in lemond (if supported) 
- Or set global `ctx_size: 32768` — doubles effective context for all LLMs

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
# Already applied in lemonade-launch-pi:
flm serve gemma4-it:e2b --port 13306 --quiet --pmode performance

# FLM performance modes:
# --pmode balanced    (default) — lower power, lower throughput
# --pmode performance            — full XDNA 2 clocks, ~15.5 tok/s decode (warm cache)
# --pmode latency               — minimize TTFT (good for interactive ack turns)
```

NPU cold-load: ~10s. XDNA 2 model cache (warm): TTFT ~1.6s, 15.5 tok/s.  
NPU is independent of iGPU — runs concurrently with zero iGPU impact.

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
