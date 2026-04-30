# Local Environment Quirks — Strix Halo Living Document

Per the **Cohezion Architecture Manifest** Phase 1 directive: this file is the running memory of **AMD Ryzen AI MAX+ 395 / Strix Halo** specifics discovered during live session work. Hardware quirks, driver overrides, port assignments, recovery protocols, and the "you only have to burn this once" knowledge.

Refresh cadence: **append, don't rewrite**. Every entry is dated and cites its discovery source.

---

## 2026-04-18 — Current verified state

### Silicon inventory

| Component | Identity | Verified via |
|-----------|----------|--------------|
| CPU | AMD Ryzen AI MAX+ 395 (Zen 5, 16C/32T, AVX-512, AVX-VNNI, AMX) | `/proc/cpuinfo` |
| iGPU | Radeon 8060S, `gfx1151`, Wave Size 32, 131 072 MiB VRAM | llama-server startup log |
| NPU | XDNA 2 (8 columns) | `/dev/accel/accel0` present |
| RAM | 128 GB LPDDR5X unified memory | — |
| GTT pool | 120 GB (configured via kernel parameter — see below) | `TURBOQUANT_UNLOCK_REPORT.md` session 94 |
| Storage | 2 TB NVMe + 32 GB swap (ZFS) | — |

### Mandatory environment variables

Set in shell rc (or sourced via `scripts/symphony_warmstart.sh`):

```bash
export HSA_OVERRIDE_GFX_VERSION=11.5.1   # gfx1151 hardware identity
export TRITON_AMD_WMMA=1                 # ROCWMMA backend for Triton
export HSA_XNACK=1                       # transparent page faults for unified memory
```

`HSA_OVERRIDE_GFX_VERSION=11.5.1` (note the `.1`, not `.0` as some older guides say). The `.0` version is insufficient for the current ROCm 7.2.1 wheel set.

### Kernel parameters (120 GB GTT pool)

For the iGPU to address the full 120 GB of unified memory, set the TTM pool size. This is applied via `sudo ./scripts/setup-strix-halo.sh` inside `scripts/symphony_warmstart.sh`:

```
ttm.pages_limit=31457280      # 120 GB in 4 KB pages
ttm.page_pool_size=31457280
```

Persists across reboot via `/etc/default/grub` GRUB_CMDLINE_LINUX or equivalent.

### Lemonade Server lane bindings

| Lane | Port | Backend | Model (verified loaded) |
|------|------|---------|-------------------------|
| NPU (XDNA 2) | `:13306` | `lemonade --llamacpp flm` | `Gemma-4-E2B-it-GGUF` |
| iGPU ROCWMMA | `:13307` | `lemonade --llamacpp rocm -fa 1 -ngl 99` | `Gemma-4-E4B-it-GGUF` |
| iGPU Unified | `:13308` | `lemonade --llamacpp rocm -fa 1 -ngl 99` | `Gemma-4-26B-A4B-it-GGUF` (MoE, 4B active) |
| CPU AVX-VNNI | `:13309` | `lemonade --llamacpp cpu --ctx-size 32768` | `Gemma-4-31B-it-GGUF` |

**Source of truth:** `scripts/launch_gemma4_symphony.sh`. Do not hard-code ports elsewhere; read from `src/cohezion/inference/registry.py`.

### Ollama

- Port `:11434` serves 14+ models as of 2026-04-18: `phi4:latest`, plus cloud proxies (`deepseek-v3.2:cloud`, `gemini-3-flash-preview:cloud`, `glm-5.1:cloud`).
- **4-model concurrent limit.** Exceeding triggers unpredictable eviction. See `CLAUDE.md` for the `DynamicModelRouter` admission logic.

---

## Known Binary Hard-Lock — PyTorch ROCm wheels lack gfx1151 ISA

**Source:** `TURBOQUANT_UNLOCK_REPORT.md` session 94, 2026-04-16.

Standard PyTorch ROCm wheels (6.2.4 and 7.2.1) do **not** contain valid ISA for `gfx1151`. Setting `HSA_OVERRIDE_GFX_VERSION=11.5.1` does **not** fix this — overrides cannot synthesize missing ISA in a pre-compiled binary.

**Symptom:** `Invalid Device Function` or `Memory access fault by GPU node-1 ... address 0x7a39d6506000` on the first Triton kernel dispatch.

**Resolution:**
1. For TurboQuant specifically: favor the **NPU path (FLM backend)** — it bypasses the wheel problem entirely.
2. For iGPU inference: use **direct llama.cpp HIP build** (`GGML_HIP=1 AMDGPU_TARGETS=gfx1151 make` from source), not PyTorch-dependent stacks.
3. For custom Triton kernels: `AMD_SERIALIZE_KERNEL=3` to bypass a race condition in the current Triton dispatch path on gfx1151.

