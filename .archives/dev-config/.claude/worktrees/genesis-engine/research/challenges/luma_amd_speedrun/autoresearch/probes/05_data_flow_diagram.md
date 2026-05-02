# AMD MI355X Kernel Data Flow: Python → Triton → CK ASM

## Overview

This document traces the execution path from Python API calls through to the final AMD CDNA 4 (gfx950) machine code. Understanding this flow is critical for identifying optimization opportunities and API ceilings.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PYTHON LAYER                                    │
│  submission.py → custom_kernel(data)                                        │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│  │   GEMM API   │     │  MLA API     │     │   MoE API    │               │
│  │ aiter.gemm_  │     │ mla_decode_  │     │ fused_moe()  │               │
│  │ a4w4_asm()   │     │ stage1_asm_  │     │              │               │
│  │              │     │ fwd()        │     │              │               │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘               │
└─────────┼──────────────────┼──────────────────┼─────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AITER PYTHON WRAPPER                               │
│  (aiter/ops/gemm.py)  (aiter/mla/mla_decode.py)  (aiter/fused_moe.py)       │
│                                                                              │
│  • Dispatch logic (fast_mode, splits, etc.)                                  │
│  • Auto-tuner lookup (tuned_fmoe.csv)                                       │
│  • Environment variable checks (AITER_KSPLIT, BYPASS_TUNE)                  │
│  • JIT compilation triggers                                                 │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ JIT COMPILATION (~25-260s per module)                                 │ │
│  │                                                                        │ │
│  │ moe_sorting:        ~25s  (token dispatch)                            │ │
│  │ ck2stages_fp4x2:  ~103s (MXFP4 GEMM kernels)                        │ │
│  │ cktile2stages:    ~132s (generic tile kernels)                        │ │
│  │ module_moe_asm:    ~31s (HSA assembly codegen)                        │ │
│  │                                                                        │ │
│  │ Output: .so files in /tmp/aiter_jit_cache/                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────┬──────────────────┬───────────────────────┘
                  │                  │                  │
                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TORCH/HIP DISPATCH LAYER                                  │
│  torch.ops.aiter.* → pybind11 → C++ kernels                                 │
│                                                                              │
│  • Tensor marshalling (dtype, stride, device)                               │
│  • Scale tensor handling (E8M0 format)                                      │
│  • Launch configuration (grid/block sizes)                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ DATA TYPE CONVERSIONS                                                  │ │
│  │                                                                        │ │
│  │ bf16/fp8 → fp4x2 packing: dynamic_mxfp4_quant()                       │ │
│  │ Scale shuffle: e8m0_shuffle() (layout [16,16] for weights)            │ │
│  │                                                                        │ │
│  │ MXFP4 format: fp4x2 (2 packed values/byte) + E8M0 scale (1 byte/32)   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────┬──────────────────┬───────────────────────┘
                  │                  │                  │
                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPOSABLE KERNEL (CK) LAYER                              │
│  (AMD Composable Kernel - C++ template library)                            │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ CK-Tile GEMM │  │ CK MLA       │  │ CK MoE       │                      │
│  │ (flatmm/)    │  │ (mla/)       │  │ (moe/)       │                      │
│  │              │  │              │  │              │                      │
│  │ Tile GEMM    │  │ Attention    │  │ 2-stage GEMM │                      │
│  │ with MXFP4   │  │ with KV      │  │ with routing │                      │
│  │ support      │  │ cache        │  │              │                      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                      │
│         │                 │                 │                               │
│         ▼                 ▼                 ▼                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ CK-TILE ABSTRACTION                                                    │ │
│  │                                                                        │ │
│  │ TileWindow:   Memory access pattern abstraction                       │ │
│  │ TilePipeline: Prefetch and compute overlap                            │ │
│  │ TileMFMA:     Matrix fused multiply-add                               │ │
│  │                                                                        │ │
│  │ Example: flatmm_tile_pipeline_mxfp4.hpp                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────┬──────────────────┬───────────────────────┘
                  │                  │                  │
                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HIP KERNEL LAYER                                   │
