---
name: rah-module-prd
description: Product Requirements Document for Resilience & Autonomic Healing (RAH) module
version: 1.0.0
status: in-progress
owner: mike-anderson
team: cohezion-resilience
date: 2026-03-08
---

# PRD: Resilience & Autonomic Healing (RAH)

## 1. Executive Summary

The **Resilience & Autonomic Healing (RAH)** module implements a proactive self-healing layer for the Cohezion swarm. By leveraging a **MAPE-K control loop**, RAH monitors system vitals via Gateway 33 (ResourceMonitor) and executes autonomic healing strategies such as model swapping, context reduction, and service restarts to ensure 99.9% agent availability and prevent system lockups.

### Key Metrics
- **90% Reduction** in Mean Time to Resolution (MTTR) for system pressure issues.
- **Zero Lockups** during multi-agent high-concurrency tasks.
- **<1% Overhead** on total system resources.

---

## 2. Problem Statement

### Current Pain Points
1. **Reactive Stability**: The current `ResourceMonitor` is primarily reactive, throttling tasks only after pressure is detected.
2. **Manual Intervention**: Severe memory leaks or model-induced VRAM pressure often require manual process killing.
3. **Context Bloat**: Agents don't autonomously reduce their context windows when the system is under pressure, leading to exponential latency increases.

---

## 3. Solution Overview

### RAH Autonomic Architecture

RAH implements the classic autonomic computing loop:
- **Monitor**: Continuous ingestion of vitals from `ResourceMonitor`.
- **Analyze**: Semantic interpretation of system state (Normal, High Pressure, Critical, Emergency).
- **Plan**: Selection of optimal `HealingStrategy` based on system history and hardware profile.
- **Execute**: Triggering actions like `MODEL_SWAP` or `SYSTEM_RESTART`.
- **Knowledge**: Using SurrealDB to store 'Truth Anchors' and learned effectiveness of past actions.

---

## 4. User Stories

#### As an Orchestrator
- **I want** the system to autonomously swap my primary reasoning model to a smaller one if VRAM pressure exceeds 85%.
- **So that** my long-running research tasks don't fail due to OOM (Out of Memory) errors.

#### As a Developer
- **I want** a standardized interface for adding new healing strategies.
- **So that** I can implement custom recovery logic for specific research simulations.

---

## 5. Functional Requirements

### 5.1 Autonomic Manager (MAPE-K)
- **FR-1.1**: Continuous 10s monitoring loop.
- **FR-1.2**: Tiered analysis logic (Tier 1: Swap, Tier 2: Reduce, Tier 3: Restart).
- **FR-1.3**: Implementation of a 5-minute cooldown between healing actions to prevent oscillation.

### 5.2 Healing Strategies
- **FR-2.1 (ModelSwap)**: Unload heavy models and trigger fallback to SLMs (Small Language Models).
- **FR-2.2 (ContextReduction)**: Signal agents to reduce context by a specified factor.
- **FR-2.3 (SystemRestart)**: Gracefully stop and restart Ollama/SurrealDB services.

---

## 6. Technical Architecture

### System Components
| Component | Responsibility |
|-----------|----------------|
| `ResourceMonitor` | Source of truth for CPU/RAM/VRAM/DDR5 vitals. |
| `AutonomicManager` | Orchestrates the MAPE-K loop. |
| `StrategyEngine` | Repository of executable `HealingStrategy` objects. |
| `SurrealDB` | Persistence for learnings and state vectors. |

---

## 7. Implementation Roadmap

### Phase 1: Core Loop (Today)
- [x] Implementation of `strategies.py`.
- [x] Implementation of `manager.py`.
- [ ] Integration test with simulated pressure.

### Phase 2: Knowledge Integration
- [ ] Connect `AutonomicManager` to `SurrealDB` for decision persistence.
- [ ] Implement 'Truth Anchor' grounding for AMD Ryzen AI MAX+.

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-08
**Status**: Active
