# Pilot Architectural Patterns - Inspiration for COHEZION

**Source**: [Claude Pilot](https://github.com/maxritter/claude-pilot) by Max Ritter
**License**: Proprietary source-available (see LICENSE in their repo)
**Our Approach**: We learned from these patterns but implement our own versions from scratch to respect their license

---

## Key Patterns Learned

### 1. Hooks Pipeline Architecture

**Pilot's Design:**
- 6 lifecycle events: SessionStart, SessionEnd, PreToolUse, PostToolUse, ContextWarning, ContextClear
- 15 hooks across these events
- Blocking vs non-blocking hook execution
- Language-specific quality enforcement (ruff/basedpyright for Python, ESLint/Prettier for TypeScript)

**COHEZION Application:**
- Integrate hooks with JourneyTracker (12D trajectory recording)
- Connect to GlobalMetricsAggregator for compound scoring
- Vault-backed hook persistence for cross-session learning
- HIHO-aware hook execution (maintain 0.5 coherence during enforcement)

**Why This Matters:**
Quality enforcement at the lifecycle level prevents technical debt accumulation and enables compound engineering (every feature makes future features easier).

---

### 2. Context Preservation Across Sessions

**Pilot's Design:**
- Pre-compaction hooks capture state before context clear
- Post-compaction hooks restore state in new session
- Session-specific continuation files
- Support for parallel sessions with isolated state

**COHEZION Application:**
- Extend SessionPersistence with pre-clear snapshots
- Integrate with vault for semantic context retrieval
- Use FLUME VAE to compress context into 12D manifold representation
- Enable HIHO stability maintenance across session boundaries

**Why This Matters:**
Enables "Endless Mode" for compound engineering loops that span multiple context windows without losing trajectory coherence.

---

### 3. Intelligence Routing Strategy

**Pilot's Design:**
- Opus for planning and verification (reasoning-heavy, higher quality)
- Sonnet for implementation (spec-driven execution, faster)
- Strategic model deployment based on task cognitive load

**COHEZION Application:**
- Extend CostAwareRouter with task classification
- Route by cognitive complexity, not just token cost
- Integrate with ModelQualityClassifier for confidence scoring
- Budget-aware routing that balances quality and cost

**Why This Matters:**
Optimal resource allocation - premium models for high-stakes decisions, economy models for well-specified execution. Aligns with Expert Domain Lattice routing.

---

### 4. Worktree Isolation Workflow

**Pilot's Design:**
- Each session creates isolated git worktree
- Safe experimentation without polluting main branch
- Automatic cleanup on session completion
- Support for parallel sessions

**COHEZION Application:**
- Already using worktrees in `/tmp/cohezion_swarm/` via WorktreeOrchestrator
- Enhance with automatic artifact archival before cleanup
- Integrate with JourneyTracker for worktree-scoped trajectory analysis
- Vault-backed checkpointing for recoverable experimentation

**Why This Matters:**
Prevents repository corruption during autonomous agent swarms. Enables safe "what-if" exploration with deterministic rollback.

---

### 5. Quality Enforcement Layer

**Pilot's Design:**
- Auto-lint, format, and type-check on every file edit
- Language-specific tooling integration
- Blocking hooks prevent low-quality commits
- Real-time feedback loop

**COHEZION Application:**
- PostToolUse hooks for ruff/basedpyright enforcement
- Integration with DegradationDetector (catch quality drift)
- Coherence-aware linting (skip enforcement when coherence < 0.5)
- Vault-backed quality metrics for compound improvement tracking

**Why This Matters:**
Enforced quality baseline prevents "code rot" in autonomous agent output. Enables trust in swarm-generated code.

---

### 6. Command Pattern Abstractions

**Pilot's Design:**
- `/spec` - Spec-driven development with verification
- `/sync` - Codebase learning and standards discovery
- `/learn` - Knowledge extraction as shareable skills
- `/vault` - Team asset distribution

**COHEZION Application:**
- Already have compound engineering loop with SkillRefiner
- Extend with explicit `/learn` skill for session retrospection
- Vault integration for team knowledge sharing
- `/spec` pattern maps to our plan-execute-verify loop

**Why This Matters:**
Compound engineering requires explicit knowledge capture. These command patterns formalize the learning loop.

---

## Implementation Principles

To respect Pilot's proprietary license while learning from their architecture:

1. **No Code Copying**: Implement patterns from scratch using COHEZION primitives
2. **COHEZION-Native Design**: Integrate with JourneyTracker, FLUME, HIHO, Expert Domain Lattice
3. **Clear Attribution**: Document Pilot as inspiration source in all related code
4. **Independent Innovation**: Add COHEZION-specific enhancements (12D trajectories, vault-backed learning, HIHO stability)

---

## License Compliance

Pilot's license prohibits:
- Redistribution of their software
- Creating derivative works for others
- Competing using their codebase
- Providing hosted access to their features

Our approach:
- ✅ Learn from architectural patterns
- ✅ Implement our own versions from scratch
- ✅ Give clear attribution
- ✅ Add COHEZION-specific innovations
- ❌ Do NOT copy their code
- ❌ Do NOT create derivative work

---

## Next Steps

See tasks in COHEZION task tracker:
- Task 1: ✅ Document patterns (this file)
- Task 2: Implement hooks pipeline
- Task 3: Enhance SessionPersistence
- Task 4: Extend CostAwareRouter
- Task 5: Add attribution to README

---

**Last Updated**: 2026-02-20
**Reference**: https://github.com/maxritter/claude-pilot
**License**: Proprietary (respect their terms)