**What NOT to do:** uninstall/reinstall PyTorch ROCm hoping for a fix — the missing ISA is upstream. Track `lemonade-sdk/lemonade#826` for the community fix.

---

## Aperture Contention — Cold-boot-only recovery

**Source:** `STRIX_HALO_SYMPHONY_GUIDE.md` recovery protocol.

The Strix Halo iGPU aperture (64 – 128 GB) is sensitive to **concurrent JIT compilation**. Loading multiple ROCWMMA models simultaneously triggers `GCVM_L2_PROTECTION_FAULT`, leading to **Zombie VRAM Allocation** (90%+ reported usage with no active process visible in `rocm-smi`).

**Recovery is cold-boot only.** Soft-reset (reboot, kernel restart) does not clear the zombie state. Physical power-off is required to reset kernel page tables for the aperture.

**Mitigation — sequential staged iGPU load:**

1. Start NPU (`:13306`) first.
2. Confirm NPU throughput > 100 TPS before loading any iGPU model.
3. Load one iGPU model at a time — verify `:13307` responds before starting `:13308`.
4. Never launch `launch_gemma4_symphony.sh` twice in a row without a clean shutdown between runs.

Scripts that respect this sequence: `scripts/symphony_warmstart.sh` (uses `pkill -9 -f "llama-server|lemonade|ollama"` + 2 s sleep before relaunch).

---

## Omnibus gateway side effect

`Omnibus().__init__()` logs `"🌟 Omnibus resurrected - Master Gateway Controller ready (Resilient)"` and opens an MCP connection attempt. If the MCP server (`:8360` in current config) is down, the constructor logs a 500 but does not fail — there's a local JSONL fallback at `~/.cohezion/gateways.jsonl`.

**Quirk:** any import of `cohezion.gateways.omnibus` triggers Omnibus init. Our `cohezion.inference.health.check_fleet()` calls this on every invocation (via `_omnibus_dashboard()`) but only for the dashboard string — consider caching this separately if health probe latency becomes a concern.

---

## Recovery runbook

When the fleet is behaving oddly:

```bash
# 1. Surgical teardown (don't reboot yet)
pkill -9 -f "llama-server|lemonade|ollama"
sleep 2

# 2. Verify env vars
echo "HSA=$HSA_OVERRIDE_GFX_VERSION TRITON=$TRITON_AMD_WMMA XNACK=$HSA_XNACK"
# Expect: HSA=11.5.1 TRITON=1 XNACK=1

# 3. Verify device nodes
ls /dev/accel/accel0 /sys/class/drm/card1/device/vendor

# 4. Warmstart (restores GTT + drivers + models)
bash scripts/symphony_warmstart.sh

# 5. Probe
uv run python -c "from cohezion.inference import check_fleet, format_fleet_summary; print(format_fleet_summary(check_fleet(force=True)))"

# 6. If iGPU shows zombie VRAM: cold boot. No soft recovery exists.
```

---

## Append new quirks below this line

*(Add timestamped entries as new gotchas are discovered. Do not edit historical entries — append-only log.)*

---

### 2026-04-18 — Reasoning-mode token budget (Gemma 4 FLM)

Gemma-4-E2B-it-GGUF and other Gemma 4 variants served via Lemonade FLM backend are **reasoning-mode models** — every response emits `delta.reasoning_content` chunks (internal "thinking") before any `delta.content` (visible answer).

**Empirical budget requirement:**
- `max_tokens = 16`   → 100% reasoning, 0 visible tokens, `finish_reason="length"`
- `max_tokens = 64`   → mostly reasoning, intermittent visible content
- `max_tokens = 256`  → finish_reason flips stochastically between "stop" and "length"
- `max_tokens = 512`  → reliable finish, visible content present
- `max_tokens = 1024` → safe floor for one-word answers

**Impact on orchestration:**
- `cohezion.inference.route(stream=True, max_tokens=16)` is good for **TTFT measurement only** — first reasoning chunk arrives in ~80ms, `ttft_ms` populated, but `text` may be empty.
- `cohezion.inference.route(stream=False, max_tokens=1024)` gives reliable visible content at the cost of ~2-4s total latency (generation time dominated by reasoning phase).
- For the `TieredOrchestrator` quality gates, `min_chars` must be evaluated against **visible content only** — which is what `QualityGate.check()` does (empty `text` fails the gate).

**If the visible content is empty:** not necessarily a dispatch bug — check `usage.completion_tokens` against your `max_tokens`. If they're equal with `finish_reason="length"`, the model used all budget on reasoning. Bump `max_tokens`.

**Alternative (not yet implemented):** extend `_dispatch_openai_compatible` to fall back to `reasoning_content` when `content` is empty AND `finish_reason == "length"`. This would surface *something* to the user at the cost of exposing the model's chain-of-thought. Keep as opt-in flag, default off.

---

### 2026-04-29 — Eigent + Lemonade: max_loaded_models OOM crash

**Source:** Live crash during Eigent local inference setup.

