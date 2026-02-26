---
title: "Overnight Simulation: 5.5M 12D Trajectories"
date: "2026-02-24"
status: in-progress
tags: [experiment]
---

## Hypothesis

## Method

## Results

## Learnings

## Related

- [[experiments/2026-02-23-overnight-simulation-data-characterization-55m-trajectories|Overnight Simulation Data Characterization (5.5M trajectories)]] — the preceding experiment that characterized the dataset used here; this experiment extends to 12D trajectory embeddings
- [[patterns/predictive-throttling-via-12d-trajectory-velocity|Predictive Throttling via 12D Trajectory Velocity]] — the pattern this experiment is generating data to validate; 12D trajectories feed the velocity-based throttling predictor
- [[patterns/momentum-based-trajectory-prediction-with-counterfactual-branching|Momentum-Based Trajectory Prediction with Counterfactual Branching]] — complementary trajectory analysis pattern for exploring plausible future paths
- [[concepts/universe-simulation|Universe Simulation]] — the N-body simulation that generated the 5.5M trajectory corpus
- [[experiments/2026-02-24-sprint-4-end-to-end-integration-compound-execution-flume-cache-pipeline|Sprint 4: Compound Execution → FLUME Cache Pipeline]] — same date; the pipeline experiment that consumes trajectory data from simulations like this one
