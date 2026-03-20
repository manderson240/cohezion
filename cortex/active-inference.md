---
title: "Active Inference"
date: 2026-03-10
tags: [concept, neuroscience, machine-learning, free-energy-principle, bayesian-inference, cognitive-science]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 12
  synapse_out: 13
---

# Active Inference

## Definition

**Active inference** is a corollary of Karl Friston's **free energy principle** (FEP), proposing that all adaptive systems — from single cells to brains to social organizations — can be described as minimizing a quantity called **variational free energy** (or its expected future value, **expected free energy**). The system does this through two complementary mechanisms: updating its internal model of the world (perception) and acting on the world to make observations conform to its predictions (action).

Unlike orthodox reinforcement learning, which separates the problems of perception (state estimation) and control (policy optimization), active inference unifies them under a single imperative: minimize surprise. An agent does not maximize reward; it minimizes the divergence between its predictions and its sensory observations. Preferences are encoded as prior beliefs about the observations the agent expects to make — desired states are simply states the agent's generative model predicts it should occupy.

## Key Properties

### Variational Free Energy

For an agent with sensory observations $\mathbf{o}$, hidden states $\mathbf{s}$, and an approximate posterior $q(\mathbf{s})$ over hidden states, the variational free energy is:

$$F = \underbrace{D_{KL}[q(\mathbf{s}) \| p(\mathbf{s} | \mathbf{o})]}_{\geq 0} + \underbrace{(-\ln p(\mathbf{o}))}_{\text{surprise}}$$

Since the KL divergence is non-negative, $F$ is an upper bound on surprise (negative log model evidence):

$$F \geq -\ln p(\mathbf{o})$$

Minimizing $F$ with respect to $q(\mathbf{s})$ (perception) tightens the bound, making $q$ a better approximation to the true posterior. Minimizing $F$ with respect to action changes observations $\mathbf{o}$ to reduce surprise directly.

Equivalently, free energy decomposes as:

$$F = \underbrace{D_{KL}[q(\mathbf{s}) \| p(\mathbf{s})]}_{\text{complexity}} - \underbrace{\mathbb{E}_{q(\mathbf{s})}[\ln p(\mathbf{o} | \mathbf{s})]}_{\text{accuracy}}$$

This reveals the **accuracy-complexity trade-off**: a good model is both accurate (explains observations) and simple (posterior close to prior), embodying an automatic Occam's razor.

### Expected Free Energy and Planning

For future-oriented behavior (planning, policy selection), the agent evaluates policies $\pi$ by their **expected free energy** $G(\pi)$:

$$G(\pi) = \sum_{\tau} \underbrace{D_{KL}[q(\mathbf{o}_\tau | \pi) \| p(\mathbf{o}_\tau)]}_{\text{pragmatic value}} + \underbrace{H[q(\mathbf{o}_\tau | \mathbf{s}_\tau, \pi)]}_{\text{epistemic value}}$$

The first term (pragmatic/extrinsic value) drives the agent toward preferred observations encoded in the prior $p(\mathbf{o}_\tau)$. The second term (epistemic/intrinsic value) drives information-seeking behavior — the agent actively seeks observations that reduce uncertainty about hidden states.

Policy selection follows a softmax:

$$p(\pi) = \sigma(-\gamma \cdot G(\pi))$$

where $\gamma$ is an inverse temperature (precision) parameter governing the balance between exploitation and exploration.

### Markov Blankets

The free energy principle requires a statistical boundary — a **Markov blanket** — separating internal states from external states. The blanket consists of sensory states (influenced by external states) and active states (influencing external states). The dynamics decompose as:

$$\dot{\mu} = f(\mu, s, a) \quad \text{(internal states)}$$
$$\dot{a} = g(\mu, s, a) \quad \text{(active states)}$$
$$\dot{s} = h(\mu, s, a, \eta) \quad \text{(sensory states)}$$
$$\dot{\eta} = k(s, a, \eta) \quad \text{(external states)}$$