**Symptom:** System crash / forced reboot when running Eigent agents (browser, developer, document, multi-modal) against Lemonade on port 13307.

**Root cause:** `max_loaded_models: 4` (the old default in `~/.cache/lemonade/config.json`) allowed all 4+ Eigent agents to trigger simultaneous model loads on the iGPU. This hit the documented **Aperture Contention** bug (see above section) — multiple concurrent ROCWMMA JIT compilations on gfx1151 → GCVM_L2_PROTECTION_FAULT → kernel crash.

**Fix applied:** `max_loaded_models: 1` in `~/.cache/lemonade/config.json`. Requires `sudo systemctl restart lemond` to take effect.

**Safe model for Eigent:** `Qwen3-8B-GGUF` — tool calls confirmed (`finish_reason: "tool_calls"`), ~42 tok/s on iGPU.

**Eigent UI settings** (Settings → Model):
```
Model Platform: openai-compatible-model
Model Type:     Qwen3-8B-GGUF
API Key:        lemonade
API URL:        http://localhost:13307/v1
```

**Why `max_loaded_models: 1` is safe for Eigent:** Lemonade queues concurrent *inference* requests within a single loaded model. Multiple agents all hitting the same model is fine. The danger is only concurrent *model loading events*, which `max_loaded_models: 1` prevents.

**Full setup doc:** `~/dev/cohezion/data/eigent/EIGENT_LOCAL_SETUP.md`

---

### 2026-04-29 — max_loaded_models=2 is safe with sequential pre-loading

**Discovery:** `max_loaded_models` accepts `-1` (unlimited) or any positive integer. Setting it to `2` is safe on Strix Halo provided the TWO models are loaded SEQUENTIALLY (not concurrently).

**Why the original crash happened:** `max_loaded_models=4` + Eigent spawning 4+ agents simultaneously triggered 4 concurrent model loading events (JIT compilations) → aperture contention → GCVM_L2_PROTECTION_FAULT.

**Why `max_loaded_models=2` with sequential pre-loading is safe:**
- Qwen3-8B uses **Vulkan** backend (RADV driver, different aperture code path)
- Gemma-4-26B uses **ROCm** backend (default config)
- Pre-loading one at a time (wait for each to serve before loading next) = zero concurrent JIT
- Once both are loaded, concurrent *inference* across both is safe (proven: 5 concurrent requests, stable)
- Memory usage: 5 GB + 17 GB = 22 GB / 120 GB GTT pool (18%)

**Config:** `max_loaded_models: 2` in `~/.cache/lemonade/config.json`

**Startup script:** `~/.local/bin/lemonade-preload` — run after `sudo systemctl restart lemond`

**Eigent agent routing (updated 2026-04-29):**
- `EIGENT_LOCAL_MODEL_TYPE=Gemma-4-26B-A4B-it-GGUF` → ALL agents (Qwen3-8B removed; it's a reasoning model that burns all tokens on `<think>` blocks → empty tool call → CAMEL NoneType crash)
- `EIGENT_LOCAL_BROWSER_MODEL_TYPE=Gemma-4-26B-A4B-it-GGUF` → browser agent (same model, vision + tool calls verified)
- Both served on `http://localhost:13307/v1` — same URL, different `model` parameter

---

### 2026-04-29 — lemond Vulkan backend hardcodes ctx-size 4096 (cannot override)

**Source:** Empirical investigation during Eigent htop high-usage session.

lemond's Vulkan-backend llama-server invocation hardcodes `--ctx-size 4096` regardless of:
- `ctx_size: 16384` in `~/.cache/lemonade/config.json` (stored but not forwarded to llama-server)
- `lemonade load --ctx-size 16384` (CLI accepts it, management API ignores it, models still start at 4096)
- `LEMONADE_CTX_SIZE=16384` in `/etc/lemonade/conf.d/zz-ctx-size.conf` (env var not used by lemond auto-loader)
- `llamacpp.args: "--ctx-size 16384"` in config.json (lemond strips `--ctx-size` when building llama-server args; only unrecognized flags like `--no-mmap` pass through)
- `lemonade load --llamacpp-args "--ctx-size 16384"` (management API returns HTTP 500 for `llamacpp-args` parameter)

**Mitigation:** `--context-shift` IS enabled in all invocations, so conversations longer than 4096 tokens slide the window gracefully. Adequate for Eigent's agent task patterns. May cause subtle quality degradation on very long multi-turn agent conversations (early context evicted). No crash.

**What htop showed high:** The real culprit was `max_loaded_models: 4` (old default) — Eigent spawning 4+ agents loaded 4 models simultaneously (Qwen3-8B=6.2GB + Gemma-4-26B + Qwen3-14B + rogue Gemma-4-26B from worktree) → 89GB used. Fix: `max_loaded_models: 2` + `sudo systemctl restart lemond` + `lemonade-preload`. Result: 75GB used (−14GB).
