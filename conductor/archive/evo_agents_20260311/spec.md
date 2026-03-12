# Specification: Sovereign EVO Agents & The Reward/Ratchet System

## 1. Overview
This track implements the primary actors within the Cohezion ecosystem: Sovereign EVO Agents. Modeled conceptually as Exotic Vacuum Objects (charge clusters governed by MHD physics), these agents navigate the Triune Manifold. The track also introduces the core economic governance layer: the Reward & Ratchet system, ensuring that successful behaviors are permanently retained ("ratcheted") and failures inform future trajectories without loss of accumulated capability.

## 2. Core Requirements
- **EVO Agent Base Class**: A sovereign entity capable of receiving a prompt, converting it to a `ThoughtVector` (using the FLUME VAE), acting upon the environment (modifying the 12D `TriuneState`), and evaluating coherence.
- **Reward System**: A scoring mechanism that evaluates the agent's final coherence against the 0.5 HIHO stability target and other performance metrics (e.g., token efficiency).
- **Ratchet Mechanism**: A persistence hook that identifies highly successful agent states/skills and commits them to the "Root of Trust" (via SurrealDB/Obsidian) so they are never forgotten or degraded by subsequent updates.
- **Execution Loop**: Integration of the EVO Agent with the `TriuneSimulationEngine` to step through a full task lifecycle.

## 3. Technical Constraints
- Language: Python 3.13+
- Framework: Tight integration with the existing `TriuneManifold` and `FlumeVAE` modules.
- Strict TDD: 100% test coverage required for agent logic and reward calculations.
- Code Style: Must adhere strictly to `conductor/code_styleguides/python.md`.