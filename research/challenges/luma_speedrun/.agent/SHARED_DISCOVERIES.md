# 🔬 Shared Discoveries — Cross-Agent Learning

**Last Updated:** 2026-04-05 (T+0)  
**Total Discoveries:** 0 (initialization phase)

---

## 🎯 PURPOSE

This file is the **central knowledge repository** for all 4 agents.

**When to update:**
- Every 30 minutes with new findings
- Immediately upon significant discovery
- When a blocker is resolved
- When a pattern is confirmed transferable

---

## 📋 DISCOVERY TEMPLATE

```markdown
### [TIMESTAMP] — [AGENT] — [KERNEL]
**Type:** [Pattern | Blocker | Optimization | Tool]
**Finding:** [What was discovered]
**Evidence:** [Benchmark results, code snippet, error message]
**Actionable:** [Yes/No — can other kernels use this?]
**Applies to:** [Which other kernels benefit?]

**Code/Config:**
```python
# Relevant code or configuration
```

**Status:** [Confirmed | Testing | Hypothesis]
```

---

## 🏆 CONFIRMED DISCOVERIES (Pre-Loaded from Session 95)

### T-95:00 — BMad Master — All Kernels
**Type:** Pattern  
**Finding:** load_inline HIP compilation WORKS on runner  
**Evidence:** `submission_mfma_v1.py` compiled and ran correctly (26µs)  
**Actionable:** Yes — all kernels can use custom HIP  
**Applies to:** GEMM, MoE, MLA  
**Status:** ✅ CONFIRMED

---

### T-95:00 — BMad Master — All Kernels
**Type:** Blocker  
**Finding:** Python dispatch optimization HURTS ranked scores  
**Evidence:** 6/6 "improvement" submissions scored WORSE on ranked  
**Actionable:** Yes — only GPU compute changes help  
**Applies to:** All kernels  
**Status:** ✅ CONFIRMED

---

### T-95:00 — BMad Master — GEMM
**Type:** Pattern  
**Finding:** BLOCK_K >= 128 mandatory for Triton tl.dot_scaled  
**Evidence:** BLOCK_K=64 produced wrong results, 128/256 passed  
**Actionable:** Yes — always use BLOCK_K >= 128  
**Applies to:** GEMM (Triton path)  
**Status:** ✅ CONFIRMED

---

### T-95:00 — BMad Master — MLA
**Type:** Optimization  
**Finding:** Einsum beats ASM at total_kv <= 32768  
**Evidence:** Benchmark comparison showed einsum faster for small shapes  
**Actionable:** Yes — shape-aware dispatch  
**Applies to:** MLA  
**Status:** ✅ CONFIRMED

---

### T-95:00 — BMad Master — MLA
**Type:** Discovery  
**Finding:** Undocumented ASM APIs available on runner  
**Evidence:** `mla_decode_stage1_asm_fwd` exists and works  
**Actionable:** Yes — bypass high-level APIs  
**Applies to:** MLA  
**Status:** ✅ CONFIRMED

---

### T-95:00 — BMad Master — MoE
**Type:** Discovery  
**Finding:** FP8 blockscale kernel exists (`fmoe_fp8_blockscale_g1u1`)  
**Evidence:** Found in `/home/runner/aiter/hsa/gfx950/fmoe/`  
**Actionable:** Yes — completely different compute path  
**Applies to:** MoE  
**Status:** ⚪ TESTING (v2 implementation in progress)

---

## 🚧 ACTIVE BLOCKERS

| Blocker | Kernel | Agent | Status | Resolution Path |
|---------|--------|-------|--------|-----------------|
| MXFP4→FP8 conversion | MoE | You | 🔴 ACTIVE | v2 implementation |

---

## 🔄 PENDING DISCOVERIES

### To Be Discovered

1. **MLA ASM decode bypass** — Claude Code investigating
2. **GEMM MFMA 128×128** — Gemini CLI developing
3. **Cross-kernel patterns** — Pi Agent mining
4. **FP8 blockscale optimization** — You implementing

---

## 📊 PATTERN STATISTICS

| Category | Count | Transferable |
|----------|-------|--------------|
| Tiling | 1 | 3 kernels |
| Memory | 1 | 3 kernels |
| API Discovery | 2 | 1 kernel each |
| Blockers | 2 | All kernels |
| Optimizations | 1 | 1 kernel |

---

**Next Update:** Upon first new discovery from active sprint
