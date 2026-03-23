---
title: "Federated Learning"
date: 2026-03-04
tags: [concept, machine-learning, privacy, distributed-systems]
aspect: knower
neural:
  activation: 0.86
  stage: growing
  synapse_in: 8
  synapse_out: 8
---

# Federated Learning

## Definition

Federated learning (FL) is a distributed machine learning paradigm in which multiple clients -- such as mobile devices, hospitals, or organizations -- collaboratively train a shared global model without exchanging raw data. Each client trains locally on its own data and sends only model updates (gradients or weight deltas) to a central aggregation server, which combines them into an improved global model. Introduced by McMahan et al. at Google in 2017, federated learning addresses the growing tension between the need for large training datasets and requirements for data privacy, regulatory compliance (GDPR, HIPAA), and data sovereignty.

## Key Properties

- **Data stays local:** Raw training data never leaves the client device or organization. Only model updates are transmitted, reducing privacy exposure and eliminating the need for centralized data lakes of sensitive information.
- **Aggregation algorithms:** FedAvg (Federated Averaging) is the foundational algorithm, averaging model weights across clients after local training rounds. Variants like FedProx, SCAFFOLD, and FedMA address challenges of non-IID data distributions and heterogeneous client capabilities.
- **Privacy-enhancing mechanisms:** Differential privacy adds calibrated noise to model updates to prevent reconstruction of individual training examples. Secure aggregation and homomorphic encryption ensure the server cannot inspect individual client updates. Trusted execution environments (TEEs) provide hardware-level isolation.
- **Statistical heterogeneity:** Real-world FL faces non-IID (non-independently and identically distributed) data across clients -- each device or organization has different data characteristics. This is the central technical challenge, as standard training assumes homogeneous data distributions.
- **Communication efficiency:** Gradient compression, quantization, and sparse updates reduce the bandwidth required for model synchronization, critical for mobile and IoT deployments where connectivity is limited or expensive.

## Examples

- Google's Gboard (Android keyboard) uses federated learning to improve next-word prediction models using text typed on millions of devices, without collecting user keystrokes on any server.
- MELLODDY (Machine Learning Ledger Orchestration for Drug Discovery), a European consortium of 10 pharmaceutical companies, used federated learning to collaboratively train drug discovery models on proprietary molecular data without sharing compounds across competitors.
- Hospitals in the EXAM (Electronic Medical Record-based prediction of COVID-19 severity) study used federated learning to build ICU admission prediction models across 20 sites without sharing patient records.

## Primary Sources

- McMahan, B. et al. (2017). *Communication-Efficient Learning of Deep Networks from Decentralized Data*. [arXiv:1602.05629](https://arxiv.org/abs/1602.05629)
- Kairouz, P. et al. (2021). *Advances and Open Problems in Federated Learning*. Foundations and Trends in Machine Learning. [arXiv:1912.04977](https://arxiv.org/abs/1912.04977)
- Li, T. et al. (2020). *Federated Optimization in Heterogeneous Networks (FedProx)*. [arXiv:1812.06127](https://arxiv.org/abs/1812.06127)

## Related Concepts

- [[machine-learning]] — the broader field within which federated learning operates
- [[edge-computing]] — FL clients are often edge devices performing local training and inference
- [[transfer-learning]] — federated transfer learning combines privacy-preserving distributed training with cross-domain adaptation
- [[multi-agent-systems]] — FL's distributed coordination model parallels multi-agent architectures
- [[ai-safety-alignment]] — federated learning contributes to AI safety by enabling model training without centralizing sensitive data
- [[active-inference]] — FL's distributed agents each minimize local free energy; federated aggregation corresponds to collective free energy minimization across a shared generative model without sharing raw observations
- [[privacy_security]] — federated learning is a core technique in privacy-preserving machine learning

## Related Papers

- [[nvidia-nemotron-3-nano-nemo-gym]] — efficient small models that can serve as local FL clients in resource-constrained environments
- [[ondevice_learning]] — on-device training is the local component of federated learning

## Relevance to Cohezion

Federated learning's core principle -- collaborative improvement without centralizing sensitive data -- directly parallels Cohezion's multi-agent architecture. Agents in Cohezion maintain local context and share only relevant observations through the knowledge graph, analogous to FL's model update aggregation. The vault's privacy-aware design, where agent session data stays local while aggregate patterns are shared, embodies the same data-locality principle that motivates federated learning in production systems.
