# Cohezion Project Memory Index

*System of Record: Dual-Store (SurrealDB port 8001 + Obsidian Vault `~/vaults/cohezion-vault/`)*

## Core Topic Memory
- [SurrealDB Port 8001](.omg/memory/surrealdb-port8001.md) | `surreal: learning` (647 records) | direct HTTP fallback enabled
- [Kaggle Active Tracks](.omg/memory/kaggle-active-tracks.md) | `competitions`: ARC-AGI-2, ARC-AGI-3, RSNA Knee, CASMI26, NFL BDB 2027, Gemma-4 Dev Agent
- [Strix Halo Fleet Discipline](.omg/memory/strix-halo-fleet-discipline.md) | `hardware`: 128GB UMA, 25GB RAM floor, 50GB GTT ceiling, FleetLock
- [AutoHarness Policy](.omg/memory/autoharness-policy.md) | `verification`: AST verifier, 0ms LLM bypass, continuous clearance margins $h(x)$, efference copy residual gating
- [Proprioceptive Cybernetics](.omg/memory/proprioceptive-cybernetics.md) | `cybernetics`: Somatosensory mechanoreceptors, muscle spindles, GTO tension inhibition, crossing-time rate reflex ($t_{\text{cross}}$)
- [Deterministic Idempotence](.omg/memory/deterministic-idempotence.md) | `verification`: Mathematical proof $\mathcal{T}(\mathcal{T}(x)) = \mathcal{T}(x)$, 6-domain empirical verification, bitwise SHA-256 identity
- [AMD XDNA 2 NPU Acceleration](.omg/memory/npu-xdna2-acceleration.md) | `hardware`: FastFlowLM v1.0.8 on port 8005, 170x latency speedup (9.7s–24.5s), 0 MB UMA consumption, <2W power
- [2026 Agentic Systems Roadmap](.omg/memory/agentic-roadmap-2026.md) | `architecture`: 4-level failure inversion, typed swarm handoff contracts (`TaskHandoffContract`), debate-critique resolution, circuit breakers

## Modular Rule Packs
- [Tests Required](.omg/rules/tests-required.md) | Triggers on behavior code changes
- [Migration Safety](.omg/rules/migration-safety.md) | Triggers on schema, contract, or database migrations
- [Security Review](.omg/rules/security-review.md) | Triggers on auth, tokens, secrets, or permission surfaces
- [Kaggle Discipline](.omg/rules/kaggle-discipline.md) | Triggers on Kaggle competition code, kernels, and submissions
- [Hardware Safety](.omg/rules/hardware-safety.md) | Triggers on local model execution and memory allocation
- [Subagent Delegation](.omg/rules/subagent-delegation.md) | Triggers on complex workflows, local inference, and competition ascents
- [Dual-Store Persistence](.omg/rules/dual-store-persistence.md) | Triggers on learning cycles and retrospective extraction

## Verification Hooks & Guardrails
- Pre-commit Hook: `scripts/hooks/pre-commit.py` (gates formatting, lint ratchets, forbidden subgraph patterns, and contract integrity)
- Hook State & Derived Signals: `.omg/state/hooks.json` (11 derived signals including somatic reflex, rate-damping, typed contracts, idempotence gate)
- Validation Status: `.omg/state/hooks-validation.md` (PASS, 0 critical, safe-to-run YES)
