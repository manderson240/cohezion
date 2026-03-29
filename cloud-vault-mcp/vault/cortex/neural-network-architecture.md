---
title: Neural Network Architecture
date: 2026-02-23
tags: [ml, deep-learning, architecture, transformer-architecture]
related_concepts: [transformer-architecture, self-attention-mechanism, machine-learning, machine-learning-optimization, agentic-ai]
status: active
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 46
  synapse_out: 20
---

# Neural Network Architecture

Neural network architecture defines the structural design of an artificial neural network: how many layers it has, what type of computation each layer performs, how layers connect, and what activation functions introduce non-linearity. Architecture is the primary determinant of a model's capabilities — a convolutional network is well-suited for spatial patterns in images, a recurrent network for sequential data with long-range dependencies, and a transformer for parallelizable sequence processing with attention.

The modern LLM era is dominated by the [[transformer-architecture]], which replaced recurrent networks for language tasks by processing entire sequences simultaneously via [[self-attention-mechanism]]. Transformers scale favorably: larger models trained on more data consistently outperform smaller ones, a property that drove the scaling hypothesis and GPT-series development. The practical consequence for Cohezion is that model capability is largely determined by parameter count and training data, making model selection (routing by size and type) the key optimization lever.

The FLUME VAE in Cohezion uses a variational autoencoder architecture: an encoder network compresses 12D agent trajectories into a 256-dimensional latent space, and a decoder reconstructs trajectories from latent codes. This architecture enables interpolation between agent states (exploring the latent space between two known trajectories) and anomaly detection (trajectories with high reconstruction error are anomalous).

## Key Variants
- **Feedforward (MLP)**: Dense layers; universal approximator; used for classification and regression
- **Convolutional (CNN)**: Local receptive fields; translation-invariant; used for images and spatial patterns
- **Recurrent (RNN/LSTM)**: Sequential state; handles variable-length sequences; largely superseded by transformers
- **Transformer**: Self-attention; parallelizable; dominant architecture for language models
- **Variational Autoencoder (VAE)**: Probabilistic encoder-decoder; latent space interpolation and generation
- **Graph Neural Networks (GNN)**: Node/edge message passing; used for graph-structured data

## Navigation

- [[MOC-machine-learning]] — Map of Content for the machine learning topic area

## Related
- [[transformer-architecture]] — the dominant architecture for LLMs powering Cohezion agents
- [[self-attention-mechanism]] — the core operation in transformer architectures
- [[machine-learning]] — the field neural network architectures belong to
- [[machine-learning-optimization]] — architecture-level optimization (quantization, distillation)
- [[agentic-ai]] — AI agents built on neural network foundation models
- [[FLUME-Architecture]] — Cohezion's VAE architecture for agent trajectory compression into latent space
- [[VAE-Encoder]] — the encoder component of variational autoencoders, mapping inputs to probabilistic latent distributions
- [[reinforcement-learning]] — RL algorithms use neural networks as function approximators for policies and value functions
- [[bioelectric-field-modeling-for-action-generation]] — pattern that applies gradient descent in potential fields for agent action generation
- [[structured-feature-vector-layout-for-agent-state]] — canonical feature vector layouts ensure model compatibility across architecture changes
- [[structured-experience-vector-layout]] — experience vector layout (state/action/reward/next_state/done) follows standard neural network RL training data conventions
- [[2026-02-24-anti-pattern-dual-vae-architecture-creates-integration-debt|Anti-pattern: Dual VAE]] — VAE architecture choices (FlumeVAE vs TemporalVAE) have downstream integration consequences
- [[2026-02-24-anti-pattern-character-level-tokenizer-for-semantic-embeddings|Anti-pattern: Character-Level Tokenizer]] — character-level LSTMs lack capacity for semantic representation
- [[2026-02-23-one-coherent-model-beats-two-partial-implementations|One Coherent Model]] — choosing between FlumeVAE and TemporalVAE is about correct architectural separation of concerns
- [[cognitive-science]] — neural network design draws on cognitive science models of brain computation
- [[materials-informatics]] — graph neural networks encoding crystal structures are a core materials informatics architecture
- [[synthetic-biology]] — generative models (CVAEs) design novel genetic circuits by learning from sequence-function data
- [[frameworks]] — ML frameworks provide layer abstractions, optimizers, and runtime for constructing and training architectures
- [[hw_acceleration]] — architecture design must consider target hardware capabilities (tensor cores, systolic arrays)

## Skills

- INTERPRETABILITY_PRIME — Black box transparency
- learning — PyTorch ecosystem for models
- observable_ai — Mechanistic interpretability of NNs
- physics_informed_prediction — Physics-informed neural networks
- VLIW_COG_BRIDGE_PRIME — VLIW/SIMD mapped to neural architectures
