---
title: ML Systems
date: 2026-03-04
tags: [concept, ml-systems, engineering, production, cs249r]
status: active
aspect: knower
neural:
  activation: 0.84
  stage: growing
  synapse_in: 13
  synapse_out: 8
---

# ML Systems

The engineering discipline concerned with designing, building, deploying, and maintaining machine learning applications as production-grade software systems. ML systems engineering bridges the gap between research model development and reliable production deployment, addressing challenges of data management, model serving, monitoring, and lifecycle management that pure ML research does not cover.

## Definition

An ML system is the complete sociotechnical assembly required to deliver ML-powered capabilities in production: data pipelines, feature stores, training infrastructure, model registries, serving platforms, monitoring dashboards, and the human processes that operate them. The CS249R textbook identifies the "AI Triangle" -- data, algorithms, and compute -- as the foundational resource triad, while emphasizing that most ML project failures stem from systems engineering issues (data quality, deployment complexity, silent degradation) rather than algorithmic limitations.

## Key Properties

- **Data-centric foundation** -- Data quality, freshness, and labeling accuracy dominate model performance more than architectural choices in most production settings
- **Silent degradation** -- ML systems degrade silently as data distributions shift, requiring continuous monitoring of both data and model metrics to detect performance decay
- **Technical debt accumulation** -- ML systems accumulate hidden technical debt through entangled features, pipeline jungles, dead experimental code paths, and configuration complexity
- **Lifecycle management** -- The ML lifecycle spans data collection, preparation, training, validation, deployment, monitoring, and retraining in a continuous loop
- **Reproducibility requirements** -- Production ML requires version control for data, code, models, and configurations to enable rollback and audit

## Examples

- **Recommendation systems** -- Production recommendation engines at scale (Netflix, Spotify) involve hundreds of ML models, feature pipelines, A/B testing frameworks, and real-time serving infrastructure
- **Autonomous driving stacks** -- Self-driving systems integrate perception, prediction, and planning ML models with safety-critical systems engineering requirements
- **CS249R ML lifecycle** -- The textbook presents the full ML system lifecycle from data collection through monitoring, emphasizing the engineering challenges at each stage

## Related Concepts

- [[machine-learning]] -- the algorithmic foundation that ML systems engineering operationalizes
- [[data_engineering]] -- data pipelines and feature engineering form the foundation of ML systems
- [[frameworks]] -- ML frameworks (PyTorch, TensorFlow) provide the building blocks for ML system construction
- [[training]] -- model training is one stage in the broader ML system lifecycle
- [[benchmarking]] -- system-level benchmarking measures end-to-end ML system performance
- [[efficient_ai]] -- efficiency techniques are essential for production ML systems with cost and latency constraints
- [[data-pipelines]] -- data pipeline architecture is a core concern of ML systems engineering
- [[workflow-orchestration]] -- ML systems require orchestrated workflows for training, evaluation, and deployment

## Relevance to Cohezion

Cohezion itself is an ML system in the broad sense: it orchestrates LLM-powered agents through structured workflows with data management (the vault), monitoring (session retrospectives), and lifecycle management (plan status tracking). The ML systems engineering principles of continuous monitoring, reproducibility, and lifecycle management directly inform Cohezion's architectural decisions around session persistence, knowledge graph maintenance, and agent performance tracking.
