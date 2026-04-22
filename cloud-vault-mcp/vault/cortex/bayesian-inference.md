---
title: "Bayesian Inference"
date: 2026-03-11
tags: [concept, statistics, machine-learning, probability, information-theory]
aspect: knower
neural:
  activation: 1.0
  stage: growing
  synapse_in: 2
  synapse_out: 8
---

# Bayesian Inference

## Definition

A statistical framework for updating beliefs about parameters or hypotheses in light of new evidence, based on Bayes' theorem:

> P(θ|D) = P(D|θ) · P(θ) / P(D)

Where P(θ|D) is the **posterior** (updated belief after seeing data), P(D|θ) is the **likelihood** (probability of the data given the hypothesis), P(θ) is the **prior** (belief before seeing data), and P(D) is the **evidence** or marginal likelihood (normalizing constant ensuring the posterior integrates to 1).

Bayesian inference treats probability as a **degree of belief** (epistemic probability) rather than a long-run frequency, enabling principled reasoning under uncertainty. This philosophical stance — called **subjectivist** or **Bayesian** probability — was formalized by de Finetti (1937), Ramsey (1926), and Savage (1954), and contrasts with the frequentist framework of Neyman-Pearson hypothesis testing.

The framework is foundational to modern AI: it is the mathematical backbone of [[active-inference]], variational autoencoders, Gaussian processes, Bayesian neural networks, and the entire field of probabilistic programming.

## Core Mathematics

### Bayes' Theorem (Continuous Form)

For continuous parameters θ with observed data D:

> p(θ|D) = p(D|θ) · p(θ) / ∫ p(D|θ') · p(θ') dθ'

The denominator (marginal likelihood) is often intractable, motivating two major computational strategies: **sampling** (MCMC) and **optimization** (variational inference).

### The Evidence Lower Bound (ELBO)

When exact inference is intractable, variational inference optimizes a tractable approximation q(θ) by maximizing the ELBO:

> ELBO = E_q[log p(D|θ)] - KL(q(θ) || p(θ))

The first term rewards data fit; the second penalizes deviation from the prior. This is the loss function used by variational autoencoders (VAEs) — including the [[FLUME-Architecture]] in Cohezion.

### Bayesian Decision Theory

Given a posterior p(θ|D) and a loss function L(θ, a), the optimal action a* minimizes expected loss:

> a* = argmin_a E_{p(θ|D)}[L(θ, a)]

This connects Bayesian inference to [[reinforcement-learning]] (where L encodes reward) and [[active-inference]] (where L encodes free energy).

## Key Properties

- **Prior → Posterior update**: beliefs are continuously refined as new evidence arrives; the posterior from one update becomes the prior for the next (sequential Bayesian updating)
- **Conjugate priors**: certain prior-likelihood pairs yield closed-form posteriors (e.g., Beta-Binomial, Normal-Normal, Dirichlet-Multinomial), enabling exact computation without sampling
- **Variational approximation**: when exact inference is intractable, variational methods minimize KL divergence between an approximate distribution q and the true posterior p(θ|D)
- **MCMC sampling**: Markov Chain Monte Carlo methods (Metropolis-Hastings, Hamiltonian MC, NUTS) sample from arbitrarily complex posteriors; the gold standard for accuracy at the cost of compute
- **Model comparison**: Bayes factors K = p(D|M₁)/p(D|M₂) compare competing hypotheses via marginal likelihoods, automatically penalizing model complexity (Bayesian Occam's razor)
- **Hierarchical models**: parameters can themselves have priors with hyperparameters, enabling multi-level models that share statistical strength across groups
- **Posterior predictive checks**: the posterior predictive distribution p(D*|D) = ∫ p(D*|θ)p(θ|D)dθ enables principled model validation by simulating new data from the fitted model

## Computational Methods

| Method | Exact? | Scalability | Use Case |
|--------|--------|-------------|----------|
| Conjugate analysis | Yes | Unlimited | Simple models with conjugate priors |
| Laplace approximation | No | High | Gaussian approximation around MAP |
| Variational inference (VI) | No | High | VAEs, topic models, deep learning |
| Expectation propagation | No | High | Sparse Gaussian processes |
| Metropolis-Hastings MCMC | Yes (asymptotic) | Low-Medium | General-purpose sampling |
| Hamiltonian MC / NUTS | Yes (asymptotic) | Medium | Continuous parameter spaces (Stan, PyMC) |
| Sequential Monte Carlo | Yes (asymptotic) | Medium | Online/streaming Bayesian updates |

## Examples

- **Spam filtering**: Naive Bayes classifiers use Bayesian inference to update word-class probabilities; despite the "naive" conditional independence assumption, they remain competitive for text classification
- **Clinical trials**: Bayesian adaptive designs update treatment arm probabilities as data accrues, enabling early stopping for efficacy or futility
- **Kalman filter**: The canonical example of sequential Bayesian inference — predicts and updates state estimates for linear dynamical systems (spacecraft navigation, GPS, sensor fusion)
- **Gaussian processes**: Bayesian nonparametric regression that places a prior directly over functions; used in Bayesian optimization for hyperparameter tuning
- **Probabilistic programming**: Languages like Stan, PyMC, NumPyro, and Turing.jl let users specify arbitrary generative models and automatically perform posterior inference

## Primary Sources

1. Bayes, T. (1763). "An Essay towards solving a Problem in the Doctrine of Chances." *Philosophical Transactions of the Royal Society*, 53, 370–418. [The original paper, published posthumously]
2. Jaynes, E.T. (2003). *Probability Theory: The Logic of Science.* Cambridge University Press. [The definitive modern treatment of Bayesian probability as extended logic]
3. Gelman, A. et al. (2013). *Bayesian Data Analysis.* 3rd ed. CRC Press. [The standard reference textbook; "BDA3"]
4. Bishop, C.M. (2006). *Pattern Recognition and Machine Learning.* Springer. [Chapters 1-2 and 10 provide the ML perspective on Bayesian inference and variational methods]
5. Murphy, K.P. (2023). *Probabilistic Machine Learning: Advanced Topics.* MIT Press. [Modern treatment covering VI, MCMC, normalizing flows, and Bayesian deep learning]

## Relevance to Cohezion

Bayesian inference underpins several vault concepts and platform components:
- [[active-inference]] uses variational Bayesian inference to unify perception and action under the free energy principle
- [[anomaly-detection]] can use Bayesian change-point detection for identifying regime shifts in agent performance metrics
- [[FLUME-Architecture]] uses a VAE whose training loss IS the ELBO — the core Bayesian variational inference objective
- Agent confidence scoring uses posterior probabilities to calibrate decision certainty
- The vault's neural activation model (SurrealDB neuron table) can be interpreted as sequential Bayesian updating: each session observation updates the activation posterior for a note

## Related Concepts

- [[active-inference]] — variational Bayesian inference applied to action and perception under Friston's free energy principle
- [[machine-learning]] — Bayesian methods provide a principled alternative to frequentist approaches, with built-in regularization via priors
- [[cognitive-science]] — the Bayesian brain hypothesis: the brain performs approximate Bayesian inference to predict sensory input
- [[reinforcement-learning]] — Bayesian RL maintains posterior distributions over MDPs, enabling principled exploration-exploitation trade-offs
- [[information-theory-it-from-bit|information theory]] — KL divergence, mutual information, and entropy are shared mathematical foundations
- [[FLUME-Architecture]] — the VAE encoder-decoder is a variational Bayesian inference machine
- [[cybernetics]] — Bayesian updating is the formal version of the cybernetic feedback loop: sense → update beliefs → act


