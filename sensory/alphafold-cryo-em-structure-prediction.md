---
title: 'AlphaFold + cryo-EM: protein structure prediction for automated atomic model
  building'
date: 2026-02-07
tags: [structural-biology, protein-structure, cryo-em, alphafold, deep-learning, bioinformatics]
connectivity: 0.0
cross_domain: 0.12
completion: 1.0
temporal: 1.0
recency: 1.0
connectivity_summary: ☆☆☆☆☆ (0/5 links)
completion_summary: 3/3 sections (100%)
conceptual_depth: 1.0
conceptual_label: Pure Theory
similar_papers:
- alphagenom-dna-understanding
- brain-protein-neurodegeneration
- protein-tape-recorder-cytotape
- amorphous-materials-3d-atomic-structure
domain: Structural Biology
source: 'Source: Nature'
dimensions:
  connectivity: 0.1
  cross_domain: 1
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.333
  algorithm_complexity: 0.25
  implementation_difficulty: 0.0
  interdisciplinary_transfer: 0.25
  impact_score: 0.08
aspect: knower
neural:
  activation: 0.481
  stage: growing
  cluster: papers
---
## Abstract

AlphaFold integrated with cryo-EM imaging enables automated atomic model building for protein structures. This approach combines deep learning map enhancement with structure prediction to accelerate the traditionally labor-intensive process of constructing atomic models from cryo-EM density maps.

## Key Findings

- ModelAngelo uses graph neural networks to automatically build atomic models by combining cryo-EM maps with protein sequence and structure information at quality levels comparable to human experts
- DeepTracer-LowResEnhance integrates deep learning map refinement with AlphaFold to significantly improve model construction from low-resolution cryo-EM data
- Integrated workflows combining multi-modal deep learning with AlphaFold3 achieve improved structural accuracy by using sequence-based features from protein language models alongside density maps

## Source

https://www.nature.com/articles/s41586-024-07215-4

# AlphaFold + cryo-EM: protein structure prediction for automated atomic model building

## Summary

AlphaFold + cryo-EM: protein structure prediction for automated atomic model building.

## Key Findings

- AlphaFold + cryo-EM: protein structure prediction for automated atomic model building.

## Integration Point

general

## Relevance to Cohezion

AlphaFold + cryo-EM integration demonstrates how multi-modal AI (sequence data + density maps) enables automated expert-level structural biology, a pattern directly relevant to COHEZION's multi-agent compound engineering approach. [[machine-learning-optimization]], [[neural-network-architecture]], [[bioinformatics]]

## Related Papers

- [[alphagenom-dna-understanding]] — AlphaGenome extends AlphaFold's approach from protein structure to genome-scale DNA understanding; together they represent DeepMind's progressive application of foundation models to molecular biology
- [[amorphous-materials-3d-atomic-structure]] — parallel approach to 3D atomic-scale structure determination from indirect imaging data
- [[brain-protein-neurodegeneration]] — cryo-EM and AlphaFold together resolve amyloid beta and tau tangle structures central to Alzheimer's pathology

## Related Concepts

- [[transformer-architecture]] — AlphaFold's attention mechanism captures residue-residue co-evolution patterns using transformer self-attention
- [[bioinformatics]] — computational structural biology at the intersection of ML and molecular biology
- [[machine-learning]] — graph neural networks and deep learning for structure prediction
- [[neural-network-architecture]] — ModelAngelo's GNN architecture for atomic model building
- [[machine-learning-optimization]] — multi-modal deep learning combining sequence and density map data
- [[data-analysis]] — tomographic reconstruction and structure refinement pipelines
