# FLUME Journey Benchmark Platform — Project Plan

> **Status**: Active Development  
> **Start Date**: March 25, 2026  
> **Hardware**: AMD Ryzen AI MAX+ 395 (16C/32T Zen 5) + AMD Radeon 8060S (RDNA 3.5 iGPU)  
> **Memory Budget**: 80 GiB RAM (hard ceiling, leaving ~48GiB for OS + system)
> **Framework**: PyTorch 2.9.1+rocm6.3 (ROCm 6.3 for AMD Radeon 8060S) — note: PyTorch 2.11 has no ROCm wheel
> **Target**: Anthropic Research Engineer, Universes role

---

## Overview

**What**: A production-grade benchmark platform that trains RL agents to navigate the FLUME manifold (12D axiomatic state space), treating every agentic journey as an **Etheric Variant Oscillator (EVO)** — an exotic vacuum object with a full physics biography governed by TRIUNE SELF dynamics, Kordylewski swarm gravity, and HIHO stability physics.

**Why it matters**: No existing benchmark treats agent journeys as exotic vacuum objects. This is genuinely novel physics-inspired ML infrastructure that directly positions for Anthropic's Universes team ("build environments where models learn to navigate ambiguity, handle interruptions, maintain context over extended interactions, and exercise judgment in open-ended scenarios").

**Output**: Both a research dataset (arXiv + HuggingFace dataset card) and a benchmark harness (LM Evaluation Harness-style).

---

## Memory Architecture (80GB Ceiling)

| Component | Max RAM | Strategy |
|-----------|---------|----------|
| PyTorch model (TRIUNEPolicy + VAE) | 2 GB | Load once, `torch.compile` |
| PPO episode buffer (50 episodes × 1000 steps) | 8 GB | 32-bit floats |
| EVO trajectory storage (20 active) | 6 GB | Memmap to `data/evo_trajectories/` |
| FlumeNavEnv + HIHOUnifiedEngine | 4 GB | Clear after each episode |
| HuggingFace export (staging) | 4 GB | Stream to disk |
| Training headroom | 56 GB | torch.compile + ZeRO offload |
| System + OS + other processes | 48 GB | Hard ceiling |

---

## System Architecture

