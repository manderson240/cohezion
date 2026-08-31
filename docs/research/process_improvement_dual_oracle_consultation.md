# Comprehensive Process Improvement Blueprint (Dual-Oracle Synthesis)

This blueprint integrates high-leverage process improvements from both **`deepseek-v4-pro:cloud`** and **Claude CLI** for sovereign swarm engineering on Framework Desktop 16 / AMD Strix Halo.

---

## 1. Core Paradigm: From "Curated Lists" to "Discovered Ground-Truth"

> **Key Insight**: *An unlanded branch, a phantom invariant, and an unwired skill are all the exact same defect in different coordinate systems: **a claim recorded in a place nothing executes.** Curated lists decay at the speed of development; discovered scans enforce reality continuously.*

---

## 2. The 4 Cross-Cutting Action Pillars

### 1) Continuous Branch Landing & Dormancy Debt
- **Automated Ancestry Auditing (`--is-ancestor`)**:
  - Replace manual tracking with an automated scheduled sweep: `git merge-base --is-ancestor <branch> main`.
  - Automatically publish all verified-unlanded branches to the Kanban board and trigger AutoMerge landing trains.
- **Discovered Dormancy Scanning (`dormancy_scan.py`)**:
  - Transition `dormancy_scan.py` from a hand-curated allowlist to dynamic AST symbol discovery: flag any public symbol with 0 active non-test consumers.

### 2) Zero-Friction Test Automation & AutoHarness Rigor
- **Phantom Invariant Linter**:
  - Parse every `### <ID>:` block in `harness.md` and mechanically assert that each symbol and test path resolves in `src/` and `tests/`.
- **Consumption Meta-Invariant**:
  - Reject harness entries whose only evidence is `hasattr` or `inspect.signature`. Require active execution/neutralization tests.
- **Durable Artifact Storage (Eliminate `$TMPDIR` / tmpfs Loss)**:
  - Default all AutoHarness and swarm benchmark outputs to durable storage (`~/vaults/cohezion-vault/swarm-runs/<lane>/`) to prevent loss on session restart.

### 3) Real-Time Profiling & Silicon Admittance with TraceLens
- **Register & Wire AMD TraceLens**:
  - Wire `tracelens-analysis-orchestrator` directly into `src/cohezion/registry/skill_registry.json`.
- **Profile UMA Memory Admittance & Bus Contention**:
  - Sample `/sys/class/kfd` topology and GTT residency to prevent GTT/TTM overcommit before launching heavy local swarms.
- **Measure True Fixed-Cost Tier Latencies**:
  - Use TraceLens CPU-idle and compute-kernel profilers to break down fixed NPU dispatch overhead vs. KV-cache allocation.

### 4) Human-Agent Symbiosis & High-Leverage Direction
- **Positive Verdict Tokens from All Review Lanes**:
  - Enforce explicit `VERDICT: PASS | FAIL | INCONCLUSIVE` tokens so silent failures or restricted subagents never count as approvals.
- **State-Diff Kanban Reporting**:
  - Remove the human from status polling. Swarms push deltas (unlanded verified work, dormancy drifts, test regressions) directly to the Kanban board.
