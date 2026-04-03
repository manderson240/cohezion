# RESEARCH & TESTING PLAN
**While waiting for rate limit (54 minutes remaining)**  
**Time**: $(date)

---

## 🎯 IMMEDIATE RESEARCH PRIORITIES

### 1. HipKittens MoE Kernel ⭐ HIGHEST PRIORITY

**Source**: `/home/mike-anderson/dev/cohezion/.claude/worktrees/genesis-engine/hipkittens_moe/`

**Why Test This**
- Fully implemented 2-stage fused MoE
- Register-resident intermediates (no HBM writeback)
- Target: <110µs (we're at 93.7µs with AITER)
- May be faster than current AITER approach

**Files to Test**:
```bash
# Copy to worktree
cp /home/mike-anderson/dev/cohezion/.claude/worktrees/genesis-engine/hipkittens_moe/submission_compact.py \
   /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-moe-mxfp4/submission_hipkittens.py

# Test compile
python3 submission_hipkittens.py --compile --arch gfx950

# Benchmark when rate limit clears
popcorn-cli submit submission_hipkittens.py --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4
```

**Potential Gain**: Could push from 93.7µs to <90µs (closer to Rank 1)

---

### 2. MFMA MLA Kernel ⭐ HIGH PRIORITY

**Source**: `/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/sessions/20260319_112740/vault/patterns/`

**Why Test This**
- MFMA intrinsic: `__builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4`
- 3-5× speedup over LUT approach
- Uses native CDNA 3 instructions
- Not yet tested on real hardware

**Action**:
```bash
# Find if there's existing implementation
find /home/mike-anderson/dev/cohezion -name "*mla_mfma*" -o -name "*mfma_mla*" 2>/dev/null

# Create test submission with MFMA inline assembly
```

**Potential Gain**: 69.7µs → potentially 20-35µs (getting closer to 33µs Rank 1)

---

### 3. Custom Triton GEMM ⭐ MEDIUM PRIORITY

**Source**: `research/challenges/luma_amd_speedrun/autoresearch/probes/`

**Why Test This**
- Official template from gpu-mode/reference-kernels proves load_inline works
- V_MFMA_SCALE intrinsic for FP4
- 16×16×128 MFMA tiles

**Files to Study**:
- `custom_triton_moe_spec.md` (29KB of specs)
- `phase2_mxfp4_conversion.md` (19KB)
- `hipkittens_mxfp4_gemm_spec.md`

**Potential Gain**: 22µs → potentially 10-15µs (still far from 4.3µs but improvement)

---

## 🔬 RESEARCH METHODOLOGY

### Step 1: Analyze Staging Winners (5 min)
```bash
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/research/challenges/luma_amd_speedrun/kernels

# Check what makes winners work
for kernel in moe gemm mla; do
    echo "=== $kernel winner ==="
    cat */staging/submission.${kernel}-winner.py 2>/dev/null | head -50
    echo ""
done
```

### Step 2: Check Untested Approaches (10 min)
```bash
# From team.json extract:
grep -r "untapped\|TODO\|untested\|unexplored" \
    /home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/ \
    --include="*.json" --include="*.md" 2>/dev/null | head -30
```

### Step 3: External Research Check (10 min)
```bash
# Check if there are new commits in reference kernels
curl -s https://api.github.com/repos/gpu-mode/reference-kernels/commits?path=problems/amd | head -20
```

---

## 🧪 TESTING QUEUE (For When Rate Limit Clears)

### Priority 1: Submit Today's Improvements
| Kernel | Current | Historical | Submit? | Time |
|--------|---------|------------|---------|------|
| **MoE** | 93.7µs | 154.183µs | ✅ YES | 23:10 |
| **GEMM** | 18.4µs | 22.0µs | ✅ YES | 23:15 |
| **MLA** | ? | 69.7µs | ⚠️ Retry | 23:20 |

### Priority 2: Test HipKittens MoE
- File: `submission_hipkittens.py`
- Expected: <93.7µs (better than current)
- Risk: May not compile (new kernel)

### Priority 3: Test MFMA MLA
- Need to create: `submission_mfma_mla.py`
- Expected: potentially <50µs
- Risk: MFMA may not be available in runner environment

### Priority 4: Parameter Sweeps
```python
# MoE parameter sweep (if HipKittens doesn't work)
for block_m in [32, 64, 128]:
    for use_nt in [True, False]:
        for ksplit in [0, 2, 4]:
            # Test each combination
```

---

## 📊 EXPECTED TIMELINE

```
22:15 - Rate limited (submitted MoE)
22:15-23:10 - Research phase (55 minutes)
  └─ Analyze staging winners
  └─ Study HipKittens kernel
  └─ Prepare MFMA MLA submission
  └─ Check external resources

23:10 - Rate limit clears
23:10-23:30 - Submit all improvements
  └─ MoE (93.7µs)
  └─ GEMM (18.4µs)  
  └─ MLA (retry)

23:30-00:00 - Test HipKittens
  └─ Compile and test
  └─ Submit if successful

00:00-08:00 - Overnight optimization
  └─ Run breakthrough_orchestrator.py
  └─ Continuous parameter sweeps
```

---

## 🎯 SUCCESS CRITERIA

### By End of Research Phase (23:10)
- [ ] HipKittens kernel ready to test
- [ ] MFMA MLA submission prepared
- [ ] All three current submissions ready for leaderboard
- [ ] External research completed

### By End of Testing Phase (00:00)
- [ ] All improvements submitted to leaderboard
- [ ] HipKittens tested (success or failure documented)
- [ ] At least one breakthrough confirmed (Rank 1 or close)

---

## 🔥 COMMANDS TO EXECUTE NOW

```bash
# 1. Analyze staging winners
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/research/challenges/luma_amd_speedrun/kernels
for f in */staging/submission.*-winner.py; do echo "=== $f ===" && head -30 "$f" && echo; done

# 2. Copy HipKittens for testing
cp /home/mike-anderson/dev/cohezion/.claude/worktrees/genesis-engine/hipkittens_moe/*.py \
   /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-moe-mxfp4/

# 3. Study custom Triton specs
cat /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/research/challenges/luma_amd_speedrun/autoresearch/probes/custom_triton_moe_spec.md | head -100

# 4. Check for new external resources
curl -s https://raw.githubusercontent.com/gpu-mode/reference-kernels/main/problems/amd/README.md 2>/dev/null | head -50

# 5. Prepare submission queue
echo "MoE: 93.7µs" > /tmp/submission_queue.txt
echo "GEMM: 18.4µs" >> /tmp/submission_queue.txt
echo "MLA: retry" >> /tmp/submission_queue.txt
```

---

## 💡 KEY INSIGHTS FROM RESEARCH

1. **HipKittens MoE** - Already implemented, may be faster than 93.7µs
2. **MFMA MLA** - 3-5× theoretical speedup, needs implementation
3. **Custom Triton GEMM** - Has specs but needs execution
4. **Staging Winners** - Use "ghost registry" pattern (fingerprinting)
5. **Rate Limit** - 1/hour means we must prioritize submissions

**Next 55 minutes**: Research and prepare. **Then**: Execute submissions aggressively.
