---
title: "Anomaly Detection"
date: 2026-02-07
tags: [concept, agentic-ai, jwst-observations, ai-safety-alignment]
related_concepts: [ai-safety-alignment, agent-journey-tracking, non-blocking-observability, machine-learning, astrophysics-observations]
aspect: knower
neural:
  activation: 0.86
  stage: mature
  synapse_in: 13
  synapse_out: 17
---

## Definition

Methods for identifying unusual patterns and outliers in large datasets through statistical, clustering, classification, and distance-based approaches. Formalized by Chandola, Banerjee, and Kumar's 2009 ACM Computing Surveys paper, distinguishing simple anomalies from contextual and collective anomalies.

## Key Properties

- Categorizes techniques into classification-based, nearest neighbor, clustering, and statistical approaches
- Distinguishes point anomalies, contextual anomalies, and collective anomalies
- Operates in supervised, unsupervised, and semi-supervised settings
- Performance varies by feature dimensionality, data distribution, and anomaly type
- Foundation for fraud detection, network intrusion detection, and scientific discovery

## Examples

- Fraud detection: identifying unusual spending patterns inconsistent with user history
- Network intrusion detection: sequences of normal packets forming anomalous attack patterns

## Primary Sources

- Varun Chandola, Arindam Banerjee, Vipin Kumar (2009). *Anomaly Detection: A Survey*. [https://dl.acm.org/doi/10.1145/1541880.1541882](https://dl.acm.org/doi/10.1145/1541880.1541882)
- Multiple authors (2020). *A comprehensive survey of anomaly detection techniques for high dimensional big data*. [https://link.springer.com/article/10.1186/s40537-020-00320-x](https://link.springer.com/article/10.1186/s40537-020-00320-x)

## Related Papers

- [[ai-anomaly-detection-hubble-archive]]
- [[emoticons-llm-silent-failures]]

## Related Concepts

- [[agentic-ai]]
- [[jwst-observations]]
- [[ai-safety-alignment]]
- [[FLUME-Architecture]] -- FLUME reconstruction error is the primary anomaly detection signal for agent session health
- [[VAE-Encoder]] -- VAE reconstruction error serves as a proxy for normality, flagging anomalous agent behaviors
- [[Ouroboros-Loop]] -- the autonomic feedback loop that consumes anomaly detection signals to trigger corrective action

## Related Lessons

- [[lesson-measurement-integrity-honest-reporting]] — verified metrics over claimed metrics is the foundation of trustworthy anomaly detection; inflated numbers hide real anomalies

## Relevance to Cohezion

Anomaly detection capabilities in Cohezion are supported through the SemanticCache's L2 semantic similarity layer and the Knowledge Graph's anomaly-tracking capability within universe nodes. The ContextEngineeringInfrastructure's find_relevant_context function helps surface unusual patterns in prior execution logs stored by VaultExecutionLogger, enabling agents to detect deviations from normal solution patterns.

## Related Patterns

- [[morphospace-stability-wells]] — defines normal behavioral regions as stability wells; trajectories outside all known wells are anomaly candidates
- [[momentum-based-trajectory-prediction-with-counterfactual-branching]] — counterfactual branches enable probabilistic anomaly detection by checking if plausible futures enter anomalous regions
- [[momentum-based-trajectory-prediction-with-counterfactuals]] — early warning: predicts whether momentum carries the agent toward an anomalous region before arrival
- [[2026-02-23-hiho-coherence-loss-must-target-per-sample-not-batch-mean|HIHO Per-Sample Loss]] — bimodal coherence distributions hidden by batch mean are specific anomalies per-sample loss exposes
- [[2026-02-24-anti-pattern-hiho-coherence-loss-on-batch-mean|Anti-pattern: Batch-Mean HIHO]] — bimodal coherence distributions hidden by batch statistics are anomalies this anti-pattern masks
- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories|Hash-Based Journey Tracking Failure]] — hash-based trajectories produce false positive anomalies in 12D space

## Session References

- [[SESSION-43-PHASE-6-LAUNCH]] — Phase 6 anomaly detection task for cost monitoring
- [[SESSION-46-COMPLETE]] — anomaly detection component verified with threshold-based classification (0-100 scoring)

## Agent Outputs

- **Task: Autonomic Self-Healing Protocol** — `Agents/Antigravity/3bd15409-d092-4c70-9f1d-87d898d11153/task.md`

## Skills

- allostatica_prime — Monitoring manifold signals for anomalies
- HALLUCINATION_RESOLVER_PRIME — Truth anchors from live diagnostics
- HIHO_STABILITY_PRIME — Preventing chaotic drift and hallucinations
- REDUNDANCY_SUPPRESSION_PRIME — Detecting infinite scanning loops
- SELF_HEALING_PRIME — Detecting performance drift
- swarm_synthesis — Hallucination filtering in swarms
