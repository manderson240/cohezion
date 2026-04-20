# Luma AMD Speedrun - Competition Workspace

**Multi-Session Coordination Required** ⚠️

This directory is shared across multiple sessions (opencode, gemini, antigravity, claude). **Do not overwrite files without coordination!**

---

## 🚨 Critical Files

### **COORDINATION.md** ← START HERE
**Session coordination hub** - Check this first before submitting!
- Current session statuses
- Staged submissions from all sessions
- Lock mechanism to prevent conflicts
- Best results and benchmarks

### **Official Reference Implementations**
Aligned with `/home/mike-anderson/dev/cohezion/luma_speedrun/` (official AMD GPU MODE competition files):
- `kernels/mixed-mla/reference.py` - MLA decode (FP8 optimized)
- `kernels/mxfp4-mm/reference.py` - GEMM (MXFP4)
- `kernels/moe-mxfp4/reference.py` - MoE (fused_moe)

### **SUBMISSION_LOCK.txt** (Deprecated)
Old coordination mechanism - use COORDINATION.md instead.

---

## Directory Structure

```
luma_amd_speedrun/                          ← This directory (competition workspace)
├── COORDINATION.md                         ⭐ Multi-session coordination
├── README.md                               (this file)
├── RULES.md                                Competition rules
├── TODO.md                                 Task tracking
├── technical_analysis.md                   Technical deep-dives
├── plan.md                                 Strategic planning
├── kernel_program.md                       Program specification
├── benchmark_baseline.py                   Baseline measurements
├── submission_logs/                          Historical logs
│
└── kernels/                                ⭐ Submission directories
    ├── mixed-mla/                          MLA decode kernel
    │   ├── submission.py                   ← Current submission (DO NOT OVERWRITE!)
    │   ├── reference.py                    ⭐ Official reference (from luma_speedrun/)
    │   ├── reference.py.backup             Previous version backup
    │   ├── task.py                         Problem definition
    │   ├── eval.py                         Evaluation script
    │   └── staging/                        ⭐ Session staging area
    │       ├── submission.opencode.k2-5.20260318_150205.py
    │       └── submission.opencode.k2-5.latest.py
    │
    ├── mxfp4-mm/                           GEMM kernel
    │   ├── submission.py
    │   ├── reference.py                    ⭐ Official reference
    │   ├── reference.py.backup
    │   ├── task.py
    │   ├── eval.py
    │   └── staging/             ⭐ Session staging area
    │       └── submission.opencode.k2-5.20260318_150205.py
    │
    └── moe-mxfp4/               MoE kernel
        ├── submission.py
        ├── reference.py
        ├── task.py
        ├── eval.py
        └── staging/             ⭐ Session staging area
```

---

## Quick Start

### For New Sessions

1. **Check COORDINATION.md first** - See who's working on what
2. **Copy your submission to staging**:
   ```bash
   cp your_submission.py kernels/{kernel}/staging/submission.{session}.{timestamp}.py
   ```
3. **Update COORDINATION.md** - Add your session to registry
4. **Wait for consensus** - Before promoting to main submission.py

### Submitting to Popcorn

```bash
# Navigate to kernel directory
cd kernels/mixed-mla/  # or mxfp4-mm/ or moe-mxfp4/

# Test mode (check correctness)
popcorn-cli submit submission.py --gpu MI355X --mode test --no-tui

# Benchmark mode (check performance)
popcorn-cli submit submission.py --gpu MI355X --mode benchmark --no-tui

# Leaderboard mode (official submission)
popcorn-cli submit submission.py --gpu MI355X --mode leaderboard --no-tui
```

**Important**: Use file directives in your submission.py:
```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X
```

---

## Competition Details

**Phase**: Qualifiers (March 6 - April 6, 2026)
**Deadline**: March 30, 2026 (11 days remaining)
**Prize Pool**: $100K (Top 10 advance to Finals)
**Total Prize**: $1.1M (including Finals)

### Target Performance

| Kernel | Current | Target | Leader |
|--------|---------|--------|--------|
| **GEMM** | ~23µs | ≤10µs | 9.671µs |
| **MLA** | ~67µs | ≤20µs | 4.335µs |
| **MoE** | TBD | ≤145µs | 145.177µs |

### Scoring

- Max 20 kernels per problem considered
- Must beat baseline to get points
- Geometric mean across test cases
- Points = Max Points × (1 - rank/20)

---

## Session Coordination

### Active Sessions

| Session | Status | Working Directory |
|---------|--------|-------------------|
| opencode-hip-k2-5 | ✅ ACTIVE | `/hip-kernels-kimi-k2-5/` |
| gemini | ❓ Unknown | TBD |
| antigravity | ❓ Unknown | TBD |
| claude | ❓ Unknown | TBD |

### Current Best Submissions (from COORDINATION.md)

**GEMM**: 
- opencode: ~23µs (gemm_a4w4) ✅

**MLA**:
- opencode: ~67µs (reference) ✅

**MoE**:
- TBD

---

## Resources

### Official Reference Implementations
Located at `/home/mike-anderson/dev/cohezion/luma_speedrun/`:
- `amd-mixed-mla/reference_implementation.py` - MLA decode
- `amd-mxfp4-mm/reference_implementation.py` - GEMM
- `amd-moe-mxfp4/reference_implementation.py` - MoE

These are the **official AMD GPU MODE competition reference files**. The competition directory (`research/challenges/luma_amd_speedrun/`) has copies aligned with these official versions.

### Documentation
- [Popcorn CLI Usage Guide](/hip-kernels-kimi-k2-5/POPCORN_CLI_GUIDE.md)
- [Official Competition Rules](https://github.com/gpu-mode/popcorn-cli)
- [Reference Kernels](https://github.com/gpu-mode/reference-kernels)

### Support
- **Discord**: https://discord.gg/gpumode
- **GitHub**: https://github.com/gpu-mode/popcorn-cli
- **Website**: https://www.gpumode.com/

### Workspace References

**Opencode Session**:
- Working directory: `/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/`
- Submissions: 29 files including optimized variants
- Status: Active, GEMM and MLA working

**Other Sessions**:
- Please update this section with your workspace paths

---

## Workflow

### 1. Individual Development (Each Session)
```
Session Workspace
├── Your submission files
├── Reference implementations
└── Test scripts
```

### 2. Staging (Copy to Competition)
```
kernels/{kernel}/staging/
├── submission.opencode.k2-5.20260318_150205.py
├── submission.gemini.v2.20260318_160000.py
└── submission.antigravity.20260318_170000.py
```

### 3. Collaborative Review
- Compare benchmark results in COORDINATION.md
- Decide which submission to promote
- Consensus required before overwriting main submission.py

### 4. Final Submission
- Copy best staged submission to `kernels/{kernel}/submission.py`
- Submit via Popcorn CLI
- Document results in COORDINATION.md

---

## Important Notes

⚠️ **Never overwrite `submission.py` directly** - Use staging first

⚠️ **Always check COORDINATION.md before submitting** - Avoid conflicts

⚠️ **Update COORDINATION.md immediately** - After staging/submitting

⚠️ **Document your learnings** - In session workspace and vault

---

## Action Items

- [ ] All sessions: Copy current submissions to staging
- [ ] All sessions: Update COORDINATION.md with your status
- [ ] Consensus: Decide on best GEMM submission
- [ ] Consensus: Decide on best MLA submission
- [ ] Consensus: Decide on best MoE submission
- [ ] Final submission before March 30

---

**Last Updated**: 2026-03-18 15:05 UTC
**Next Review**: TBD
