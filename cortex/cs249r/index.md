---
tags: [index, ml-systems, cs249r]
source: cs249r
date: 2026-02-18
aspect: knower
neural:
  activation: 0.603
  stage: growing
  cluster: concepts
---

# CS249R ML Systems Book - Index

**Source:** [Machine Learning Systems Textbook](https://mlsysbook.ai/) by Harvard CS249R
**Repository:** https://github.com/harvard-edge/cs249r_book

## Overview

This vault contains knowledge extracted from the comprehensive CS249R ML Systems textbook, covering the full spectrum of machine learning systems engineering from foundations to frontiers.

**Content:**
- 21 core chapter concept notes
- 656 glossary terms (see [[ml-systems-glossary]])
- Cross-linked with existing Cohezion concepts

## Part I: Systems Foundations

- [[introduction]] - ML systems revolution, AI Triangle framework, silent degradation patterns
- [[ml_systems]] - ML system lifecycle, production deployment challenges
- [[dl_primer]] - Deep learning fundamentals, neural network basics
- [[dnn_architectures]] - CNNs, RNNs, Transformers, attention mechanisms

## Part II: Design Principles

- [[workflow]] - ML development workflow, experimentation frameworks
- [[data_engineering]] - Data pipelines, feature engineering, data quality
- [[frameworks]] - ML frameworks (TensorFlow, PyTorch), framework design
- [[training]] - Model training strategies, optimization techniques

## Part III: Performance Engineering

- [[efficient_ai]] - Knowledge distillation, pruning, quantization, NAS
- [[optimizations]] - Model optimizations, operator fusion, graph optimization
- [[hw_acceleration]] - Hardware acceleration, GPU/TPU utilization, specialized chips
- [[benchmarking]] - Benchmarking methodology, performance measurement

## Part IV: Robust Deployment

- [[ops]] - MLOps, model serving, A/B testing, monitoring for drift
- [[ondevice_learning]] - On-device learning, federated learning, edge ML
- [[privacy_security]] - Privacy-preserving ML, model security, differential privacy
- [[robust_ai]] - Robustness, adversarial examples, model reliability

## Part V: Trustworthy Systems

- [[responsible_ai]] - Fairness metrics, bias detection, explainability (SHAP/LIME)
- [[sustainable_ai]] - Environmental impact, carbon-aware scheduling, green AI
- [[ai_for_good]] - AI for social good, ethical AI applications

## Part VI: Frontiers

- [[frontiers]] - Emerging trends in ML systems
- [[conclusion]] - Future directions, open challenges

## Related Cohezion Concepts

**Cross-linked with existing vault:**
- [[meta-learning]] - Related to ML systems lifecycle and model training
- [[multi-agent-systems]] - Related to distributed ML and edge intelligence
- [[ai-safety-alignment]] - Related to responsible AI and trustworthy systems
- [[anomaly-detection]] - Related to monitoring and robust AI

## Glossary

**[[ml-systems-glossary]]** - Comprehensive glossary with 656 ML systems terms

## See Also

- PRIME Skills: `ML_SYSTEMS_FOUNDATIONS_PRIME`, `DNN_ARCHITECTURES_PRIME`, `DATA_ENGINEERING_PRIME`
- PRIME Skills: `EFFICIENT_AI_PRIME`, `MODEL_OPTIMIZATION_PRIME`, `MLOPS_DEPLOYMENT_PRIME`
- PRIME Skills: `RESPONSIBLE_AI_PRIME`, `EDGE_INTELLIGENCE_PRIME`
- TinyTorch: `src/cohezion/tinytorch/` - From-scratch ML framework based on book content