│  (Generated from CK templates or hand-written)                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ MFMA INSTRUCTIONS (CDNA 4 / gfx950)                                    │ │
│  │                                                                        │ │
│  │ mfma_f32_32x32x64_f8f6f4   - MXFP4 GEMM accumulation                 │ │
│  │ mfma_f32_32x32x16_fp16     - FP16 GEMM                                │ │
│  │ mfma_f32_32x32x8_bf16      - BF16 GEMM                                │ │
│  │                                                                        │ │
│  │ Tile: 32x32 output with 64-element K reduction                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ WAVE SYNCHRONIZATION                                                   │ │
│  │                                                                        │ │
│  │ __syncthreads() / __syncwarp()                                        │ │
│  │ DS_READ/DS_WRITE (LDS operations)                                     │ │
│  │ Buffer/Wavefront operations                                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────┬──────────────────┬───────────────────────┘
                  │                  │                  │
                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HSA/ASSEMBLY LAYER                                        │
│  (AMD Heterogeneous System Architecture)                                     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ PRE-COMPILED KERNELS (.co files)                                       │ │
│  │                                                                        │ │
│  │ /home/runner/aiter/hsa//gfx950/                                        │ │
│  │ ├── fmoe/silu/fmoe_bf16_pertokenMXfp4_g1u1_vs_silu_1tg_ps_32x512.co   │ │
│  │ ├── fmoe/silu/fmoe_bf16_pertokenMXfp4_g1u1_vs_silu_2tg_ps_32x256.co   │ │
│  │ └── mla/mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co                      │ │
│  │                                                                        │ │
│  │ Loaded at runtime via hipModuleLoad()                                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ASSEMBLY CODE GENERATION (module_moe_asm)                              │ │
│  │                                                                        │ │
│  │ Pandas-based ISA codegen (aiter/jit/hsa/codegen.py)                   │ │
│  │ Generates .s files → assembled to .co                                   │ │
│  │                                                                        │ │
│  │ Template substitution for tile sizes                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────┬──────────────────┬───────────────────────┘
                  │                  │                  │
                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GPU HARDWARE (MI355X)                                   │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │
│  │   XCD 0     │  │    ...      │  │   XCD 7     │                          │
│  │  38-40 CUs  │  │             │  │  38-40 CUs  │                          │
│  │             │  │             │  │             │                          │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │                          │
│  │ │ L2 Cache│ │  │ │ L2 Cache│ │  │ │ L2 Cache│ │                          │
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │                          │
│  │      │      │  │      │      │  │      │      │                          │
│  │ ┌────┴────┐ │  │ ┌────┴────┐ │  │ ┌────┴────┐ │                          │
│  │ │ MFMA    │ │  │ │ MFMA    │ │  │ │ MFMA    │ │                          │
│  │ │ Units   │ │  │ │ Units   │ │  │ │ Units   │ │                          │
│  │ │(per CU) │ │  │ │(per CU) │ │  │ │(per CU) │ │                          │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │                          │
│  └─────────────┘  └─────────────┘  └─────────────┘                          │
│         │                │                │                                  │
│         └────────────────┴────────────────┘                                  │
│                          │                                                  │
│                   ┌──────┴──────┐                                          │
│                   │  HBM3 Memory │                                          │
│                   │  (1.5 TB/s) │                                          │
│                   └─────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Bottlenecks by Layer

### Python Layer (~20-50µs)

| Bottleneck | Cost | Mitigation |
|------------|------|------------|
| Dynamic quantization | 26-84µs | Fuse into kernel (blocked) |
| Python dispatch per op | 20-25µs | Direct ASM dispatch |
| Torch op overhead | 5-15µs | Use torch.matmul for small shapes |

### JIT Compilation Layer (~128-260s one-time)

| Module | Build Time | Cacheable |
|--------|-----------|-----------|
| moe_sorting | ~25s | No (ephemeral runner) |
| ck2stages_fp4x2 | ~103s | No (ephemeral runner) |
| cktile2stages | ~132s | No (ephemeral runner) |

**Mitigation:** `AITER_JIT_DIR=/tmp/aiter_jit_cache` (unverified on runners)

