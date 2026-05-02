# HipKittens Environment Setup Status

**Date:** 2026-03-27
**Status:** Partial Setup Complete

---

## What Was Accomplished

### 1. Repository Cloned
```
/tmp/HipKittens/
├── analysis/          # Performance analysis scripts
├── kernels/           # Kernel implementations
│   ├── attn/         # Attention kernels
│   ├── gemm/         # GEMM kernels (bf16fp32, fp8fp32)
│   ├── layernorm/    # LayerNorm kernels
│   └── rotary/       # RoPE kernels
├── include/          # Header files (C++ template library)
├── tests/            # Unit tests
└── docs/             # Documentation
```

### 2. Virtual Environment Created
```bash
/tmp/hipkittens-rocm-env/  # Python 3.14 venv
├── torch 2.11.0+cpu       # CPU-only PyTorch installed
└── pip packages           # Ready for HipKittens build
```

### 3. Critical Discovery: HipKittens is C++ Header Library

**HipKittens is NOT a Python library.** It is a C++ header-only library that requires:
- ROCm compiler (`hipcc`)
- AMD GPU access for execution
- Compilation to `.so` or executable

### 4. Major Finding: HipKittens Now in AITER

From README (line 27):
> "[March 2026] HipKittens is officially an AITER backend! The first HK kernels have landed in AITER"

**This changes strategy:** Instead of compiling HipKittens directly, we should:
1. Check if aiter already has HipKittens kernels available
2. Use aiter's Python API to access HK-optimized kernels

---

## Setup Challenges

### Challenge 1: ROCm Compiler Required

HipKittens kernels require ROCm docker or local ROCm installation:
```bash
# Required setup from HipKittens README:
podman pull docker.io/rocm/7.0-preview:rocm7.0_preview_pytorch_training_mi35x_beta

# Then compile with:
source env.src  # Sets ROCm environment variables
make -j64       # Compiles unit tests
```

**On current system:** ROCm docker not available, cannot compile HipKittens kernels.

### Challenge 2: GPU Required for Execution

Even with compilation, HipKittens kernels require AMD GPU (MI300X/MI350X/MI355X).
Local setup without GPU can only verify compilation, not execution.

### Challenge 3: No Python Bindings

HipKittens is C++ templates. To use from Python:
- Option A: Compile as torch extension with `torch.utils.cpp_extension.load_inline`
- Option B: Use aiter's HipKittens integration
- Option C: Write custom pybind11 wrapper

---

## Alternative Path: AITER + HipKittens

### Discovery
HipKittens is now an AITER backend (March 2026). This means:
- aiter may already have HK-optimized kernels
- We can access through aiter's Python API
- No need to compile HipKittens manually

### Verification Needed
```python
# Check if aiter has HipKittens kernels
import aiter

# Look for HK-prefixed functions
print([x for x in dir(aiter) if 'hk' in x.lower() or 'hipkittens' in x.lower()])

# Check gemm backends
print([x for x in dir(aiter) if 'gemm' in x.lower()])

# Look for backend selection
help(aiter.gemm) if hasattr(aiter, 'gemm') else None
```

---

## Revised Strategy

Given the setup constraints, here's the recommended approach:

### Option 1: Check aiter HipKittens Integration (Fastest)

1. Verify if aiter already uses HipKittens for some kernels
2. Check if we can force HipKittens backend via environment variables
3. Test if HipKittens kernels are faster than current CK kernels

### Option 2: Manual HipKittens Compilation (If Needed)

If aiter doesn't have HK kernels yet:

1. Create minimal C++ MoE kernel using HipKittens templates
2. Compile with `torch.utils.cpp_extension.load_inline`
3. Hope runner doesn't block `hipcc` compilation

**Risk:** Runner static scanning may block compilation.

### Option 3: CK-Tile Direct (Recommended)

Since HipKittens setup is complex:

1. Use CK-Tile's `fused_moe` which is already available
2. Study CK-Tile pipeline at `/opt/rocm/include/ck_tile/ops/fused_moe/`
3. Extend for 2-stage fusion if needed

---

## Files Created

```
research/challenges/luma_amd_speedrun/autoresearch/probes/
├── 08_hipkittens_study_notes.md    # HipKittens patterns documented
└── 09_hipkittens_setup_status.md   # This file
```

---

## Checkpoint Report (4 Hour Mark)

### Completed
- ✅ HipKittens paper studied (8-wave ping-pong, tile primitives)
- ✅ Repository cloned and structure analyzed
- ✅ Virtual environment created
- ✅ Discovered HipKittens is C++ header library (not Python)
- ✅ Discovered HipKittens is now an AITER backend

### Blockers
- ❌ ROCm docker not available for compilation
- ❌ No local AMD GPU for testing
- ❌ HipKittens requires C++ compilation, not Python import

### Recommendation

**Pivot to Option 1:** Check if aiter already has HipKittens integration.

```python
# Test this on runner:
import aiter
print([x for x in dir(aiter) if 'hk' in x.lower()])

# Check if any gemm functions have backend parameter
help(aiter.gemm_a4w4) if hasattr(aiter, 'gemm_a4w4') else None
```

If aiter doesn't expose HipKittens yet, **recommend CK-Tile path** instead.

---

## References

- HipKittens: https://github.com/HazyResearch/HipKittens
- Paper: https://arxiv.org/abs/2511.08083
- AITER PR: https://github.com/ROCm/aiter/pull/2039
- Setup docs: /tmp/HipKittens/README.md

---

*Status:* Setup incomplete due to ROCm dependency
*Recommendation:* Verify aiter HipKittens integration before proceeding
