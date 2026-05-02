# 🎯 Meta Agent — Pi Assignment

**Agent:** Pi Agent  
**Role:** Cross-Kernel Pattern Mining & Coordination  
**Mission:** Extract transferable patterns from all 3 kernel optimizations

---

## 📋 CURRENT STATUS

**Phase:** Pending Agent Spawn  
**Started:** -  
**Last Update:** -  
**ETA:** T+1 hour for first pattern extraction

---

## 🎯 ASSIGNMENT

### Primary Role: Cross-Kernel Learning Facilitator

**Mission:**
1. Monitor all 3 kernel agents' submissions
2. Extract common successful patterns
3. Identify transferable optimizations
4. Update shared state files
5. Feed patterns back to struggling kernels

**Why This Matters:**
- Pattern from GEMM MFMA tiling → MoE stage 1 GEMM
- Pattern from MoE dispatch → MLA attention splitting
- Prevents duplicate failed attempts across agents
- Accelerates convergence via shared learning

---

## 🔧 TECHNICAL DETAILS

### Pattern Categories to Extract

#### 1. Tiling Strategies
```json
{
  "pattern": "8_wave_pingpong",
  "origin": "gemm",
  "applicable_to": ["moe_stage1", "mla_attention"],
  "implementation": "__builtin_amdgcn_s_setprio scheduling",
  "conditions": {"thread_count": 512, "waves": 8}
}
```

#### 2. Memory Access Patterns
```json
{
  "pattern": "cooperative_128bit_load",
  "origin": "gemm",
  "applicable_to": ["moe", "mla"],
  "implementation": "int4 vector loads",
  "conditions": {"data_aligned": true}
}
```

#### 3. Parallelism Strategies
```json
{
  "pattern": "lds_double_buffer",
  "origin": "gemm",
  "applicable_to": ["moe", "mla"],
  "implementation": "ping-pong shared memory",
  "conditions": {"smem_available": true}
}
```

### State Files to Maintain

#### File 1: `../autoresearch/state/cross_kernel_failures.json`
Anti-patterns that failed across kernels.

#### File 2: `../autoresearch/state/cross_kernel_successes.json`
Transferable wins from any kernel.

#### File 3: `../autoresearch/state/ksearch_trees/*.json`
Per-kernel world models for co-evolution.

---

## 🔄 AUTOMATED TASKS

### Every 30 Minutes

1. **Scan Submissions:**
   ```python
   import glob
   import json
   
   # Collect verified submissions
   submissions = []
   for file in glob.glob("../submissions/verified/*.json"):
       with open(file) as f:
           submissions.append(json.load(f))
   ```

2. **Extract Patterns:**
   ```python
   def extract_patterns(submission):
       patterns = []
       # Analyze code for optimization patterns
       # Look for: tiling sizes, memory patterns, parallelism strategies
       return patterns
   ```

3. **Update Shared State:**
   ```python
   # Append to cross_kernel_successes.json
   # Mark patterns as transferable to other kernels
   ```

4. **Report to Hub:**
   - Update `.agent/SHARED_DISCOVERIES.md`
   - Notify other agents of new patterns

---

## 📊 PATTERN TRANSFER MATRIX

| Pattern | GEMM | MoE | MLA | Transfer Confidence |
|---------|------|-----|-----|---------------------|
| MFMA 32×32 tiling | ✅ | ✅ Stage 1 | ⚪ | HIGH |
| LDS double buffer | ✅ | ✅ | ✅ | HIGH |
| 8-wave ping-pong | ✅ | ✅ | ✅ | MEDIUM |
| Blockscale quant | ⚪ | ✅ | ⚪ | MEDIUM |
| Einsum for small | ⚪ | ⚪ | ✅ | HIGH |
| Split-K reduce | ⚪ | ⚪ | ✅ | MEDIUM |

---

## 📝 DISCOVERY LOG

### (To be populated by Pi Agent...)

---

## 🚧 BLOCKER TRACKER

| Blocker | Status | Resolution |
|---------|--------|------------|
| Agent spawn | ⚪ PENDING | Waiting for activation signal |

---

## 🔗 REFERENCES

- [K-Search Paper](https://arxiv.org/pdf/2602.19128) — World model co-evolution
- [GPU Kernel Scientist](https://arxiv.org/html/2506.20807v2) — Pattern extraction
- [COORDINATION_HUB](./COORDINATION_HUB.md)
- [SHARED_DISCOVERIES](./SHARED_DISCOVERIES.md)

---

## 🎯 SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Patterns extracted | 10+ per hour |
| Successful transfers | 3+ patterns applied across kernels |
| Anti-patterns logged | All failures documented |
| State file updates | Every 30 minutes |

---

**Activation Signal:** Begin when this file is modified with "🟢 ACTIVE"