```
PyTorch 2.11 (ROCm) + AMD Radeon 8060S (RDNA 3.5)
128 GiB LPDDR5X-8000 Unified Memory (UMA)

┌─────────────────────────────────────────────────────────────────────────────┐
│                          TASK GENERATION LAYER                              │
│  PRIME Skills (180+) ──► TaskGenerator (test oracle)                      │
│  5 archetypes × 4 difficulty levels = 20 TaskSpecs                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUME NAV ENV LAYER                                 │
│  FlumeNavEnv + HIHOUnifiedEngine (full physics)                            │
│  State: 12D Axiomatic (Space/Field/Control/Precipitation Fabrics)          │
│  TRIUNE SELF states: Doer(12D) / Thinker(512D) / Knower(2048D)           │
│  Interruption injection, context injection, open-ended mode                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐       ┌─────────────────────────────────────┐
│     SWARM ADVISOR          │       │      TRIUNE NEURAL POLICY            │
│   (Cohezion multi-agent)   │       │         (PPO, PyTorch 2.11)         │
│  TeamOrchestrator           │       │  Policy: Knower→Thinker→Doer (12D)  │
│  deepseek-r1:70b          │       │  torch.compile on RDNA 3.5          │
│  Provides 2048D Knower goal│       │  PPO clip ε=0.2, 4 epochs, lr=3e-4 │
└─────────────────────────────┘       └─────────────────────────────────────┘
                    │                               │
                    │         ┌─────────────────────┘
                    │         ▼
                    │ ┌─────────────────────────────────────────────────────┐
                    │ │                  EVAL PIPELINE                       │
                    │ │  RalphLoop + git + EVAL_PROGRESS.md                 │
                    │ │  oracle.validate(EVO) → pass/fail per episode         │
                    │ └─────────────────────────────────────────────────────┘
                    │         │
                    └─────────┤
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BENCHMARK + SCORECARD LAYER                            │
│  6 agentic metrics (EVO Coherence Amplitude, Phase Locking, etc.)          │
│  Bootstrap 95% CIs, Mann-Whitney U, Bonferroni correction                  │
│  CapabilityScorecard: radar chart, longitudinal tracking                    │
│  HuggingFace export: research dataset + benchmark harness                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Task Archetypes

| # | Archetype | Description | Swarm Advisor Utility |
|---|-----------|-------------|----------------------|
| 1 | HIHO Basin Navigation | Start far from HIHO_Origin, navigate to stability well | Medium |
| 2 | TRIUNE Balance | Maintain Doer/Thinker/Knower equilibrium | High |
| 3 | Interruption Recovery | Pause at interruption point, recover SPIN coherence | High |
| 4 | Exotic Charge Tolerance | Navigate with high exotic_charge_density without collapse | Medium |
| 5 | Kordylewski Orbit | Maintain orbit around L4/L5 memory cloud under swarm gravity | Very High |

---

## Metric Families

| Metric | Unit | Measurement |
|--------|------|-------------|
| EVO Coherence Amplitude | [0, 1] | Peak HIHO coherence reached during journey |
| Phase Locking Rate | [0, 1] | % steps where SPIN coherence aligned |
| Exotic Charge Lifetime | steps | Steps with exotic_charge_density < 0.95 before collapse |
| Kordylewski Orbit Quality | [0, 1] | 1 - (distance_variance / baseline_variance) |
| TRIUNE Balance Index | [0, 1] | 1 - std(doer/thinker/knower activation) |
| Recovery Basin Radius | distance | Max HIHO distance from which recovery succeeds |

---

## Phases

| Phase | Name | Days | Agent |
|-------|------|------|-------|
| 0 | PyTorch 2.11 + ROCm Foundation | 0.5 | Pipeline & Infrastructure |
| 1 | EVO (Etheric Variant Oscillator) Model | 2.0 | Research Architect + RL Env Specialist |
| 2 | TaskGenerator + TRIUNE Task Specs | 2.0 | RL Environment Specialist |
| 3 | FlumeNavEnv + HIHOUnifiedEngine | 2.0 | RL Environment Specialist |
| 4 | TRIUNE PPO Trainer | 2.0 | Pipeline & Infrastructure |
| 5 | Agentic Benchmark Metrics | 3.0 | Benchmark Engineer |
| 6 | EvalPipeline + Long-Running Patterns | 2.0 | Pipeline & Infrastructure |
| 7 | CapabilityScorecard + EVO Viz + HuggingFace Export | 2.0 | Research Architect + Pipeline & Infrastructure |

**Total: ~15.5 days**

---

## Documentation Structure

```
docs/
├── README.md                           # Top-level: overview, quickstart
├── architecture/
│   ├── FLUME_MANIFOLD.md              # 12D axiomatic, TRIUNE SELF, fabrics
│   ├── EVO_MODEL.md                   # Etheric Variant Oscillator formalization
│   ├── BENCHMARK_HARNESS.md           # LM Evaluation Harness-style API
│   └── RL_TRAINER.md                  # PPO + TRIUNE policy architecture
├── phases/
│   ├── PHASE_0_PYTORCH.md
│   ├── PHASE_1_EVO.md
│   ├── PHASE_2_TASKGEN.md
│   ├── PHASE_3_ENV.md
│   ├── PHASE_4_PPO.md
│   ├── PHASE_5_METRICS.md
│   ├── PHASE_6_PIPELINE.md
│   └── PHASE_7_SCORECARD.md
├── benchmark/
│   ├── api_reference.md
│   ├── task_registry.md
│   └── metric_definitions.md
└── publications/
    └── EVO_BENCHMARK_PAPER.md        # arXiv-ready paper outline
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PyTorch version | 2.9.1+rocm6.3 | Latest ROCm wheel available; 2.11 has no ROCm build |
| RL framework | Pure PyTorch PPO | AMD RDNA 3.5 iGPU compatible, transparent, no CUDA lock-in |
| Memory management | .npy for EVO trajectories | 80GB ceiling, prevents OOM on long episodes |
| Swarm advisor | Every episode start | Enables direct comparison (swarm vs. self-supervised) |
| Checkpoint naming | Hybrid: `ppo_ep{NNNN}_coh{X.XX}.pt` + manifest | Episode count + capability score, no conflicts |
| arXiv vs. benchmark | Benchmark harness first | Engineered artifact before narrative paper |
| TRIUNE policy | 3-tier (Knower→Thinker→Doer) | Matches existing FLUME architecture |

---

## TDD + Adversarial Review Protocol

Every phase follows:
1. Write tests first (adversarial review of interface contracts)
2. Implement to pass tests
3. Adversarial review: `CompoundExecutor` self-improvement check
4. Refine based on review
5. Commit

---

## Open Questions (Resolved)

| # | Question | Decision |
|---|----------|----------|
| 1 | Checkpoint naming | Hybrid: `ppo_ep{NNNN}_coh{X.XX}.pt` + manifest |
| 2 | Swarm advisor frequency | Every episode start (enables direct comparison) |
| 3 | Memory budget | 80GB RAM ceiling; EVO trajectories memmap'd to disk |
| 4 | arXiv vs. benchmark first | Benchmark harness API first, arXiv outline second |

---

*Last updated: March 25, 2026*
