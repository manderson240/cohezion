# Agent Orchestration Guide
# Luma AMD Speedrun - Specialist Agent Pattern

**Purpose**: How to spawn and manage specialist agents for parallel kernel optimization

**Last Updated**: 2026-03-18 15:30 UTC  
**Current Phase**: Day 1 - Agent Spawning  
**Status**: Ready to execute

---

## Overview

This document describes how to spawn and manage specialist agents for optimizing the three competition kernels (GEMM, MLA, MoE) in parallel.

### Why Specialist Agents?

- **Parallel execution**: All three kernels optimized simultaneously
- **Clear ownership**: Each agent focuses on one kernel
- **No coordination overhead**: Agents work independently
- **Shared auth**: Single Popcorn CLI auth source
- **Scalable**: Easy to add more agents or iterations

---

## Agent Types

### 1. GEMM Specialist Agent

**Focus**: amd-mxfp4-mm kernel (MXFP4 GEMM)

**Goals**:
- Optimize `gemm_a4w4` usage
- Explore tile sizes and block configurations
- Target: <15µs (first milestone), <10µs (final)
- Current baseline: ~23µs

**Input Files**:
- Reference: `kernels/mxfp4-mm/reference.py`
- Current best: `kernels/mxfp4-mm/staging/submission.opencode.k2-5.latest.py`
- Task: `kernels/mxfp4-mm/task.py`

**Output**:
- New submission: `kernels/mxfp4-mm/staging/submission.{agent}.{timestamp}.py`
- Benchmark results
- Optimization notes in vault

**Key Techniques**:
- Tile size tuning (16x16, 32x32, 64x64)
- Block configuration optimization
- Scale quantization strategies
- Memory access patterns

**Spawn Command**:
```
Task: Spawn GEMM optimization agent
Prompt: Optimize the GEMM kernel (amd-mxfp4-mm) using gemm_a4w4. 
Target: <15µs from current ~23µs baseline.
Work in kernels/mxfp4-mm/ directory.
Stage submissions to staging/ folder.
Update COORDINATION.md with results.
```

---

### 2. MLA Specialist Agent

**Focus**: amd-mixed-mla kernel (MLA Decode)

**Goals**:
- Optimize FP8 decode path
- Explore metadata handling
- Target: <40µs (first milestone), <20µs (final)
- Current baseline: ~67µs

**Input Files**:
- Reference: `kernels/mixed-mla/reference.py`
- Current best: `kernels/mixed-mla/staging/submission.opencode.k2-5.latest.py`
- Task: `kernels/mixed-mla/task.py`

**Output**:
- New submission: `kernels/mixed-mla/staging/submission.{agent}.{timestamp}.py`
- Benchmark results
- Optimization notes in vault

**Key Techniques**:
- FP8 quantization optimization
- Metadata caching
- Persistent mode tuning
- KV cache format selection (bf16/fp8/mxfp4)

**Spawn Command**:
```
Task: Spawn MLA optimization agent
Prompt: Optimize the MLA decode kernel (amd-mixed-mla) using mla_decode_fwd.
Target: <40µs from current ~67µs baseline.
Work in kernels/mixed-mla/ directory.
Stage submissions to staging/ folder.
Update COORDINATION.md with results.
```

---

### 3. MoE Specialist Agent

**Focus**: amd-moe-mxfp4 kernel (MoE Layer)

**Goals**:
- Optimize `fused_moe` usage
- Explore expert routing strategies
- Target: <145µs (baseline unknown)
- Current status: Not started

**Input Files**:
- Reference: `kernels/moe-mxfp4/reference.py`
- Task: `kernels/moe-mxfp4/task.py`

**Output**:
- New submission: `kernels/moe-mxfp4/staging/submission.{agent}.{timestamp}.py`
- Benchmark results
- Optimization notes in vault

**Key Techniques**:
- Expert selection optimization
- Weight shuffling strategies
- Activation fusion
- Top-k routing efficiency

**Spawn Command**:
```
Task: Spawn MoE optimization agent
Prompt: Optimize the MoE kernel (amd-moe-mxfp4) using fused_moe.
First establish baseline, then optimize.
Work in kernels/moe-mxfp4/ directory.
Stage submissions to staging/ folder.
Update COORDINATION.md with results.
```

---

### 4. Results Monitoring Agent

**Focus**: All kernels

**Goals**:
- Monitor Popcorn CLI submission status
- Track benchmark results
- Update coordination files
- Alert on auth issues

**Responsibilities**:
- Check submission status every 30 minutes
- Update `COORDINATION.md` with new results
- Track best performers per kernel
- Monitor for auth errors
- Document learnings

**Commands**:
```bash
# Check submissions
popcorn-cli submissions list --leaderboard amd-mixed-mla
popcorn-cli submissions list --leaderboard amd-mxfp4-mm
popcorn-cli submissions list --leaderboard amd-moe-mxfp4

# Check auth
cat ~/.popcorn.yaml
```

