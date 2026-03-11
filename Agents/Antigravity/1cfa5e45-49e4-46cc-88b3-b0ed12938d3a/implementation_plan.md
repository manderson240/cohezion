---
type: antigravity-artifact
session_id: 1cfa5e45-49e4-46cc-88b3-b0ed12938d3a
date: 2026-03-04
title: "Nexus Research Miner Implementation"
tags: [agent-output, antigravity, research-mining, knowledge-graph]
aspect: doer
neural:
  activation: 0.475
  stage: growing
  cluster: Agents
---

# Nexus Research Miner Implementation Plan

The goal is to implement a continuous monitoring and mining system for external research developments on arXiv, Hugging Face, GitHub, and broader conceptual frontiers like **World Models (JEPA/Yann LeCun)** and **Universe Simulation**. This ensures the Cohezion swarm stays calibrated with SOTA and disruptive theoretical physics/AI frontiers daily.

## Proposed Changes

### [Component: Swarm Debate]

#### [NEW] [source_discovery_debate.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/debates/source_discovery_debate.md)
A recorded debate between Arquitect, Engineer, and Librarian agents to identify non-obvious, high-signal research sources (e.g., specific researcher blogs, Discord channels, r/MachineLearning, etc.).

### [Component: Skills]

#### [NEW] [EXTERNAL_RESEARCH_PRIME.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/EXTERNAL_RESEARCH_PRIME.md)
Detailed instructions for searching, filtering, and synthesizing external research.
> [!IMPORTANT]
> **API Guardrails**: 
> - Implement Exponential Backoff for all API calls.
> - Cache results in SurrealDB for 24h to prevent redundant hits.
> - Jittered scheduling to avoid "burst" detection.
> - Token-aware summarization: Fetch abstracts first, only download full PDFs if rank > 0.9.

### [Component: Swarm Agents]

#### [NEW] [nexus_research_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/nexus_research_agent.py)
A specialized agent that handles:
- **MCP Research Integration**: Migrate arXiv and Hugging Face queries to MCP servers (research-mcp) for enhanced reliability and token efficiency.
- **JEPA & World Models**: Explicitly monitor Yann LeCun's research (V-JEPA, I-JEPA) and related world-model architectures.
- **Universe Simulation Pulse**: Monitor developments in cosmological simulation, cellular automata, and physics-informed neural networks (PINNs).
- **YouTube Transcripts**: Implement `YouTubeTranscriptAgent` to mine AI video content.
- **X (Twitter) Scout**: Implement `XScoutAgent` to monitor high-signal researcher feeds (e.g., Yann LeCun, Andrej Karpathy).
- **GitHub Trending**: Repo mining and code analysis.
- **Synthesizer** integration to push findings to the Knowledge Graph/SurrealDB.

### [Component: Security]

#### [MODIFY] [prompt_guard.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/security/prompt_guard.py)
Fine-tune patterns (specifically `base64_encoded` and `prompt_leak`) to allow technical LaTeX/Math/Code snippets common in research abstracts.
- Implement an **Exemption List** for specific agents (e.g., `NexusResearchAgent`).
- Relax `base64_encoded` length requirement or use a secondary "scientific context" check.

#### [MODIFY] [__init__.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/__init__.py)
Register `NexusResearchAgent`.

### [Component: Infrastructure]

#### [NEW] [cohezion-surreal.service](file:///etc/systemd/system/cohezion-surreal.service) [ADMIN]
A systemd unit to automate SurrealDB boot launch and persistence.
- **ExecStart**: `/home/mike-anderson/.surrealdb/surreal start --user root --pass root file://data/surrealdb`
- **Restart**: `always`
- **Persistence**: Switched from `memory` to `file` mode for long-horizon stability.

## Verification Plan

### Automated Tests
- Run `nexus_research_agent.py` in a dry-run mode to verify it can fetch data from arXiv and Hugging Face.
- Test JSON serialization of mined papers into the Knowledge Graph format.
- `pytest tests/test_nexus_research.py` (New test file).

### [Component: Security & Secrets]

#### [NEW] [credential_migration_plan.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/security/credential_migration_plan.md)
Documenting the transition from plaintext `.env` to a secure credential manager.

| Tool | Recommended | Why |
|------|-------------|-----|
| **Bitwarden CLI** | ✅ Primary | Industry standard, AES-256, cloud-sync, secrets manager for swarms. |
| **Pass (Unix)** | Alternate | Minimalist, GPG-based, local-only, hacker-friendly. |
### [Component: Recursive Language Model (RLM)]

#### [NEW] [rlm_executor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/rlm/rlm_executor.py)
A module to implement the RLM paradigm:
- **Environment**: Sandboxed Python REPL for code-based context exploration.
- **Recursion**: Enables agents to decompose large research inputs (PDFs, long threads) and recursively call themselves or specialized sub-agents.
- **Context Preservation**: Avoids lossy summarization by programmatically navigating the prompt space.

#### [NEW] [rlm_reasoning_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/rlm_reasoning_agent.py)
A specialized agent that utilizes the `RLMExecutor` for deep-dive synthesis of "infinite" context research.

### [Component: Remote Phone Communication]

#### [NEW] [phone_orchestrator.py](file:///home/mike-anderson/dev/cohezion/scripts/phone_orchestrator.py)
A long-running service that:
- **Polls Gmail**: Specifically for subjects starting with `[CMD]`.
- **Executes Commands**: `status`, `resume <task_id>`, `run <script>`, `query <text>`.
- **Notifies User**: Automatically sends an email when an agent is `BlockedOnUser`.

#### [NEW] [remote_cmd_debate.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/debates/remote_cmd_debate.md)
Architect and Security agents debating the safest way to execute phone-sent commands (e.g., restricted command list vs shell access).

### [Component: Advanced RLM & Visualization]

#### [NEW] [scalar_context_manager.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/rlm/scalar_context_manager.py)
Implements "Scalar Context Management" by:
- Assigning a `ImportanceScalar` (0.0-1.0) to context blocks.
- Using the scalar to determine RLM recursion depth (higher scalar = deeper dive).
- Compressing low-scalar context for memory efficiency.

#### [NEW] [journey_12d_explorer.py](file:///home/mike-anderson/dev/cohezion/notebooks/marimo/journey_12d_explorer.py)
A Marimo notebook for 12D journey visualization:
- Projects 256D FLUME vectors into 12D state vectors.
- Uses **Radar Charts** for the 8-brane sub-manifold and **3D Scatter** for spatial-temporal paths.
- Provides interactive playback of agent "thought journeys".

### [Component: Verification & Adversarial Tuning]

#### [NEW] [adversarial_transparency_test.py](file:///home/mike-anderson/dev/cohezion/tests/adversarial_transparency_test.py)
A specialized test suite to verify "Black Box" transparency claims:
- Injects ambiguous/confusing data to see if the interpretability layer correctly identifies the uncertainty.
- Validates the 12D state transitions against expected physical constraints.

**Migration Steps**:
1. Install `bw` (Bitwarden CLI).
2. Create/Login to Vault.
3. Import current `.env` secrets into a "Cohezion" collection.
4. Replace `.env` reads with `bw get item` or similar via a wrapper.

## Related Vault Notes

- [[semantic-search]]
- [[multi-agent-systems]]
- [[knowledge-graph-systems]]