### CK/ASM Layer (~7-150µs)

| Kernel | Typical | Bottleneck |
|--------|---------|------------|
| GEMM | 7-10µs | Memory bandwidth (quant) |
| MLA | 40-290µs | Python dispatch, KV cache bandwidth |
| MoE | 90-350µs | Sorting, 2-stage pipeline |

---

## Data Format Transformations

### MXFP4 Packing Flow

```
bf16 tensor: [M, K]  float16 values
       │
       ▼
dynamic_mxfp4_quant()
       │
       ├── fp4_data: [M, K//2] uint8 (2 values per byte)
       │   - E2M1 format: 1 sign + 2 exp + 1 mantissa = 4 bits
       │   - Packed: 2 values in 1 byte
       │
       └── scale: [M, K//32] e8m0
               - E8M0: 8-bit exponent-only (power of 2)
               - One scale per 32 values

For weights only:
       │
       ▼
shuffle_weight(layout=(16, 16))
       │
       └── Reorder for L2 cache coherency
```

### E8M0 Scale Format

```c
// E8M0 (exponent-only, 8-bit)
// Represents: 2^(value - 127)
// No mantissa bits, just power-of-2 scaling

// Example:
// scale_byte = 129
// scale_factor = 2^(129 - 127) = 2^2 = 4.0

// In kernel:
// dequantized = fp4_value * e8m0_to_float(scale)
```

---

## Control Flow: MoE Example

```python
# 1. Python API
def custom_kernel(data):
    output = aiter.fused_moe(hidden, w1, w2, topk_ids, ...)
    return output

# 2. Aiter wrapper (fused_moe.py)
def fused_moe(...):
    # 2.1 Check environment variables
    ks = os.environ.get("AITER_KSPLIT", "0")
    bypass = os.environ.get("AITER_BYPASS_TUNE_CONFIG", "0")

    # 2.2 Lookup tuned config
    cfg = _get_tuned_config(...)  # May be blocked by CSV

    # 2.3 Decide kernel path
    if cfg and not bypass:
        # CSV-tuned path (deterministic kernel)
        return _ck_2stage(..., kernelName=cfg.kernelName)
    else:
        # Heuristic path (AITER_KSPLIT applies)
        if int(ks) > 0:
            return _cktile_2stage(..., split_k=int(ks))
        else:
            return _ck_2stage(..., kernelName="")

# 3. CK dispatch
# _ck_2stage() → ck_moe_stage1() + ck_moe_stage2()
# _cktile_2stage() → cktile_moe_gemm1() + cktile_moe_gemm2()

# 4. Kernel execution
# Each stage is a separate kernel launch:
# - Stage 1: Gate+Up GEMM + SiLU (in-kernel or separate)
# - Stage 2: Down GEMM + weight accumulation

# 5. Data movement
# HBM → LDS (load weights, activations)
# LDS → Registers (MFMA compute)
# Registers → LDS (SiLU, Mul)
# LDS → HBM (write output)
```

---

## Optimization Opportunities in Flow

### Current State vs Ideal

| Layer | Current | Ideal | Gap |
|-------|---------|-------|-----|
| Python | 3-5 dispatch ops | 1 dispatch | 60-100µs |
| JIT | 128-260s first call | 0s (pre-compiled) | All JIT time |
| CK | 2-stage kernels | Fused 1-stage | 30-50µs |
| ASM | Generic tiles | Shape-specific | 10-20% |

### Research-Driven Paths

1. **HipKittens:** Replace CK entirely with tile-based DSL
2. **CK-Tile Custom:** Extend flatmm for MoE 2-stage fusion
3. **ASM Injection:** Shape-specific pre-compiled kernels

---

## References

- aiter source: `python3 -c "import aiter; print(aiter.__path__)"`
- CK-Tile examples: composable_kernel/example/ck_tile/
- CDNA 4 ISA: AMD Instinct MI300/MI355X instruction set architecture
- HipKittens: github.com/HazyResearch/HipKittens

---

*Document created: 2026-03-27*
*Status: Reference for kernel development*
