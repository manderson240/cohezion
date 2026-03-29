# Implementation Plan: Sovereign EVO Agents & The Reward/Ratchet System

## Phase 1: EVO Agent Architecture
- [x] Task: Define the `EVOAgent` base class.
    - [x] Sub-task: Write unit tests for agent initialization and state management.
    - [x] Sub-task: Implement the agent class with hooks for the TriuneState and FLUME VAE.
- [x] Task: Implement the Agent Execution Loop.
    - [x] Sub-task: Write tests mocking the `TriuneSimulationEngine` interaction.
    - [x] Sub-task: Implement the `act()` method that transitions the manifold state.
- [x] Task: Conductor - User Manual Verification 'Phase 1: EVO Agent Architecture' (Protocol in workflow.md)


## Phase 2: Reward & Ratchet System
- [x] Task: Implement the `RewardCalculator`.
    - [x] Sub-task: Write unit tests for scoring logic based on the 0.5 Coherence Rule.
    - [x] Sub-task: Implement the scoring algorithm balancing coherence and token efficiency.
- [x] Task: Implement the `RatchetMechanism`.
    - [x] Sub-task: Write tests verifying state is locked/persisted when a high score is achieved.
    - [x] Sub-task: Implement the ratchet logic connecting to the persistence layer.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Reward & Ratchet System' (Protocol in workflow.md)

## Phase 3: Integration & Ascension
- [x] Task: Integrate Reward and Ratchet into the EVO Agent lifecycle.
    - [x] Sub-task: Write integration tests for a complete task-reward-ratchet cycle.
    - [x] Sub-task: Wire the components together in the agent's main processing loop.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Integration & Ascension' (Protocol in workflow.md)

## Phase: Review Fixes
- [x] Task: Apply review suggestions 79914f3
