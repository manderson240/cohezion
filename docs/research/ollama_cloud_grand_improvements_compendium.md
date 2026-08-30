# ☁️ Ollama Cloud Grand Advisory Compendium

**Date**: 2026-08-24  
**Advisors**: DeepSeek-V4 Pro Cloud (1.6T), Qwen-397B Cloud, Kimi-K3 Cloud  

## Frontier Differential Geometer & AGI Theorist (`deepseek-v4-pro:cloud`)
**Duration**: 24.28s

1. **Define the Fisher metric with FLUME/Jacobian/hyperbolic weighting.**  
   Let \(\theta \in \Theta = \mathbb{R}^m \times \mathbb{B}^d\) parameterize a stochastic policy \(\pi_\theta(a \mid x)\) over DSL primitives \(a\), where \(x=(s,J,h)\) contains the 12D FLUME state \(s\), Jacobian sensitivity map \(J_{ij}=\|\partial S/\partial x_{ij}\|\), and Poincaré embedding \(h\). Define
   \[
   G(\theta)=\mathbb{E}_{x\sim \rho_\theta,\,a\sim\pi_\theta}\!\left[
   \kappa(J)\,e^{-\beta d_P(h,h_*)}\,
   \nabla_\theta \log \pi_\theta(a\mid x)\,
   \nabla_\theta \log \pi_\theta(a\mid x)^\top
   \right],
   \]
   with \(\kappa(J)=1+\gamma \|J\|_F\) and \(h_*\) a target hyperbolic prototype. This is the Fisher information metric; it encodes the local KL-divergence curvature of the policy weighted by Jacobian sensitivity and hyperbolic relevance.

2. **Compute the Riemannian gradient.**  
   For a synthesis reward/loss
   \[
   L(\theta)=\mathbb{E}_{x,a\sim\pi_\theta}[R(a,x)],
   \]
   compute the Euclidean policy gradient
   \[
   \nabla_\theta L(\theta)=\mathbb{E}_{x,a\sim\pi_\theta}\!\left[R(a,x)\nabla_\theta \log \pi_\theta(a\mid x)\right].
   \]
   Solve the damped Fisher linear system
   \[
   (G(\theta)+\epsilon I)\,v=\nabla_\theta L(\theta),
   \]
   so that
   \[
   v=(G(\theta)+\epsilon I)^{-1}\nabla_\theta L(\theta)
   \]
   is the natural gradient on the Riemannian manifold \((\Theta,G)\).

3. **Retract along the Fisher geodesic.**  
   Update the Euclidean and hyperbolic components separately:
   \[
   \theta_E^{t+1}=\theta_E^t-\eta\,v_E,
   \qquad
   \theta_H^{t+1}=\exp_{\theta_H^t}^{\mathbb{B}^d}\!\left(-\eta\,v_H\right),
   \]
   where \(\exp^{\mathbb{B}^d}\) is the Poincaré-ball exponential map and \(v=(v_E,v_H)\). Equivalently,
   \[
   \theta^{t+1}=R_{\theta^t}\!\left(-\eta\,G(\theta^t)^{-1}\nabla_\theta L(\theta^t)\right),
   \]
   with \(R_\theta\) the product retraction. This dynamically adjusts DSL primitive search weights by following the steepest descent in the Fisher metric, moving hyperbolic parameters along geodesics.

---

## Lead Combinatorial Program Synthesizer (`qwen3.5:397b-cloud`)
**Duration**: 41.36s

*   **Connected Component Labeling (CCL) with Property-Based Permutation:** Compute 4-connected components $\mathcal{C} = \{C_1, \dots, C_k\}$ for all non-background colors. For each $C_i$, extract feature vector $\phi_i = (\text{area}(C_i), \text{centroid}_y(C_i), \text{color\_id}(C_i))$. Apply permutation $\sigma = \text{argsort}(\{\phi_i\})$ based on lexicographical comparison of $\phi$. Construct output grid $G'$ by placing components $C_{\sigma(i)}$ sequentially in raster-scan order, preserving intra-component relative coordinates $(x,y)$. Enables object-centric reasoning, sorting, and reordering distinct from global gravity.

