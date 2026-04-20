---
title: "Cohezion Platform Overview"
date: 2026-03-05
tags: [concept, cohezion, platform, compound-engineering, spine]
status: active
aspect: knower
neural:
  activation: 0.99
  stage: mature
  synapse_in: 4
  synapse_out: 10
---

# Cohezion Platform Overview

**Read this first.** This note is the entry point for any agent or human trying to understand what Cohezion is and how it works. It is intentionally plain — no internal vocabulary, no jargon that requires prior context.

---

## The Problem Cohezion Solves

Every Claude Code session starts from zero. Prior decisions are lost. Lessons evaporate. The system can't learn from its own history. This makes long-horizon engineering work expensive — each session spends 30-60 minutes re-orienting before doing real work.

Cohezion closes that loop. Every session produces structured outputs (decisions, experiments, patterns, lessons) that are indexed in a persistent knowledge graph and injected into future sessions as context. The result is a system that compounds its intelligence across sessions rather than resetting.

---

## What Was Built

Cohezion is four things working together:

**1. The Vault** — an Obsidian knowledge base with 690+ notes organized into concepts, decisions, experiments, patterns, and lessons. This is the long-term memory. Every significant choice, failure, and discovery goes here. The vault is the source of truth.

**2. FLUME** — a variational autoencoder trained on 5.5M agent session trajectories. It compresses session behavior into a 256D continuous latent space. The latent space enables: retrieving semantically similar prior sessions before starting new work, detecting anomalous sessions via reconstruction error, and interpolating between behavioral states.

**3. EcoAgent** — a Gymnasium-compatible RL environment for agent training and evaluation. Provides standardized observation spaces, action spaces, and reward signals for training agents on compound engineering tasks.

**4. The MCP Server** (cloud-vault-mcp) — a FastMCP server with 40+ tools that bridges Claude Code sessions to the vault, SurrealDB graph, and Ollama model inference. Sessions interact with the knowledge graph through this server.

---

## Numbers

| Metric | Value |
|---|---|
| Sessions completed | 60+ |
| Commits | 475 |
| Python files | 351 |
| Modules | 55 |
| Tests | 3,300+ (789/789 passing at last full run) |
| Vault notes | 690+ |
| Papers indexed | 102 |
| Concepts | 317 |
| Graph links | 1,458 |
| Lessons | 45 |
| FLUME training trajectories | 5.5M |
| VAE v2 reconstruction improvement | 53% over v1 |
| VLIW speedup (verified) | 424x |

---

## The Key Technical Findings

**FLUME latent space is semantically meaningful.** Hash-based position encoding (SHA-256 bytes as coordinates) was tried first and failed — trajectories showed no continuity, drift detection produced false positives on every step. FLUME embeddings reduced average step distance from ~1.4 (random walk) to <0.3 for coherent trajectories. This was discovered empirically and is documented as ADR `decisions/2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories.md`.

**Trajectory velocity predicts resource demand.** Analysis of 5.5M simulation trajectories revealed that velocity of movement through semantic space correlates with computational demand. Fast-moving agents (exploring) need more resources; slow-moving agents (converging) can be throttled. This became the predictive throttling pattern, calibrated from simulation data.

**Cyclical KL annealing prevents latent collapse.** V1 FLUME suffered posterior collapse — KL divergence dropped to near zero, meaning the latent space was bypassed entirely. V2 introduced cyclical β annealing (Fu et al. 2019) and achieved stable KL at 4.2 nats with 53% reconstruction improvement.

**The 45-lesson corpus is the most operationally valuable asset.** Each lesson was learned by breaking the system: 8.6M accidental file generation, concurrent pytest contention, runtime JSON pollution, zombie async processes, SHA-256 as semantic embedding. Together they form an empirical taxonomy of agentic system failure modes.

---

## Current Status (2026-03-05)

**Working:**
- Vault knowledge graph with 690 notes, 1,458 links
- MCP server with 40+ tools, deployed and accessible
- FLUME VAE v2 (preliminary results: 30 epochs, healthy KL)
- Multi-agent council with constitutional constraint discipline
- 3,300+ tests, 789/789 passing
- VLIW 424x speedup (verified)
- Predictive throttling pattern (validated on real sessions)

**In progress:**
- FLUME full validation (100-epoch run, semantic fidelity measurement pending)
- EcoAgent end-to-end RL training loop
- Portfolio assets and demo video
- `specs/` directory for system definitions (skills, agents, MCP servers)

**Known debt:**
- Disconnected `track-c` / `main` branch histories (documented in `projects/repo-and-process-debt.md`)
- 89% of researched papers not yet promoted to full vault notes
- Sensory workers (diagram, video, voice) are mock implementations only
- SurrealDB sync is manual — no real-time sync from vault writes yet

---

## Directory Map for Agents

| Need | Go Here |
|---|---|
| Understand a concept or technique | `concepts/` |
| Find a past architectural decision | `decisions/` |
| Find what was tried and what happened | `experiments/` |
| Find reusable solutions with code | `patterns/` |
| Find hard-won operational lessons | `lessons/` |
| Find current project status | `projects/` |
| Drop raw ideas for later triage | `inbox/` |
| Find today's session context | `daily/` |

---

## What to Load at Session Start

A productive session starts by reading:
1. This note (done)
2. `HANDOFF.md` — last committed session state
3. `daily/YYYY-MM-DD-*.md` — most recent session note
4. `lessons/` — high-severity lessons relevant to today's task

With that context, a session can skip 30-60 minutes of re-orientation.

---

## Related

- [[VAULT_MANIFEST]] — machine-readable vault map; read at session start to load directory routing rules and entry points
- [[FLUME-Architecture]] — full VAE architecture and experimental results
- [[compound-engineering]] — the methodology this platform implements
- [[agent-journey-tracking]] — how session trajectories are captured
- [[experience-feedback-loop]] — how captured experience feeds back into training
- [[cloud-vault-mcp]] — the MCP server bridging sessions to the knowledge graph
- [[reinforcement-learning]] — EcoAgent environment design
- [[MOC-compound-engineering]] — map of content for compound engineering topics
- [[MOC-agentic-ai]] — map of content for agentic AI topics
- [[2026-03-05-vault-surrealdb-architecture]] — planned real-time sync architecture
- [[2026-03-04-vault-assessment-v3]] — current vault state assessment
- [[2026-03-03-vault-as-platform-memory-recommendations]] — six recommendations for strengthening vault-as-platform-memory: platform spine, machine-readable lessons, link types, session memory protocol
- [[12D-Manifold]] — the 12-dimensional semantic space providing the quantitative foundation for vault visualization and analytics
- [[12D-Projection]] — the projection layer that maps FLUME's 256D latent space to 12 interpretable dimensions for the Observatory UI
