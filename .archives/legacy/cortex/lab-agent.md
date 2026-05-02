---
title: Lab Agent
date: 2026-02-23
tags: [agent-workflow, tool, compound-engineering]
status: active
aspect: knower
neural:
  activation: 0.93
  stage: mature
  synapse_in: 10
  synapse_out: 13
---

# Lab Agent

The lab agent (`lab_agent.py`) is a Cohezion agent specialized for experimental pipeline execution -- running training jobs, collecting metrics, and saving experience observations that feed back into the [[compound-engineering]] loop. It operates as a dedicated worker within Cohezion's [[multi-agent-systems|multi-agent architecture]], distinct from planning agents or review agents in that it executes compute-intensive tasks autonomously and reports structured results.

## Role in the Agent Architecture

The lab agent fills the "executor" role in Cohezion's agent hierarchy. While other agents handle planning (spec-plan), implementation (spec-implement), and verification (spec-verify), the lab agent handles experimental workloads that require sustained compute without human-in-the-loop interaction. This includes:

- **Training pipeline execution**: Running [[machine-learning|ML training jobs]] (e.g., VAE training on agent trajectory data, as in [[2026-02-24-flume-vae-v2-training-results]]) with configurable hyperparameters
- **Simulation orchestration**: Coordinating runs on the [[enhanced-simulator]] with parameter sweeps and collecting time-series output
- **Result collection and structuring**: Parsing raw training logs, extracting key metrics (loss curves, convergence rates, resource utilization), and formatting them as structured observations
- **Experience recording**: Writing results to the [[experience-feedback-loop]] so that future sessions can learn from completed experiments

The lab agent follows the [[agent-loop-architecture|agent loop pattern]]: observe environment state, decide whether to continue or terminate the experiment, act by adjusting parameters or recording results, and report findings as structured observations.

## Key Properties

- **Autonomous execution**: Once a training job or simulation is dispatched, the lab agent runs to completion without requiring session context. This is critical because training jobs may run for hours, far exceeding a single session's context window.
- **Structured output**: All results are formatted as YAML-frontmatter observations compatible with the vault's knowledge graph. This ensures experiment results are immediately queryable via [[graphrag-knowledge-graph-with-surrealdb|GraphRAG]].
- **Failure handling**: The lab agent captures failure modes (OOM errors, NaN losses, timeout conditions) as structured observations, not just success cases. Failed experiments carry as much information as successful ones for [[compound-engineering]] purposes.
- **Resource awareness**: The agent monitors GPU memory, disk space, and wall-clock time, terminating experiments that exceed configured budgets before they consume shared resources.
- **Idempotent reruns**: Experiment configurations are stored as checksummed parameter files, allowing exact reproduction of any past run.

## Examples

- **FLUME VAE v2 Training**: The lab agent executed the [[2026-02-24-flume-vae-v2-training-results|VAE v2 training run]], managing the training loop, capturing reconstruction loss and KL divergence metrics, and writing results back to the vault experiment record.
- **55M Trajectory Characterization**: The [[2026-02-24-overnight-simulation-data-characterization-55m-trajectories|overnight simulation data characterization]] was orchestrated by the lab agent, which parsed 55 million trajectory records and produced statistical summaries.

## Relevance to Cohezion

The lab agent embodies the [[compound-engineering]] principle at the execution layer. Each experiment it runs produces structured observations that make future experiments easier to design (by learning from past results), cheaper to run (by identifying optimal hyperparameter ranges), and faster to evaluate (by establishing baseline metrics). Without the lab agent, experiment execution would be manual, results would be captured inconsistently, and the feedback loop would be broken.

## Related

- [[compound-engineering]] -- the lab agent is a compound engineering asset; its results feed forward into future work
- [[agent-journey-tracking]] -- experiment runs are tracked as agent journeys with start, checkpoint, and completion events
- [[experience-feedback-loop]] -- the lab agent feeds experiment results into the experience feedback loop for compound learning
- [[enhanced-simulator]] -- the enhanced simulator provides the testing environment the lab agent runs experiments within
- [[multi-agent-systems]] -- the lab agent operates as a specialized agent within Cohezion's multi-agent architecture
- [[agent-architecture]] -- the lab agent's design follows Cohezion's standard agent architecture patterns
- [[agent-loop-architecture]] -- the observe-decide-act loop that governs lab agent behavior
- [[non-blocking-observability]] -- experiment telemetry uses non-blocking observation writes to avoid impacting training performance
- [[workflow-orchestration]] -- the lab agent is one component in Cohezion's broader workflow orchestration system
