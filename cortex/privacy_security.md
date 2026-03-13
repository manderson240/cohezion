---
title: Privacy and Security in AI
date: 2026-03-04
tags: [concept, privacy, security, ml-systems, differential-privacy, federated-learning]
aspect: knower
neural:
  activation: 0.85
  stage: growing
  synapse_in: 10
  synapse_out: 8
---

# Privacy and Security in AI

The techniques and practices that protect data confidentiality, model integrity, and system security throughout the AI/ML lifecycle. This encompasses privacy-preserving machine learning (differential privacy, federated learning, secure multi-party computation, homomorphic encryption), adversarial security (defense against model stealing, data poisoning, membership inference), and regulatory compliance (GDPR, HIPAA, CCPA).

## Definition

As AI systems process increasingly sensitive data -- medical records, financial transactions, biometric identifiers -- the risk of privacy breaches and security attacks grows. Privacy and security in AI addresses these risks at multiple levels: protecting training data from extraction, securing model parameters from theft, defending against adversarial inputs, and ensuring that deployed systems comply with data protection regulations. The field combines cryptographic techniques, statistical methods, and systems engineering.

## Key Properties

- **Differential privacy** -- Mathematical framework providing provable guarantees that individual data points cannot be identified from model outputs, controlled by privacy budget parameters (epsilon, delta)
- **Federated learning** -- Distributed training paradigm where models are trained across decentralized devices without centralizing raw data, using secure aggregation protocols
- **Adversarial threats** -- Model stealing (extracting model weights via query access), membership inference (determining if a sample was in training data), data poisoning (corrupting training data), and model inversion (reconstructing training examples)
- **Cryptographic methods** -- Homomorphic encryption (computing on encrypted data), secure multi-party computation (joint computation without revealing inputs), and zero-knowledge proofs (verifying properties without revealing data)
- **Regulatory compliance** -- Legal frameworks (GDPR, HIPAA, CCPA, EU AI Act) that mandate data protection, purpose limitation, consent management, and the right to explanation

## Examples

- **DP-SGD training** -- Training deep learning models with Differentially Private Stochastic Gradient Descent, adding calibrated noise to gradients to bound information leakage per training example
- **Federated learning in healthcare** -- Hospitals collaboratively training diagnostic models without sharing patient data, using secure aggregation to combine model updates
- **Trusted Execution Environments** -- Running inference inside hardware enclaves (Intel SGX, ARM TrustZone) to protect model weights and input data from the host system
- **Private set intersection** -- Two parties determining shared elements (e.g., matching patient records across institutions) without revealing non-shared data

## Sources

- Dwork, C. & Roth, A. (2014). "The Algorithmic Foundations of Differential Privacy." Foundations and Trends in Theoretical Computer Science, 9(3-4).
- McMahan, B. et al. (2017). "Communication-Efficient Learning of Deep Networks from Decentralized Data." AISTATS.
- CS249R ML Systems Book, Chapter: Privacy and Security. Harvard University.
- Papernot, N. et al. (2018). "SoK: Security and Privacy in Machine Learning." IEEE European Symposium on Security and Privacy.

## Related Concepts

- [[ai-safety]] -- Security as a dimension of AI safety
- [[federated-learning]] -- Distributed privacy-preserving training paradigm
- [[responsible_ai]] -- Privacy as a pillar of responsible AI development
- [[robust_ai]] -- Adversarial robustness as a security concern
- [[alignment]] -- Ensuring AI systems respect privacy constraints as part of value alignment
- [[cisa-chatgpt-data-leak]] -- Real-world case study of AI-related data exposure
- [[cs249r/privacy_security]] -- CS249R detailed chapter reference
- [[ondevice_learning]] -- on-device learning preserves privacy by keeping training data local

## Relevance to Cohezion

Cohezion agents process user context, session state, and vault content that may contain sensitive information. The framework's session isolation, context scoping, and private-tag mechanisms are practical implementations of privacy-by-design principles. Understanding privacy-preserving ML techniques informs how Cohezion handles embeddings, semantic search results, and cross-session knowledge sharing.
