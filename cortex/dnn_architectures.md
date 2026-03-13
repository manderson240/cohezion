---
title: DNN Architectures
date: 2026-03-04
tags: [concept, deep-learning, neural-networks, architectures, ml-systems]
aspect: knower
neural:
  activation: 0.86
  stage: growing
  synapse_in: 9
  synapse_out: 9
---

# DNN Architectures

The family of deep neural network structural designs -- including Multi-Layer Perceptrons (MLPs), Convolutional Neural Networks (CNNs), Recurrent Neural Networks (RNNs), and Transformers -- each optimized for different data modalities and computational patterns. Architecture choice determines how information flows through the network, what inductive biases are imposed, and how efficiently the model maps to hardware.

## Definition

DNN (Deep Neural Network) architectures are the structural blueprints that define how layers of artificial neurons are connected, how data flows through the network, and what mathematical operations are applied at each stage. Each architecture family embeds different assumptions about input structure: CNNs assume spatial locality, RNNs assume sequential dependencies, and Transformers assume that all positions may attend to all others. The choice of architecture profoundly affects model capacity, training dynamics, inference cost, and hardware utilization.

## Key Properties

- **Inductive bias** -- Each architecture family encodes assumptions about data structure (spatial locality for CNNs, temporal ordering for RNNs, global attention for Transformers)
- **Hierarchical feature extraction** -- Deep architectures learn representations at increasing levels of abstraction, from edges and textures to objects and concepts
- **Computational patterns** -- MLPs use dense matrix multiplications, CNNs use sliding-window convolutions, RNNs use sequential state updates, Transformers use parallel attention computations
- **Hardware mapping** -- Architecture operations have different efficiency profiles on CPUs, GPUs, and specialized accelerators (TPUs, NPUs)
- **Gradient flow** -- Residual connections, layer normalization, and gating mechanisms address vanishing/exploding gradient problems in deep networks

## Examples

- **Multi-Layer Perceptrons (MLPs)** -- Fully connected layers for tabular data and as building blocks within larger architectures; universal approximators but with no spatial or temporal inductive bias
- **Convolutional Neural Networks (CNNs)** -- Convolutional and pooling layers for image classification (ResNet, VGG), object detection (YOLO, Faster R-CNN), and medical imaging
- **Recurrent Neural Networks (RNNs)** -- Sequential processing via LSTM and GRU cells for time series forecasting, speech recognition, and language modeling (largely superseded by Transformers for NLP)
- **Transformer Architecture** -- Self-attention and multi-head attention for language models (GPT, BERT), vision (ViT), and multimodal systems; dominant architecture since 2017

## Sources

- LeCun, Y. et al. (1998). "Gradient-Based Learning Applied to Document Recognition." Proceedings of the IEEE.
- Vaswani, A. et al. (2017). "Attention Is All You Need." NeurIPS.
- He, K. et al. (2016). "Deep Residual Learning for Image Recognition." CVPR.
- CS249R ML Systems Book, Chapter: DNN Architectures. Harvard University.

## Related Concepts

- [[neural-network-architecture]] -- General neural network design principles
- [[transformer-architecture]] -- Detailed treatment of the Transformer family
- [[self-attention-mechanism]] -- Core mechanism in Transformer architectures
- [[dl_primer]] -- Deep learning fundamentals underlying all DNN architectures
- [[efficient_ai]] -- Efficiency considerations in architecture design
- [[computer-vision]] -- Primary application domain for CNN architectures
- [[natural-language-processing]] -- Primary application domain for Transformer architectures
- [[machine-learning]] -- Parent discipline encompassing all DNN architectures
- [[cs249r/dnn_architectures]] -- CS249R detailed chapter reference

## Relevance to Cohezion

Understanding DNN architectures is essential for Cohezion's research pipeline, which processes papers on neural network innovations, model optimization, and hardware-software co-design. The vault's concept graph links architecture choices to downstream performance, efficiency, and deployment considerations, enabling agents to reason about the full stack from architecture design to production deployment.
