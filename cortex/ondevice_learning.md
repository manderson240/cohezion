---
title: On-Device Learning
date: 2026-03-04
tags: [concept, ml-systems, edge-computing, privacy, cs249r]
status: active
aspect: knower
neural:
  activation: 0.82
  stage: growing
  synapse_in: 9
  synapse_out: 7
---

# On-Device Learning

The practice of training or fine-tuning machine learning models directly on end-user devices (smartphones, IoT sensors, embedded systems) rather than in centralized data centers. On-device learning enables personalization, privacy preservation, and low-latency adaptation while operating within the severe compute, memory, and energy constraints of edge hardware.

## Definition

On-device learning extends beyond on-device inference (running pre-trained models locally) to performing actual gradient computation and weight updates on the device itself. This enables models to adapt to individual user behavior, local environmental conditions, or domain-specific data distributions without transmitting raw data to cloud servers. The approach addresses privacy concerns (data never leaves the device), latency requirements (no network round-trip for adaptation), and connectivity limitations (offline operation). Key challenges include limited compute for backpropagation, constrained memory for storing gradients and optimizer states, and managing catastrophic forgetting when adapting to new data.

## Key Properties

- **Privacy by design** -- Training data remains on the device, eliminating privacy risks from centralized data collection and satisfying regulations like GDPR and HIPAA
- **Resource constraints** -- Backpropagation requires more memory and compute than inference alone; on-device learning techniques must minimize gradient storage and computation overhead
- **Personalization** -- Models adapt to individual user patterns (typing behavior, activity recognition, health metrics) that are too personal or sparse to learn from aggregate data
- **Catastrophic forgetting** -- Continuous learning on non-stationary local data risks degrading performance on previously learned tasks, requiring regularization or replay strategies
- **Federated integration** -- On-device learning is the local training component of federated learning, where per-device model updates are aggregated into a shared global model

## Examples

- **Gboard next-word prediction** -- Google's keyboard trains personalized language models on-device using federated learning, adapting to individual vocabulary and writing style
- **Health monitoring** -- Smartwatches running on-device learning to detect personalized anomaly patterns in heart rate, activity, and sleep data
- **Industrial IoT** -- Sensor nodes learning local normal operating patterns and detecting anomalies without requiring cloud connectivity

## Related Concepts

- [[federated-learning]] -- federated learning coordinates on-device training across many devices into a shared global model
- [[edge-computing]] -- on-device learning is the ML training dimension of edge computing
- [[efficient_ai]] -- resource-efficient training techniques are essential for learning within device constraints
- [[machine-learning]] -- on-device learning applies core ML training algorithms in constrained environments
- [[privacy_security]] -- on-device learning is a privacy-preserving ML technique
- [[hw_acceleration]] -- edge accelerators (NPUs, DSPs) enable practical on-device training
- [[transfer-learning]] -- pre-trained models fine-tuned on-device combine cloud-scale training with local adaptation

## Relevance to Cohezion

On-device learning principles inform Cohezion's local-first architecture. The framework's use of Ollama for local embedding generation and semantic search mirrors the on-device pattern: keeping data local (vault notes never leave the machine), adapting to the user's specific knowledge domain, and operating without mandatory cloud connectivity. The vault's concept caching strategy is analogous to on-device model caching, balancing freshness with resource constraints.
