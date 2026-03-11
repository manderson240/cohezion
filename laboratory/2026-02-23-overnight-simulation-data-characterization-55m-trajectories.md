---
title: "Overnight Simulation Data Characterization (5.5M trajectories)"
date: "2026-02-23"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.595
  stage: mature
  cluster: experiments
---

## Hypothesis

An overnight run of the [[universe-simulation|N-body gravitational simulation]] would produce a trajectory dataset of sufficient size and quality to characterize the statistical properties of particle dynamics under gravitational interaction -- and that these properties would be informative for designing the [[agent-journey-tracking|agent trajectory]] representation used in Cohezion's [[compound-engineering]] pipeline. The hypothesis specifically predicted that gravitational systems would naturally produce the kinds of trajectory patterns (convergence, divergence, oscillation, escape) that mirror agent behavioral modes.

## Method

1. **Simulation configuration**: Configured the N-body simulation with parameters tuned for diversity: multiple gravitational wells, a range of initial velocities, and sufficient particle count to generate statistically significant trajectory families.
2. **Overnight execution**: Launched the simulation as an unattended overnight process using the [[enhanced-simulator|enhanced simulator]] tooling, with automatic checkpointing and trajectory output.
3. **Data collection**: Collected 5.5M trajectory samples, each recording position, velocity, and energy at multiple timesteps throughout the simulation.
4. **Basic statistics**: Computed first-order statistics (mean, variance, range) across all trajectory dimensions to establish the data distribution baseline.
5. **Anomaly screening**: Checked for numerical instabilities (NaN, Inf, energy conservation violations) that would indicate simulation bugs.
6. **Pattern identification**: Visually and statistically examined trajectory families to identify recurring patterns: bound orbits, scattering events, capture events, and ejections.

## Results

- **Dataset size**: 5.5M trajectories collected over the overnight run, totaling several GB of trajectory data.
- **Data quality**: Zero numerical instabilities detected. Energy conservation held within expected tolerances for the integration scheme.
- **Trajectory families identified**: At least 4 distinct trajectory types: (1) stable bound orbits around gravitational wells, (2) scattering trajectories that deflect off wells without capture, (3) capture events where initially free particles become bound, and (4) ejection events where bound particles gain enough energy to escape.
- **Distribution properties**: Position distributions showed strong spatial clustering around gravitational wells. Velocity distributions followed a heavy-tailed pattern consistent with gravitational dynamics (Maxwell-Boltzmann core with power-law tails from scattering).
- **Implications for VAE**: The dataset showed sufficient diversity and structure for downstream machine learning. The natural trajectory families provided implicit labels, and the continuous nature of the dynamics provided smooth interpolation between trajectory types.

## Analysis

The characterization confirmed that gravitational N-body simulations produce trajectory data with rich, structured variation -- precisely the kind of data that a [[neural-network-architecture|VAE]] can learn to encode into a meaningful latent space. The 4 trajectory families (bound, scatter, capture, eject) map naturally onto agent behavioral modes: agents that settle into productive patterns (bound), agents that briefly interact with a task and move on (scatter), agents that transition from exploration to focused work (capture), and agents that disengage from a failing strategy (eject).

This natural mapping validates the [[universe-simulation]] as more than a physics exercise: it is a principled generator of behavioral trajectory data that encodes the same dynamics relevant to agent orchestration. The [[2026-02-23-never-train-vae-on-random-noise-as-synthetic-data]] decision, made around the same time, was directly informed by seeing the difference between this structured real data and the previous synthetic Gaussian placeholder.

## Learnings

1. **Overnight simulation is a reliable data generation strategy**: Unattended runs with checkpointing produce large, high-quality datasets without operator attention, making them scalable and repeatable.
2. **Gravitational dynamics naturally produce diverse trajectory types**: The 4 families (bound, scatter, capture, eject) emerged from physics alone, without any engineering. This diversity is essential for training models that need to handle multiple behavioral modes.
3. **Energy conservation as data quality check**: Monitoring energy conservation during simulation provides a built-in anomaly detector -- any numerical instability shows up as energy drift before it corrupts trajectory data.
4. **Real data >> synthetic data for learning**: The structured correlations in real simulation data (positions predict velocities, energy constrains trajectories) are exactly what learning algorithms need. Synthetic Gaussian noise destroys these correlations.
5. **Characterization before training prevents wasted compute**: Spending time to understand the data distribution before feeding it to a model catches quality issues early and informs architecture decisions (e.g., how many latent dimensions the VAE needs).

## Relevance to Cohezion

This characterization experiment is the foundation for all trajectory-based learning in Cohezion. The [[2026-02-24-overnight-simulation-55m-12d-trajectories|12D trajectory embedding]] experiment, the [[2026-02-24-temporalvae-first-training-run-on-overnight-data|TemporalVAE training run]], and the [[predictive-throttling-via-12d-trajectory-velocity|predictive throttling]] pattern all depend on the data quality established here. By characterizing the data before using it, this experiment ensured that downstream components could trust their input and focus on their own learning objectives rather than debugging data quality issues.

## Related

- [[2026-02-24-overnight-simulation-55m-12d-trajectories|Overnight Simulation: 5.5M 12D Trajectories]] — the follow-up experiment using 12-dimensional trajectory embeddings on the same 5.5M trajectory dataset characterized here
- [[universe-simulation|Universe Simulation]] — the N-body simulation that generated the 5.5M trajectory dataset being characterized
- [[momentum-based-trajectory-prediction-with-counterfactual-branching|Momentum-Based Trajectory Prediction with Counterfactual Branching]] — the trajectory analysis pattern applicable to the 5.5M trajectory dataset
- [[predictive-throttling-via-12d-trajectory-velocity|Predictive Throttling via 12D Trajectory Velocity]] — the 12D trajectory velocity pattern derived from experiments with this simulation data
- [[2026-02-23-never-train-vae-on-random-noise-as-synthetic-data|Never Train VAE on Random Noise]] — data quality decision made around the same time as this characterization; motivated by understanding the real data distribution