where $\mu$ are internal states, $a$ active states, $s$ sensory states, and $\eta$ external states. Internal states only "see" external states through the sensory blanket, and influence them only through active states.

### Generative Models

Active inference requires a **generative model** $p(\mathbf{o}, \mathbf{s}, \pi)$ specifying:

- **Likelihood**: $p(\mathbf{o}_\tau | \mathbf{s}_\tau)$ — how hidden states generate observations
- **Transition**: $p(\mathbf{s}_{\tau+1} | \mathbf{s}_\tau, \pi)$ — state dynamics under policy $\pi$
- **Prior preferences**: $p(\mathbf{o}_\tau)$ — which observations the agent "prefers"
- **Prior over policies**: $p(\pi)$ — initially uniform, shaped by expected free energy

The discrete-state formulation uses categorical distributions and matrices (A, B, C, D matrices in the standard notation), making it computationally tractable for moderate state spaces.

### Relation to Reinforcement Learning

| Aspect | Reinforcement Learning | Active Inference |
|--------|----------------------|------------------|
| Objective | Maximize cumulative reward | Minimize (expected) free energy |
| Reward | Externally specified signal | Emergent from prior preferences |
| Exploration | Separate mechanism (epsilon-greedy, UCB) | Intrinsic via epistemic value |
| Perception | Often separate module | Unified with action selection |
| Model | Optional (model-free RL exists) | Mandatory (generative model) |
| Optimality | Bellman optimality | Bounded rationality (variational) |

Active inference subsumes reward-maximizing behavior: setting prior preferences $p(\mathbf{o}_\tau)$ to concentrate on high-reward observations recovers reward-maximizing behavior as a special case, while retaining intrinsic epistemic drive.

## Examples

### Oculomotor Control (Saccadic Eye Movements)

Active inference explains saccadic eye movements as epistemic foraging: the visual system moves the eyes to locations that maximally reduce uncertainty about the scene. The model predicts saccade sequences that match human data, including the tendency to fixate on informative regions (faces, text) rather than uniform backgrounds.

### Interoception and Emotion

Interoceptive inference treats emotions as the brain's inference about the causes of internal bodily signals. Anxiety, for instance, arises when there is high uncertainty (imprecise interoceptive predictions) about visceral states. This framework unifies theories of emotion, homeostasis, and allostasis under a single variational principle.

### Robot Navigation

Active inference agents navigating a maze exhibit a natural balance between goal-directed behavior (moving toward a target) and curiosity-driven exploration (visiting unexplored areas to reduce map uncertainty). The epistemic term in expected free energy provides exploration without requiring explicit exploration bonuses or count-based methods.

### Morphogenesis and Biological Self-Organization

Friston and colleagues have applied active inference to morphogenesis, arguing that cells minimize free energy relative to a morphogenetic "generative model." This connects to [[levin-bioelectrics]]: bioelectric patterns encode the target morphology (the generative model), and cells act to minimize the discrepancy between current and target patterns through ion channel regulation and gap junction communication.

## Primary Sources

1. Friston, K. (2010). "The free-energy principle: a unified brain theory?" *Nature Reviews Neuroscience*, 11(2), 127-138.
2. Friston, K. et al. (2017). "Active inference: a process theory." *Neural Computation*, 29(1), 1-49.
3. Parr, T., Pezzulo, G. & Friston, K. (2022). *Active Inference: The Free Energy Principle in Mind, Brain, and Behavior*. MIT Press.
4. Da Costa, L. et al. (2020). "Active inference on discrete state-spaces: a synthesis." *Journal of Mathematical Psychology*, 99, 102447.
5. Friston, K., FitzGerald, T., Rigoli, F., Schwartenbeck, P. & Pezzulo, G. (2017). "Active inference and learning." *Neuroscience & Biobehavioral Reviews*, 68, 862-879.
6. Sajid, N., Ball, P.J., Parr, T. & Friston, K. (2021). "Active inference: demystified and compared." *Neural Computation*, 33(3), 674-712.
7. Ramstead, M.J.D., Badcock, P.B. & Friston, K.J. (2018). "Answering Schrödinger's question: a free-energy formulation." *Physics of Life Reviews*, 24, 1-16.

