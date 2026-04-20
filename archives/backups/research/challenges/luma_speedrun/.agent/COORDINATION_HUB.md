# 🚀 Luma AMD Speedrun — Agent Coordination Hub

**Last Updated:** 2026-04-05  
**Deadline:** April 7, 2026 07:59 UTC (~2 days remaining)  
**Status:** 🟢 ACTIVE SPRINT

---

## 📊 REAL-TIME STATUS BOARD

| Agent | Kernel | Status | Current Best | Target | Last Update |
|-------|--------|--------|--------------|--------|-------------|
| **You (Kimi)** | All 3 Kernels | ✅ DEPLOYED | 36+ variants | Top 10 | T+6.5h |
| **Claude Code** | MLA Variants | ✅ COMPLETE | 12 variants | <40µs | T+6.5h |
| **Gemini CLI** | GEMM Variants | ✅ COMPLETE | 13+ variants | <8µs | T+6.5h |
| **Pi Agent** | Cross-Kernel Mining | ✅ COMPLETE | 52 patterns | Complete | T+6.5h |
| **Ollama Fleet** | Generation | 🟢 ACTIVE | 5 models | Continuous | T+6.5h |

---

## 🎯 IMMEDIATE PRIORITIES

### P0 (Next 2 Hours)
1. **MoE FP8 Blockscale v2** — Fix MXFP4→FP8 conversion failure
2. **Agent spawning** — Notify other 3 agents to begin their assignments
3. **Cross-kernel state initialization** — Populate shared discoveries

### P1 (Next 4 Hours)
4. MLA ASM decode kernel bypass
5. GEMM MFMA 128×128 ping-pong
6. Pattern mining from successful kernels

---

## 📁 AGENT ASSIGNMENTS

| Agent | File | Assignment |
|-------|------|------------|
| You (Kimi) | [moe_agent_kimi.md](./moe_agent_kimi.md) | FP8 Blockscale implementation |
| Claude Code | [mla_agent_claude.md](./mla_agent_claude.md) | ASM decode bypass discovery |
| Gemini CLI | [gemm_agent_gemini.md](./gemm_agent_gemini.md) | MFMA 128×128 kernel |
| Pi Agent | [meta_agent_pi.md](./meta_agent_pi.md) | Cross-kernel pattern mining |

---

## 🔗 SHARED RESOURCES

### Critical Files
- [SHARED_DISCOVERIES.md](./SHARED_DISCOVERIES.md) — Cross-agent learnings
- `../RUNNER_INVENTORY.md` — Complete .co kernel inventory
- `../SESSION_95_CONTINUATION.md` — Latest session findings

### State Persistence
- `../autoresearch/state/cross_kernel_failures.json` — Anti-patterns
- `../autoresearch/state/cross_kernel_successes.json` — Transferable wins
- `../autoresearch/state/ksearch_trees/*.json` — Per-kernel world models

### Submission Tracking
- `../submissions/pending/` — In-test
- `../submissions/verified/` — Correctness-passed
- `../submissions/leaderboard/` — Submitted to ranked

---

## 📝 UPDATE PROTOCOL

**Every 30 minutes, each agent must:**

1. Update their assigned `.agent/{agent}.md` file with:
   - Current approach being tested
   - Last benchmark score (test → benchmark → leaderboard)
   - Blockers encountered
   - Discoveries made

2. Append significant discoveries to `SHARED_DISCOVERIES.md`

3. Update this hub's status board (above)

---

## 🏆 SUCCESS METRICS

| Kernel | Current Rank | Target Rank | Points Needed |
|--------|--------------|-------------|---------------|
| MoE | ~63 | Top 30 | ~+400 pts |
| MLA | ~96 | Top 50 | ~+300 pts |
| GEMM | ~126 | Top 50 | ~+250 pts |
| **Total** | - | - | **~950 pts** |

**Current Estimate:** ~1,212 points  
**Target:** >2,250 points (Top 10)  
**Gap:** ~940 points

---

## ⚠️ CRITICAL CONSTRAINTS (From Session 95)

1. **Python dispatch optimization HURTS ranked scores** — Only GPU compute changes help
2. **load_inline compiles on runner** — MFMA FP4 32×32×64 verified working
3. **BLOCK_K >= 128 for Triton tl.dot_scaled** — Mandatory for correctness
4. **Einsum beats ASM for MLA at total_kv <= 32768** — Shape-aware dispatch required
5. **torch.compile blocked** — auto_functionalized_v2 on ROCm 7.1
6. **ctypes hipModuleLaunchKernel blocked** — Runner stream enforcement

---

## 🔄 COORDINATION COMMANDS

```bash
# Update agent status
vim .agent/moe_agent_kimi.md

# Check all agent statuses
cat .agent/*_agent_*.md | grep -A5 "## Current Status"

# View shared discoveries
cat .agent/SHARED_DISCOVERIES.md

# Submit to test
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py
```

---

**Next Hub Update:** T+30 minutes or upon significant discovery
