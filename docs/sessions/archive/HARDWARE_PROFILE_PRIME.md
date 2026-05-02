---
name: hardware-profile
version: 1.0
last_updated: 2026-04-18
owner: cohezion.inference
status: TRUTH_ANCHOR
---

# Strix Halo Hardware Profile (PRIME)

**Referenced by:** `CLAUDE.md`, `src/cohezion/inference/registry.py`,
`src/cohezion/core/symmetry_hardware_bridge.py`, `SHOWCASE.md`,
`MANIFEST_ALIGNMENT.md`.

**Role:** Single source of truth for what compute the Cohezion platform runs
on. Every quantization, kernel, driver, and memory assumption in the inference
stack must trace back to a line in this document. If reality drifts from this
profile, update the profile first, then the code.

---

## 1. Silicon (AMD Ryzen AI MAX+ 395 "Strix Halo")

| Component | Value | Notes |
|---|---|---|
| CPU | 16x Zen 5, 32 threads | AVX-512 + VNNI + AMX |
| iGPU | Radeon 8060S, 40 CUs, RDNA 3.5 | LLVM target `gfx1151` (alias `gfx1150` in older toolchains) |
| NPU | XDNA 2, 50 TOPS | INT4 / INT8 / BF16 native |
| Memory | 128 GB LPDDR5X, 256 GB/s | **Unified** — no VRAM split at the hardware level |
| Storage | 2 TB NVMe + 32 GB swap (ZFS) | Gen5 PCIe if BIOS is set correctly |
| Platform | Framework Desktop, BIOS v3.05+ | UMA Frame Buffer must be `Auto` on kernel 6.18.4 |

**Assertion:** If `rocminfo | grep gfx1151` returns nothing, the rest of this
document does not apply — you are on a different machine.

---

## 2. Host stack baseline (April 18, 2026)

| Layer | Pinned version | Reason |
|---|---|---|
| Kernel | **6.18.4** (ppa:cappelikan Mainline) | First kernel that dynamically scales UMA up to ~112 GB on Auto |
| AMDGPU firmware | Latest `strix_halo*` blobs from `kernel.org/linux-firmware` | Required for NPU + iGPU memory controller on 6.18.4 |
| ROCm | **7.2.2** | First release with stable TurboQuant (TBQ) kernels on RDNA 3.5 per Apr 18 PDF |
| Ryzen AI Software | **1.7.1** (hotfix Apr 8, 2026) | INT4 native, MoE BF16 improvements; no TBQ NPU operator yet |
| AMD Quark | **0.10** | QuaRot weight-rotation quantization (prior art to TurboQuant) |
| vLLM-rocm | Nightly wheels (`--extra-index-url https://download.pytorch.org/whl/nightly/rocm7.2`) | Carries TBQ kernels |

---

## 3. BIOS settings (Framework Desktop v3.05+)

Required for full unified-memory utilization and peak bandwidth:

1. **UMA Frame Buffer:** `Auto` — lets kernel 6.18.4 dynamically scale allocation to ~112 GB.
2. **AI Max Performance Mode:** `Enabled` — prioritizes memory bandwidth for the iGPU.
3. **PCIe Speed:** `Gen5` — matters if SurrealDB or model weights live on external NVMe.

Values actually in effect (update after every BIOS change):

| Setting | Value | Verified on |
|---|---|---|
| UMA Frame Buffer | _unknown_ | _not yet verified_ |
| AI Max Performance Mode | _unknown_ | _not yet verified_ |
| PCIe Speed | _unknown_ | _not yet verified_ |

---

## 4. Environment pin (`~/.cohezion/strix_halo.env`)

All launcher scripts (`scripts/launch_vllm_lane.sh`,
`scripts/launch_llamacpp_lane.sh`, etc.) source this file first.

```bash
export HSA_OVERRIDE_GFX_VERSION=11.5.0   # 11.5.0 per Apr 17 PDF, NOT 11.5.1
export HIP_VISIBLE_DEVICES=0
export GPU_MAX_WORKGROUP_SIZE=1024
export AMDGPU_TARGETS=gfx1151
export ROCM_PATH=/opt/rocm
export PATH="/opt/rocm/bin:$PATH"
```

---

## 5. Inference lane layout

| Lane | Port | Model | Weight quant | KV quant | Runtime backend |
|---|---|---|---|---|---|
| NPU XDNA2 | 13306 | Gemma-4-E2B-it-GGUF | INT4 (future: QUAROT_INT4) | none — AMD compiler has no TBQ op | FLM (Ryzen AI 1.7.1) |
| iGPU ROCWMMA | 13307 | Gemma-4-E4B-it-GGUF | Q4_K_M | TurboQuant 3.5-bit (`--kv-cache-type turbo3`) | llama.cpp PR #20969 |
| iGPU Unified | 13308 | Gemma-4-26B-A4B-it-GGUF (or Llama-3.5-70B) | MXFP4 / Q4_K_M | TurboQuant 4-bit (`--kv-cache-dtype tbq4`) | vLLM-rocm (ROCm 7.2.2) |
| CPU AVX-VNNI | 13309 | Gemma-4-31B-it-GGUF | Q4_K_M | none — no AVX-512 TBQ kernels exist | llama.cpp CPU backend |

**NPU KV-TurboQuant gap:** AMD's Ryzen AI compiler has no TBQ operator as of
1.7.1. Revisit when Ryzen AI 1.8 ships (est. Q3 2026). Until then, NPU KV
stays FP16; weight-side rotation (QuaRot via Quark 0.10) is the nearest
family member and is applied offline in `scripts/quark_quarot_gemma4_e2b.py`.

**CPU KV-TurboQuant gap:** No public AVX-512 kernels for Hadamard-rotate +
Lloyd-Max as of April 2026. CPU lane stays Q4_K_M weight-only. Research
project; not scoped for this cycle.

---

## 6. Fallback escape hatch — Vulkan RADV

If ROCm 7.2.2 regresses on gfx1151 (the community pre-7.2 benchmarks reported
a >64GB VRAM load bug per ROCm#6146), stock `llama.cpp` + Vulkan RADV runs
on the same ports but with **`KVQuant(scheme="none")`** — no TurboQuant.

Measured pre-7.2 baseline: **36.80 tokens/sec** (Vulkan RADV) vs **~36 t/s**
(ROCm 6.4.4 with hipBLASLt, unstable above 64 GB VRAM load).

Whether to use this fallback is decided empirically in
`scripts/probe_backend.py` (Phase 0b). The outcome lives at
`benchmarks/backend_probe_2026-04-18.md` after the probe runs.

---

## 7. Verification commands

Non-destructive probes a fresh session can run to confirm this profile still holds:

```bash
uname -r                          # must print 6.18.4 or later
rocminfo | grep gfx1151           # must show the device
dmesg | grep -i strix_halo        # firmware must be loaded
rocm-smi --showmeminfo vram       # must report ≥ ~108 GB on Auto UMA
lscpu | grep -E 'avx512|vnni|amx' # must show all three CPU features
```

---

## 8. Change log

| Date | Change | By |
|---|---|---|
| 2026-04-18 | Initial profile. Plan ref: `.claude/plans/dreamy-jingling-thacker.md`. | Phase 0 |