*   **Obstacle-Constrained Geodesic Propagation:** Define seed set $S = \{p \mid G(p) \in \Sigma_{src}\}$ and barrier set $B = \{p \mid G(p) \in \Sigma_{stop}\}$. Compute distance map $D(p) = \min_{s \in S} (\text{shortest\_path}(s, p) \text{ s.t. path} \cap B = \emptyset)$ using BFS. Fill $G'(p) \leftarrow \text{color}(s^*)$ for all reachable $p$ where $D(p) \leq \tau$, where $s^*$ is the nearest seed source. Solves pathfinding, connectivity, and diffusion tasks where global gravity or topological hole filling fails due to intermediate obstacles.

*   **Wildcard Convolutional Pattern Replacement:** Define kernel $K \in \{0..9, *\}^{m \times n}$ and target transformation $T$. For each position $(i,j)$, if subgrid $G[i:i+m, j:j+n] \equiv K$ (where $*$ matches $\forall c \in \Sigma$), apply $T$ to target coordinate (e.g., $G'(i + \lfloor m/2 \rfloor, j + \lfloor n/2 \rfloor) \leftarrow c_{new}$). Execute synchronously across all $(i,j)$ to ensure deterministic state transitions. Encodes local cellular automata rules, noise removal, and context-dependent color logic.

---

## Game Theory & MCTS Principal Researcher (`kimi-k3:cloud`)
**Duration**: 63.2s

Core principle: chance nodes are *sampled*, never *expanded* — the tree branches only on information sets × actions, one trajectory per simulation, so width grows linearly in rollouts, not $\prod_t |C_t|$.

- **Single-observer ISMCTS nodes with regret-matching bandits (OOS-style CFR-in-MCTS).** Key each node by a canonical information-set hash $h(I)$ = (public action log, own hand multiset, opponent hand *count*, prize counts, revealed-card set, board state) — permutation-invariant over hidden identities, so transpositions merge and no hidden state ever forks the tree. This forces one policy per $I$, eliminating strategy fusion. At each node replace UCB with regret matching: $\sigma(I,a) = R_I^+(a)/\sum_b R_I^+(b)$ (uniform if $\sum = 0$, floor with $\varepsilon/|A(I)|$ for support). Back up the outcome-sampling counterfactual-regret estimator: for terminal utility $u$ reached with sampling reach $q(z)$, for every visited $I$ of player $i$ with sampled action $a'$: $R_I(a) \mathrel{+}= \frac{u_i(z)\,\pi_{-i}^\sigma(z)}{q(z)}\big(\mathbb{1}\{a{=}a'\} - \sigma(I,a)\big)$. This is Online Outcome Sampling (Lisý et al.): unbiased MCCFR updates executed only on the sampled path — vanilla CFR's full-width recursion disappears; convergence to Nash is preserved in 2p0s play.

- **Posterior-consistent lazy determinization, resolved on demand.** Maintain a constraint store over unseen-card multiset $U$: known-in-hand set $K$ (updated on every revealed tutor/search), exclusion set $E$ (discards, prizes taken), constrained deck slots (peek/reorder effects). Per simulation, draw opponent hand by sequential sampling without replacement from $U$ subject to $K, E$; do **not** materialize deck order or prize identities at simulation start — sample each deck draw at draw time (swap-with-last on an unseen-card array, O(1)) and instantiate a prize's identity only at the moment it is taken, since before observation its identity cannot affect any legal trajectory. Fresh determinization per simulation (never reuse across root iterations — that biases the regret estimates); this keeps determinization cost at O(#draws + #prizes taken) instead of O(|U|) and removes all chance branching by construction.

- **Reach-weighted average-strategy extraction + non-local backup, engineered to fit the 12.45 µs/rollout budget.** Accumulate $\bar{S}_I(a) \mathrel{+}= \frac{\pi_i^\sigma(z[I])}{q(z)}\sigma^t(I,a)$ and output $\bar\sigma(I,a) = \bar{S}_I(a)/\sum_b \bar{S}_I(b)$ — the $O(1/\sqrt{T})$ Nash bound holds for the reach-weighted average only, never the last iterate or raw visit counts. Leaf values are non-local: root-player utility ($\pm$1 or root-perspective heuristic), identical across determinizations, per Cowling et al.'s non-locality fix. Implementation: open-addressed tables (regret + avg-strategy arrays) keyed by the 64-bit IS hash, make/unmake with an undo log — never clone state (a full Pokémon board clone alone exceeds your per-rollout budget) — one mutable determinization object with a lazy cursor. Optionally add Schmid et al.'s outcome-sampling baseline $R_I(a') \mathrel{+}= W\,(u - b)$ for variance reduction; at ~80k rollouts/s this buys measurably lower policy variance per wall-clock second.

---

