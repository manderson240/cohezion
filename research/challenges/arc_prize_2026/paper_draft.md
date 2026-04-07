# Interactive Reasoning via Physics-Grounded World Models: JEPA + Topological Routing for ARC-AGI-3

## Abstract
Abstract reasoning remains one of the most challenging benchmarks for modern AI. The ARC-AGI-3 competition introduces an interactive component that requires agents to explore and discover rules within dynamic environments. We propose a novel architecture combining Joint-Embedding Predictive Architectures (JEPA) with Topological Data Analysis (TDA) for behavior regime detection. Our system, part of the Cohezion ecosystem, treats reasoning as navigation through a 12D manifold of physical and semantic constraints.

## 1. Introduction
The Abstraction and Reasoning Corpus (ARC) tests the ability to acquire new concepts from few examples. ARC-AGI-3 extends this to an interactive "Arcade" format. Existing methods relying on static LLM prompting fail to capture the causal dynamics of these environments.

## 2. Methodology
### 2.1 Joint-Embedding Predictive Architecture (JEPA)
We employ a JEPA world model to predict future latent states of the grid. By learning a representation that is invariant to irrelevant noise but sensitive to logical transformations, the JEPA provides a robust foundation for planning.

### 2.2 Topological Behavioral Routing
Agent trajectories are projected into a 256D latent space. We apply persistent homology to these trajectories to detect behavioral regimes:
- **EXPLOIT**: Stable clusters in H0, indicating a successful strategy.
- **EXPLORE**: High entropy and diverse H1 features, indicating active information gathering.
- **PIVOT**: Persistent loops in H1, indicating the agent is stuck in a repetitive, non-productive cycle.

### 2.3 Surprise-Driven Exploration
Exploration is driven by the prediction error of the JEPA model. High-surprise regions of the action-space are prioritized to maximize information gain.

## 3. Results (Preliminary)
Our baseline agent shows a significant reduction in JEPA prediction error within the first 50 steps of interaction on the "ls20" task. Topological routing successfully identifies stagnation points, enabling autonomous strategy pivoting.

## 4. Conclusion
Integrating physical grounding and topological awareness into interactive reasoning represents a promising path toward General Artificial Intelligence.
