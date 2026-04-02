# Luma Speedrun - Multi-Agent Team Structure

## Parallel Execution Strategy

We have **7 specialist agents** across **3 kernel teams**, all working simultaneously:

### Team GEMM (Target: 4.3µs, Current: 22.8µs)

| Agent | Strategy | Location | Priority |
|-------|----------|----------|----------|
| **claude-gemm-primary** | load_inline + V_MFMA_SCALE | luma_speedrun/ | P0 |
| **autoresearch-gemm** | K-Search tree exploration | research/challenges/ | P1 |
| **kimi-gemm-rocwmma** | rocWMMA + hipKittens | hip-kernels-kimi-k2-5/ | P1 |

**Key Breakthrough**: V_MFMA_SCALE_F32_16X16X128_F8F6F4 intrinsic - FP4 multiply-accumulate in 1 instruction

### Team MLA (Target: 33.0µs, Current: 69.7µs)

| Agent | Strategy | Location | Priority |
|-------|----------|----------|----------|
| **claude-mla** | SnapMLA fused kernel | luma_speedrun/ | P0 |
| **autoresearch-mla** | Direct ASM dispatch | research/challenges/ | P1 |

**Key Breakthrough**: Fuse stage1+reduce into single dispatch (eliminates ~40µs Python overhead)

### Team MoE (Target: 109.8µs, Current: 154.2µs)

| Agent | Strategy | Location | Priority |
|-------|----------|----------|----------|
| **claude-moe** | LDS bridge / direct CK | luma_speedrun/ | P0 |
| **moe-specialist** | Adaptive KSPLIT | kernels/moe-mxfp4/ | P1 |

**Key Breakthrough**: 182 pre-compiled CK kernels at `/home/runner/aiter/hsa/gfx950/fmoe_2stages/`

## Quick Commands

### Run All Teams in Parallel
```bash
python luma_speedrun/orchestrate.py
```

### Run Single Kernel Team
```bash
# GEMM only
python luma_speedrun/orchestrate.py gemm

# MLA only
python luma_speedrun/orchestrate.py mla

# MoE only
python luma_speedrun/orchestrate.py moe
```

### Manual Parallel Execution (Bash)
```bash
cd /home/mike-anderson/dev/cohezion

# Start GEMM agents in parallel
(cd .worktrees/luma-breakthrough-sprint && python luma_speedrun/autoresearch/driver.py --kernel gemm) &
(cd research/challenges/luma_amd_speedrun && python autokernel.py --kernel gemm) &

# Start MLA agents
(cd .worktrees/luma-breakthrough-sprint && python luma_speedrun/autoresearch/driver.py --kernel mla) &

# Start MoE agents
(cd .worktrees/luma-breakthrough-sprint && python luma_speedrun/autoresearch/driver.py --kernel moe) &

# Wait for all
wait
echo "All agents complete"
```

## Resource Allocation

| Resource | GEMM | MLA | MoE | Shared |
|----------|------|-----|-----|--------|
| GPU | MI355X | MI355X | MI355X | Popcorn runners |
| CPU | 8 cores | 8 cores | 8 cores | 395X |
| Memory | 32GB | 32GB | 32GB | 128GB total |
| Compile Time | ~30s | ~30s | ~30s | Parallel safe |
| Benchmark Time | ~60s | ~60s | ~60s | Rate limited |

## Communication Protocol

Agents share results via:
1. **SurrealDB** (MCP) - `coherence.save_kernel_result()`
2. **JSONL files** - `luma_speedrun/logs/*.jsonl`
3. **Git commits** - Each agent commits winners to branch

## Daily Standup Format

```
[Agent:claude-gemm-primary]
- Commits: 5
- Best: 22.8µs (target: 4.3µs)
- Strategy: V_MFMA_SCALE tiling
- Blockers: Compilation errors on gfx950

[Agent:autoresearch-gemm]
- Commits: 3
- Best: 24.1µs
- Strategy: K-Search node expansion
- Blockers: None

[Agent:moe-specialist]
- Commits: 8
- Best: 154.2µs (target: 109.8µs)
- Strategy: KSPLIT grid search
- Blockers: Need more shapes
```

## Breakthrough Sharing

When any agent finds a breakthrough:
1. Saves to `staging/submission.{agent}.winner.py`
2. Commits to worktree with `[BREAKTHROUGH]` prefix
3. Posts to MCP: `coherence.update_kernel_record()`
4. Other agents pull and adapt the strategy

## CI/CD for Parallel Teams

```yaml
# .github/workflows/parallel-luma.yml
strategy:
  matrix:
    agent: [gemm-primary, gemm-ksearch, mla, moe]
    
jobs:
  optimize:
    runs-on: ubuntu-latest
    steps:
      - name: Run Agent
        run: python luma_speedrun/orchestrate.py ${{ matrix.agent }}
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: results-${{ matrix.agent }}
          path: luma_speedrun/logs/
```

## Success Metrics per Team

| Team | Leader | Current | Gap | Success Criteria |
|------|--------|---------|-----|------------------|
| GEMM | 4.3µs | 22.8µs | 5.3× | <5µs (top 10) |
| MLA | 33.0µs | 69.7µs | 2.1× | <35µs (top 10) |
| MoE | 109.8µs | 154.2µs | 1.4× | <110µs (top 3) |

**Total Points Available**: 1,000 + 1,250 + 1,500 = **3,750 points**