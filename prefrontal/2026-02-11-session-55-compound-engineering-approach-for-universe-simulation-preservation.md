---
title: Session 55 - Compound Engineering Approach for Universe Simulation Preservation
date: '2026-02-11'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Session 55 - Compound Engineering Approach for Universe Simulation
      Preservation'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
  confidence_score: 0.6
aspect: thinker
neural:
  activation: 0.585
  stage: mature
  cluster: decisions
---

## Context

The Cohezion project included a [[universe-simulation]] component that generated physics simulation data -- particle trajectories, gravitational interactions, and emergent structure formation. This simulation represented significant compute investment (multiple GPU-hours per run) and produced data that informed both the project's scientific research papers and its ML training pipelines.

During Session 55, repository cleanup operations threatened to destroy simulation output files that had been committed to git history. The core tension was between repository health (the 12GB bloat caused by committed simulation data) and knowledge preservation (the simulation results themselves were valuable experimental data). The [[compound-engineering]] principle demanded that we find a way to clean the repository without losing the knowledge embedded in simulation results.

This is a specific instance of a broader pattern in [[agentic-ai|agentic AI]] development: agent-generated artifacts (training data, simulation outputs, experiment results) have compound value that exceeds their storage cost, but storing them in git history is the wrong medium. The compound engineering approach requires choosing the right persistence layer for each type of artifact.

## Decision

Apply the [[compound-engineering]] preservation approach to universe simulation data:

1. **Extract before cleaning**: Before any git history rewriting, extract all simulation results from the historical commits into a dedicated artifact store (local directory outside the git tree, with a manifest file tracked in git).
2. **Preserve knowledge, not bytes**: For each simulation run, preserve the structured results (parameter configurations, summary statistics, key findings) as vault experiment records, even if the raw data files (multi-GB trajectory dumps) are discarded. The knowledge graph entries are the compound asset; the raw bytes are the ephemeral artifact.
3. **Retrospect before destroy**: Following the [[compound-engineering-investigation-retrospection-before-destructive-operations|investigation-retrospection pattern]], review each simulation run's contribution to downstream work before deciding whether to preserve, summarize, or discard its data.
4. **Document the provenance chain**: For any ML model or paper that was trained/written using simulation data, add explicit provenance links in the vault so that the origin of those results remains traceable even after raw data is removed from git.

## Consequences

- **Positive**: All simulation knowledge was preserved as structured vault records while the raw data files were safely removed from git history, reducing repository size without losing intellectual value.
- **Positive**: The provenance chain documentation revealed that 3 research papers in the vault depended on simulation results that would have been untraceable after cleanup. These dependencies are now explicit wiki-links.
- **Positive**: The "extract knowledge, discard bytes" pattern is reusable for all future compute-intensive experiments, establishing a clear boundary between the knowledge graph (persistent) and the artifact store (ephemeral).
- **Negative**: Extraction and documentation took approximately 1.5 hours of session time, delaying the repository cleanup.
- **Negative**: Some raw simulation trajectories were discarded that might have been useful for future retraining. However, the parameter configurations were preserved, allowing re-execution if needed.

## Alternatives Considered

- **Preserve everything in Git LFS** -- Move simulation files to Git LFS instead of removing them. Rejected because Git LFS still contributes to clone times and storage costs. The files were multi-GB raw trajectories that are reproducible from their parameter configurations.
- **Delete without extraction** -- Simply run BFG to strip large files without reviewing their content. Rejected because this would have broken provenance chains and potentially lost unique simulation results that informed published papers.
- **Move to a separate data repository** -- Create a dedicated git repo for simulation data. Rejected as unnecessarily complex; a simple local directory with a tracked manifest achieves the same goal with less infrastructure.
- **Keep the bloated repository** -- Accept the 12GB size and work around it. Rejected because the repository was operationally broken (failed pushes, slow clones) and the problem would worsen as more simulations were run.

## See Also

- [[compound-engineering]] -- the guiding principle for this decision
- [[universe-simulation]] -- the simulation system whose output was preserved
- [[compound-engineering-investigation-retrospection-before-destructive-operations]] -- the retrospection pattern applied before cleanup
- [[agent-journey-tracking]] -- universe simulation generates trajectory data used by the journey tracking system
- [[session-retrospective]] -- compound engineering approach includes retrospective analysis before destructive operations
- [[non-blocking-observability]] -- simulation preservation requires non-blocking data capture to avoid impacting runtime performance
- [[experience-feedback-loop]] -- preserved simulation knowledge feeds the experience loop for future experiments
- [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]] -- the training data antipattern that triggered the cleanup
- [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]] -- the staged cleanup approach used after preservation

## Primary Sources

- [Compound Engineering: Make Every Unit of Work Compound Into the Next](https://every.to/guides/compound-engineering) -- the compound engineering methodology this decision applies
- [Compound Engineering: How Every Codes With Agents](https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents) -- practical compound engineering patterns including knowledge capture
- [How Agentic AI Will Reshape Engineering Workflows in 2026 (CIO)](https://www.cio.com/article/4134741/how-agentic-ai-will-reshape-engineering-workflows-in-2026.html) -- cognitive leverage through reduced rediscovery of system knowledge
