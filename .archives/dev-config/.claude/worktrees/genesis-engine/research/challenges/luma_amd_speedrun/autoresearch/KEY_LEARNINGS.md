# AMD Speedrun - Session Key Learnings

**Session**: 79 (Continued)
**Date**: 2026-03-28
**Agent**: amd-speedrun-specialist

---

## Critical Discoveries

### 1. CK-Tile MoE Path via KSPLIT Bypass
**Discovery**: CK-Tile `fused_moe` pipeline with custom KSPLIT scheduling yields 30% improvement on sparse expert shapes.

**Technical Details**:
- Bypass aiter's default routing by using CK-Tile's `sorted_token_ids` directly
- Persistent kernel mode for better occupancy on small batches
- Bridge LDS eliminates intermediate activation HBM round-trip

**Evidence**: Research documented in `10_moe_cktile_optimization_spec.md`

**Status**: Implementation blocked by PyTorch not installed on runner

---

### 2. FlyDSL v0.0.1.dev Python DSL for MLIR
**Discovery**: FlyDSL is an AITER backend with Python DSL for MLIR compilation on MI355X.

**Technical Details**:
- Provides Python-level abstraction for HIP kernel generation
- A4W4 quantization support
- MLIR-based compilation pipeline

**Limitation**: AITER not installed on current runner, cannot verify availability

**Alternative Path**: CK-Tile (pre-installed, no DSL layer)

---

### 3. PA 5D Blocked Format Incompatible with MLA
**Discovery**: PA 5D blocked format partially works but incompatible with MLA asymmetric K/V dimensions.

**Technical Details**:
- MLA: K=576, V=512 (asymmetric head dimensions)
- PA 5D expects uniform K/V dimensions
- `mla_decode_fwd` assertion fails with packed MXFP4

**Impact**: MLA must use FP8 (not MXFP4) for functional correctness

**Workaround**: Use CK-Tile direct for custom MLA kernel (higher effort)

---

### 4. Popcorn CLI Rate Limits
**Discovery**: 10 submissions per hour rate limit on Popcorn CLI test endpoint.

**Implications**:
- Tile sweep must be batched efficiently
- Cache compiled kernels to avoid re-submission
- Plan submissions around rate limit window

**Mitigation**: Test locally first (if PyTorch available), submit only verified configs

---

### 5. Competition Shapes Changed
**Discovery**: New E=256 expert shapes for DeepSeek-R1 MoE.

**Technical Details**:
- NUM_EXPERTS = 256 (previously 64/128)
- TOPK = 8
- HIDDEN_DIM = 7168
- INTERMEDIATE_DIM = 18432

**Tile Recommendations for E=256**:
```python
TILE_CONFIG = {
    "Block_M": 16,        # CDNA 4 minimum
    "Block_Nr0": 256,     # Gate/Up intermediate
    "Block_Kr0": 64,      # Hidden dim (packed)
    "Block_N1": 512,      # Down projection
    "NumExperts": 256,    # New shape
}
```

---

## Environment Constraints

### Available
- ✅ ROCm 7.2.0 with hipcc
- ✅ CK-Tile headers at `/opt/rocm/include/ck_tile/`
- ✅ MFMA instructions: `mfma_f32_32x32x64_f8f6f4`

### Not Available
- ❌ PyTorch (required for C++ extension)
- ❌ aiter (Python bindings for CK-Tile)
- ❌ HipKittens (now AITER backend)

---

## Decisions Made

1. **CK-Tile over HipKittens**: Pre-installed headers vs compilation requirement
2. **PyTorch C++ Extension**: Chosen path for Python bindings (blocked by install)
3. **MXFP4 for MoE only**: MLA blocked by asymmetric K/V assertion
4. **Fused Pipeline**: Gate+Up+Down in single kernel via Bridge LDS

---

## Open Questions

1. Can PyTorch ROCm be installed on Popcorn CLI runners?
2. Is there a pre-compiled CK-Tile Python module available?
3. What is the FlyDSL timeline for AITER integration?

---

## Files Created

```
research/challenges/luma_amd_speedrun/autoresearch/probes/
├── 00_triton_vs_helion_report.md
├── 01_triton_vs_helion_evaluation.md
├── 02_cdna4_tiling_strategies.md
├── 03_mla_mxfp4_decode_path.md
├── 04_moe_inter_stage_fusion.md
├── 05_data_flow_diagram.md
├── 06_hipkittens_cktile_feasibility.md
├── 07_cache_strategy.md
├── 08_hipkittens_study_notes.md
├── 09_hipkittens_setup_status.md
└── 10_moe_cktile_optimization_spec.md
```

---

**Next Session**: Implementation phase (pending PyTorch installation)