## Related Concepts

- [[machine-learning]] — active inference provides an alternative foundation to reward-maximizing RL
- [[bayesian-inference]] — the mathematical backbone; active inference is variational Bayesian inference applied to action
- [[embodied-ai]] — active inference is inherently embodied: perception and action are inseparable
- [[levin-bioelectrics]] — bioelectric morphogenesis as cellular active inference
- [[cognitive-science]] — the FEP is proposed as a unified theory of brain function
- [[emergence-and-self-organized-criticality]] — self-organization emerges from collective free energy minimization
- [[reinforcement-learning]] — active inference generalizes and subsumes RL
- [[anomaly-detection]] — surprise (negative log evidence) is literally the anomaly signal
- [[integrated-information-theory]] — FEP and IIT are competing unifying theories of mind; both ground cognition in information geometry; active inference minimizes free energy while IIT maximizes Φ — potentially complementary objectives
- [[natural-language-processing]] — language models as predictive coding machines; next-token prediction is variational free energy minimization over a sequence generative model
- [[material-science]] — active inference applied to materials discovery: models predict structure-property relations, flag high-surprise experimental outcomes for targeted synthesis
- [[astrophysics-observations]] — AI anomaly detection in JWST and Hubble archives is active inference: models predict expected observations, flag high-surprise deviations as discovery candidates
- [[computer-vision]] — ViT and CNN models implement perceptual inference — mapping visual observations to latent states — which is the perceptual half of active inference
- [[federated-learning]] — distributed FL agents each minimize local free energy; federated aggregation corresponds to collective free energy minimization across a distributed generative model

### Indigenous Cosmology Cross-Validation

- [[indigenous-cosmologies-toe-synthesis]] — 15 traditions describe agents (shamans, diviners, ceremony leaders) that perceive, model, and act to minimize surprise — active inference in pre-formal language
- [[andean-quechua-cosmology-and-toe]] — Ayni (reciprocity) as the FEP in action: the community minimizes free energy through reciprocal exchange
- [[daoist-cosmology-and-toe]] — Wú Wéi (effortless action) as optimal active inference: acting without fighting the generative model

## Relevance to Cohezion

Active inference provides the deepest formal connection between the TOE synthesis and the Cohezion platform architecture. The claim in [[the-awareness-of-nothing-at-all-and-quadrature-physics]] that "consciousness reduces entropy" receives precise mathematical formulation through the FEP: any system with a Markov blanket — including an AI agent — necessarily acts to minimize variational free energy, which upper-bounds surprise, which is the entropy of observations under the generative model.

For Cohezion's agent architecture, active inference offers a principled alternative to reward engineering. Instead of specifying reward functions for vault maintenance, knowledge linking, and triage, agents could be equipped with **generative models** of what a healthy vault looks like (prior preferences over vault states). The agents would then naturally:

1. **Perceive** — infer the current state of the vault (missing links, stale notes, orphan documents)
2. **Act** — modify the vault to bring it closer to the preferred state
3. **Explore** — seek out uncertain or underdeveloped regions of the knowledge graph (epistemic drive)

This unification of perception and action under a single objective mirrors how the vault itself functions as a dissipative structure (see [[dissipative-structures]]): agent energy input maintains low-entropy organization, and the generative model defines the attractor basin — the organized state toward which the system is driven.

The free energy principle thus provides the mathematical bridge between Campbell's "consciousness reduces entropy," Prigogine's dissipative structures, and Friston's active inference — all unified as manifestations of systems with Markov blankets minimizing variational free energy relative to their generative models of the world.
