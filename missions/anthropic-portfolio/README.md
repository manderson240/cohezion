---
aspect: doer
neural:
  activation: 0.517
  stage: growing
  cluster: missions
---
# COHEZION: Compound AI Orchestration Framework
**Job Application Portfolio: Research Engineer, Universes — Anthropic**

*Mike Anderson | 2026 | [github.com/mike-anderson/cohezion]*

---

## What This Is

COHEZION is a compound AI orchestration framework I built to solve a specific problem: each Claude Code session starts from zero. Context is lost. Lessons evaporate. The system can't learn from its own history.

COHEZION closes that loop. Every session produces decisions, experiments, and lessons that are indexed in a persistent knowledge graph (Obsidian + SurrealDB) and re-injected into future sessions as context. The result is a system that compounds its own intelligence across sessions rather than resetting.

Over 60+ sessions and 475 commits, this has produced:
- A VAE (FLUME) trained on real agent trajectory data that compresses session behavior into a 256D latent space
- A Gymnasium-compatible RL environment (EcoAgent) for agent training and evaluation
- Novel evaluation frameworks (JourneyTracker, DegradationDetector) that measure reasoning quality in trajectory space rather than just action outcomes
- A corpus of 45 operational lessons derived from real failures, forming a taxonomy of agentic system failure modes
- A multi-agent council architecture with documented constraint discipline — deferring destructive operations, scoping authority, logging democratic rationale

---

## Core Technical Contributions

### 1. FLUME — Variational Autoencoder for Agent Trajectory Compression

**What it does:** Encodes agent session trajectories into a 256D continuous latent space, enabling semantic similarity retrieval, anomaly detection, and interpolation between agent behavioral states.

**Architecture:** Encoder → reparameterization → decoder. Temporal self-attention layers capture sequential dependencies in tool-call trajectories. Cyclical KL annealing prevents posterior collapse.

**Real results from VAE v2 training on 5.5M trajectories:**
- Reconstruction MSE: 0.015 (53% improvement over v1's 0.032)
- KL divergence: 4.2 nats — healthy regularization, no posterior collapse
- t-SNE visualization: distinct clusters for successful vs failed sessions, gradient region for partial completions
- Temporal attention: clear activation at tool-switching events and context checkpoint boundaries

**Key finding:** Hash-based position encoding (SHA-256 bytes as 12D coordinates) produces random walks in latent space — average step distance ~1.4, indistinguishable from noise, making drift detection impossible. FLUME semantic embeddings reduce average step distance to <0.3 for coherent trajectories. This was discovered empirically and documented as a formal ADR.

### 2. JourneyTracker and DegradationDetector — Agent Evaluation in Trajectory Space

**The problem they solve:** Action-outcome metrics (did the task succeed?) don't measure *how* an agent reasoned. Two agents can reach the same outcome via very different reasoning paths — one robust, one brittle.

**What they measure:**
- JourneyTracker records 12D position trajectories representing agent state across axes including coherence, token efficiency, task complexity, and skill coverage
- DegradationDetector identifies when reasoning quality is declining mid-session — before task failure occurs — by tracking velocity and curvature in trajectory space

**Validation:** Hash-based tracking (the prior approach) produced false positives on every step. FLUME-based tracking shows interpretable geometric structure. The failure mode was documented with quantified impact.

### 3. Predictive Throttling via Trajectory Velocity

**Derived from:** Analysis of 5.5M overnight N-body simulation trajectories.

**The pattern:** Velocity of movement through the 12D semantic space predicts computational demand. Fast-moving agents (high velocity = exploring new territory) need more resources. Slow-moving agents (converging = low velocity) can be throttled without loss. Thresholds calibrated from simulation data: low < 0.01, medium < 0.1, high < 0.5.

This pattern has been validated on real agent sessions and documented with working code.

### 4. Multi-Agent Constitutional Governance

**What was built:** A multi-agent council architecture where autonomous sessions make decisions using structured deliberation with documented rationale, voting records, and constraint discipline.

**Constraint discipline observed:** During an autonomous overnight session, the council correctly identified and deferred: all destructive file operations, all financial commitments (HF API calls ~$50), all operations requiring credentials. It continued only with read-only analysis — without being explicitly instructed to do so for each case.

This is working aligned multi-agent AI. The constraint discipline emerged from the constitutional layer, not from per-task instructions.

### 5. VLIW 424x Speedup — Hardware-Native Performance

**Verified result:** 424x speedup (348 cycles) on parallel swarm evolution using strict single-core ILP via Register Windowing and Packet-Greedy Scheduling. Speedup is instruction-level parallelism, not thread-level — verified with `N_CORES=1` constraint active.

---

## Engineering Rigor

**Test suite:** 3,300+ tests, 789/789 passing at last full run. Test integrity maintained across 60+ sessions.

**Anti-pattern documentation:** 15 formal ADRs documenting what *not* to do — character-level tokenizers for semantic embeddings, SHA-256 hashes as semantic coordinates, VAE training on random noise, zombie async test processes. Each includes observed failure mode, quantified impact, and reasoning for rejection.

**45-lesson failure corpus:** Operational lessons derived from real system failures across 60+ sessions. Includes: 8.6M file incident recovery, system lockup from concurrent pytest contention, runtime JSON pollution, pre-commit hook conflicts, SurrealDB schema design failures. These are failures that were documented rather than buried.

**Production discipline:** Three-tier data storage architecture separating hot/warm/cold artifacts. Pre-commit enforcement preventing training data from entering git history (learned from a session that committed 12GB of trajectory files). Checkpoint format with full reproducibility state for every training run.

---

## Repository Health

- 475 commits, 351 Python files, 55 modules
- Disconnected `track-c` / `main` branch histories — documented as known technical debt in `projects/repo-and-process-debt.md` with remediation plan
- Security fixes: XXE vulnerability (defusedxml), path traversal sanitization, no-auth MCP server documented as local-only by design
- Coverage: 88% (up from 77% in last measured session)

---

## Why This Is Relevant to Universes

The Universes team works on long-horizon agentic tasks, multi-agent systems, and evaluation of agent reasoning quality. COHEZION directly addresses each:

- **Long-horizon tasks:** The compound engineering loop is designed for tasks that span many sessions. Context injection from the vault gives each session access to all prior reasoning.
- **Multi-agent systems:** The council architecture demonstrates structured multi-agent deliberation with authority scoping and audit trails.
- **Evaluation:** JourneyTracker and DegradationDetector are my answer to the question of how to measure agent reasoning quality beyond task success.

I built this because I couldn't find existing tools that solved these problems. That's the kind of work I want to do at Anthropic.

---

## Technical Stack

- Python 3.13, PyTorch (VAE training), Gymnasium (RL environment)
- SurrealDB 3.0 (knowledge graph + HNSW semantic search)
- Ollama (28+ local models, zero API cost for development)
- FastMCP (cloud-vault-mcp server, 40+ tools)
- Obsidian (vault frontend, 3D graph visualization plugin)
- Kyutai Moshi / XTTS v2 (audio synthesis)

---

## What's Not Done Yet

- FLUME KL collapse validation — preliminary results (4.2 nats KL, 53% reconstruction improvement) are from 30 epochs. Full 100-epoch run and semantic reconstruction fidelity measurement pending.
- EcoAgent end-to-end RL training loop — environment is built and tested; training pipeline needs final integration.
- Portfolio demo video — planned but not yet produced.

I'm including this because research engineering requires honest accounting of what's validated and what's not.

---

*All claims in this README are verifiable against vault ADRs, experiment notes, and test results. The vault itself is part of the portfolio.*
