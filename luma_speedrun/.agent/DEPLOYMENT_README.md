# 🚀 Deployment Package — Ready for Runner

**Created:** 2026-04-06  
**Status:** ✅ Ready for AMD MI355X Runner

---

## 📦 Package Contents

### Submissions (3 kernels, 1,112 lines total)

| Kernel | File | Lines | Strategy | Status |
|--------|------|-------|----------|--------|
| **MoE** | `submission_fp8_blockscale_v2.py` | 348 | FP8 blockscale conversion | ✅ Syntax OK |
| **MLA** | `submission_asm_decode_bypass.py` | 271 | BF16 ASM bypass | ✅ Syntax OK |
| **GEMM** | `submission_mfma_128x128_v1.py` | 493 | 8-wave ping-pong MFMA | ✅ Syntax OK |

### Deployment Script
- `deploy_submissions.sh` — Automated test/benchmark/leaderboard submission

### Documentation
- `COORDINATION_HUB.md` — Real-time agent status
- `PHASE_3_PLAN.md` — Testing protocol
- `DEPLOYMENT_README.md` — This file

---

## 🎯 Execution Instructions

### Step 1: Deploy to Test (Correctness)
```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun
./deploy_submissions.sh test
```

**Expected:** All 3 submissions pass 4/4 tests

### Step 2: Deploy to Benchmark (If Tests Pass)
```bash
./deploy_submissions.sh benchmark
```

**Expected:** Compare times to baselines

### Step 3: Deploy to Leaderboard (If Benchmark Improves)
```bash
./deploy_submissions.sh leaderboard
```

**Expected:** Rank improvement on luma-leaderboard

---

## 📊 Success Criteria

| Kernel | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| MoE | 154µs | <100µs | 1.54x faster |
| MLA | 69µs | <40µs | 1.7x faster |
| GEMM | 13.4µs | <8µs | 1.7x faster |

---

## 🔧 Individual Submission Commands

### MoE FP8 Blockscale
```bash
cd amd-moe-mxfp4
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py
```

### MLA ASM Bypass
```bash
cd amd-mixed-mla
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-mixed-mla \
  submission_asm_decode_bypass.py
```

### GEMM MFMA 128×128
```bash
cd amd-mxfp4-mm
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-mxfp4-mm \
  submission_mfma_128x128_v1.py
```

---

## 📝 Submission Details

### MoE: FP8 Blockscale v2
**Strategy:** Convert MXFP4 weights to FP8 blockscale (128×128 tiles) using `fmoe_fp8_blockscale_g1u1`

**Key Optimizations:**
- Block-wise FP8 quantization with E8M0 scales
- Proper weight shuffling for ASM kernel
- Fallback to baseline for incompatible shapes

**Expected Impact:** 1.5x+ speedup via FP8 wider MFMA throughput

---

### MLA: ASM Decode Bypass
**Strategy:** Trigger `mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co` via BF16-only tensors

**Key Optimizations:**
- Bypass FP8 quantization (BF16 direct)
- Shape manipulation for decode kernel selection
- Direct `mla_decode_stage1_asm_fwd` API

**Expected Impact:** 1.7x+ speedup via decode-specific kernel

---

### GEMM: MFMA 128×128 Ping-Pong
**Strategy:** 8-wave ping-pong with 128×128 tiles and double-buffered LDS

**Key Optimizations:**
- 512 threads = 8 waves of 64
- Cooperative 128-bit global loads
- XOR swizzle for bank conflict avoidance
- `__builtin_amdgcn_s_setprio` wave scheduling

**Expected Impact:** 1.7x+ speedup via larger tiles + better parallelism

---

## 🔍 Troubleshooting

### If Test Fails
1. Check error log: `deploy_*_TIMESTAMP.log`
2. Common issues:
   - Weight format mismatch → Check shuffle layout
   - Scale tensor dimensions → Verify divisible by 128
   - Kernel API signature → Compare to runner inventory

### If Benchmark No Improvement
1. Check if ranked shapes different from test
2. Profile with IntelliKit (if available)
3. Consult cross-kernel patterns in `autoresearch/state/`

### If Timeout
1. Retry with longer timeout: `timeout 900 ...`
2. Check runner status
3. May be JIT compilation (first run only)

---

## 📞 Coordination

**Agent Status:** See `COORDINATION_HUB.md`
**Shared Discoveries:** See `SHARED_DISCOVERIES.md`
**Pattern Mining:** Run `autoresearch/pattern_miner.py --report`

---

**Ready for deployment. Good luck! 🚀**