**Spawn Command**:
```
Task: Spawn results monitoring agent
Prompt: Monitor all kernel submissions and results.
Check Poporn CLI every 30 minutes.
Update COORDINATION.md with latest results.
Track best performers per kernel.
Alert on any auth issues.
```

---

## Agent Communication Protocol

### 1. Work in Isolation
- Each agent has their own subdirectory in `staging/`
- No coordination needed between agents
- Parallel execution is safe

### 2. Stage Results
When an agent completes work:
```bash
# Copy submission to staging
cp submission.py kernels/{kernel}/staging/submission.{agent}.{timestamp}.py

# Update coordination
echo "Agent {agent} completed {kernel} submission" >> COORDINATION.md
```

### 3. Document Learnings
- Store optimization notes in vault
- Document what worked and what didn't
- Share insights for other agents

### 4. Notify Coordinator
- Update `COORDINATION.md` with status
- Report benchmark results
- Flag any blockers

---

## Coordinator Responsibilities

### 1. Spawn Agents
Use the Task tool to spawn specialist agents:
```python
Task(
    description="Spawn GEMM agent",
    prompt="Optimize GEMM kernel...",
    subagent_type="general"
)
```

### 2. Monitor Progress
- Check `COORDINATION.md` for updates
- Review `staging/` directories
- Track benchmark results

### 3. Handle Auth
- Maintain `~/.popcorn.yaml`
- Fix auth issues if they arise
- Announce auth status to agents

### 4. Final Submission
- Select best submission per kernel
- Copy to main `submission.py`
- Submit to leaderboard
- Document results

---

## Workflow Examples

### Example 1: Spawning All Agents (Day 1)

```python
# Spawn all specialist agents simultaneously
Task(description="GEMM optimization", prompt="...")
Task(description="MLA optimization", prompt="...")
Task(description="MoE optimization", prompt="...")
Task(description="Results monitoring", prompt="...")
```

### Example 2: Reviewing Results (Day 2)

```bash
# Check what agents produced
ls kernels/*/staging/

# Review COORDINATION.md
cat COORDINATION.md

# Compare results
# Select best performers
```

### Example 3: Iteration (Day 3-4)

```python
# Spawn refinement agents for top performers
Task(description="GEMM refinement", prompt="Improve upon ~20µs result...")
Task(description="MLA refinement", prompt="Improve upon ~50µs result...")
```

---

## Agent Naming Convention

Use descriptive names:
- `gemm-optimizer-v1`
- `mla-fp8-explorer`
- `moe-baseline-establisher`
- `results-tracker`

Include in submission filenames:
- `submission.gemm-optimizer.20260318_143000.py`
- `submission.mla-fp8.20260318_150000.py`

---

## Success Criteria

### GEMM Agent Success
- [ ] Submission passes test mode
- [ ] Benchmark shows improvement over baseline
- [ ] Documented optimization approach
- [ ] Staged in `kernels/mxfp4-mm/staging/`

### MLA Agent Success
- [ ] Submission passes test mode
- [ ] Benchmark shows improvement over baseline
- [ ] Documented optimization approach
- [ ] Staged in `kernels/mixed-mla/staging/`

### MoE Agent Success
- [ ] Submission passes test mode
- [ ] Baseline established
- [ ] Benchmark shows improvement
- [ ] Staged in `kernels/moe-mxfp4/staging/`

### Results Agent Success
- [ ] All submissions tracked
- [ ] COORDINATION.md updated regularly
- [ ] Best performers identified
- [ ] No missed submissions

---

## Troubleshooting

### Agent Not Responding
- Check if task completed
- Review agent output
- Respawn if needed

### Auth Issues
- Check `~/.popcorn.yaml`
- Run `popcorn-cli reregister github` if needed
- Update SESSION_HANDOFF.md
- Announce to all agents

### Submission Failures
- Check test mode first
- Review error logs
- Iterate and resubmit
- Document failure reasons

### Coordination Conflicts
- Check SESSION_HANDOFF.md for current state
- Verify no other session active
- Update timestamps
- Proceed with clear ownership

---

## Quick Reference

### Spawn All Agents
```
Task: Spawn all specialist agents
Prompt: Spawn GEMM, MLA, MoE, and Results agents simultaneously.
Each agent should work on their assigned kernel.
Agents should update COORDINATION.md with progress.
```

### Check Agent Status
```bash
# List all staged submissions
find kernels/*/staging/ -name "*.py" -type f

# Check coordination status
grep -A 5 "Current State" COORDINATION.md
```

### Select Best Submission
```bash
# Compare benchmark results
# Copy best to main submission.py
cp kernels/{kernel}/staging/best_submission.py kernels/{kernel}/submission.py
```

---

**Document Owner**: Multi-session coordination team  
**Next Review**: After agent spawning or major workflow change  
**Status**: ACTIVE - Ready for agent spawning

---

*End of AGENT_ORCHESTRATION.md*
