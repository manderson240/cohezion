---
title: Agent Journey Tracking
date: 2026-02-23
tags: [agent-workflow, observability, compound-engineering, agentic-ai]
related_concepts: [experience-feedback-loop, compound-engineering, non-blocking-observability, universe-simulation, agent-architecture]
status: active
aspect: knower
neural:
  activation: 0.92
  stage: mature
  synapse_in: 26
  synapse_out: 25
---

# Agent Journey Tracking

Agent journey tracking is the practice of recording the full execution trace of an agent session — every task attempted, tool call made, decision taken, and output produced — so the session can be analyzed retrospectively and its learnings fed back into future sessions. In Cohezion, this is implemented through the `JourneyTracker` component, which records 12-dimensional position data representing the agent's location in the compound learning space.

Each execution step is logged as a state transition: the input, the action taken, the result, and the coherence score after the action. This trajectory data serves two purposes: real-time anomaly detection (identifying coherence collapse or drift mid-session) and post-session retrospection (extracting patterns and lessons for skill refinement). The [[non-blocking-observability]] pattern ensures tracking never blocks the primary execution path.

The 12D coordinate system maps agent state across multiple axes including task complexity, coherence, token efficiency, and skill coverage. Trajectory analysis of 5.5M simulated agent paths (from the [[universe-simulation]]) revealed the predictive throttling pattern — detecting velocity gradients in trajectory space to anticipate resource exhaustion before it occurs.

## Related
- [[2026-03-05-journeytracker-research-framing]] — project to frame JourneyTracker and DegradationDetector as a research contribution to agent evaluation methodology
- [[lesson-19-session-awareness-protocol]]
- [[lesson-37-experience-guided-execution-works-new]]
- [[session-57-local-finetuning|Session 57: Local Model Finetuning Pipeline]] — converts journey data (from this tracking system) to JSONL format for QLoRA and Ollama Modelfile finetuning
- [[2026-02-13-experience-vae-training-pipeline-session-58|Experience → VAE Training Pipeline]] — uses journey data to train a VAE on real agentic behavior distributions
- [[universe-simulation]] — the N-body simulation that generates agentic journey traces for compound learning
- [[momentum-based-trajectory-prediction-with-counterfactual-branching]] — predicts future trajectory branches using momentum from journey tracking data
- [[momentum-based-trajectory-prediction-with-counterfactuals]] — momentum-based prediction of next positions in the 12D journey space
- [[morphospace-stability-wells]] — identifies stable behavioral regions from historical journey trajectories
- [[structured-experience-vector-layout]] — experience vectors built from journey tracking observations
- [[structured-feature-vector-layout-for-agent-state]] — canonical layout for the agent state vectors that journey tracking records
- [[2026-02-20-session-58-cosmic-fire-module-retrospective|Session 58: Cosmic Fire Retrospective]] — journey tracker was modified to add cosmic fields and lazy-loaded ThreeFires integration
- [[2026-02-11-session-55-compound-engineering-approach-for-universe-simulation-preservation|Session 55: Universe Simulation Preservation]] — universe simulation generates trajectory data consumed by journey tracking
- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories|Hash-Based Journey Tracking Failure]] — documents why journey tracking requires FLUME latent vectors, not hash-based positions
- [[2026-02-27-ux-flume-as-foreground-three-lenses|FLUME as Foreground]] — Git Trajectory lens visualizes codebase paths through latent space built on journey tracking data
- [[research-lineage]] — journey tracking data contributes to the research lineage chain linking execution traces to knowledge outputs
- [[2026-02-12-phase1-complete-vault-and-surrealdb-integration]] — Phase 1 completion integrated vault and SurrealDB as the persistence layer for journey tracking data
- [[12D-Projection]] — the dimensionality reduction layer that maps FLUME latent space to 12 interpretable dimensions for journey visualization
- [[FLUME-Architecture]] — the VAE architecture that provides meaningful latent vectors for journey trajectory analysis

## Daily References

- [[2026-02-13-session-cf44ece1]] — Session 58: Experience VAE Pipeline + Model Roster + Long-Horizon Plan
- [[2026-02-14-session-1f75c2d8]] — Session 58: Experience VAE Pipeline + Agent Orchestration Design
- [[2026-02-14-session-7a1f0d61]] — Session 58: 7-phase journey enrichment complete + adversarial review fixes (789/789 tests passing)

## Session References

- [[session-50-handoff]] — real-time HIHO monitoring enabled by FLUME speedup in journey tracking

## Agent Outputs

- **Task: Harden Journey Substrate (EVO Cosmology)** — `Agents/Antigravity/1a07b73c-9de3-4349-bcc0-ba5977d202ee/task.md`

## Agent Execution Logs

- [[2026-02-11T14-30-example-phase1-step1]] — Phase 1 Step 1 implementation: SurrealDB agent context schema complete (2h 38m, 47 function calls, 1347 LOC)

## Skills

- JOURNEY_TRACKING_PRIME — Agent journey 12D tracking
