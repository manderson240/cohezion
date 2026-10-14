## Adversarial Portfolio Review: Mike Anderson, Solo Competitor

**Overall verdict:** None of the four current approaches is on a trajectory to Top 5, let alone Top 1. The gaps are not incremental tuning gaps; they are architectural paradigm gaps. You are competing in the upper-middle of the pack with methods that are either too heuristic, too small-model, or too brute-force. The leaderboard gaps are not closable by polishing your current pipelines.

---

## 1. ARC Prize 2026: ARC-AGI-2

**Current:** 31.81%, Rank 245/2,630, Top 10 cutoff 33.89%, Top 1 83.61%

### Fundamental Ceiling & Self-Deception

Your pipeline is a **quantized 4-bit Qwen3-4B LoRA SFT on 139 tasks**, augmented with test-time training (TTT) and a second-attempt DSL injection filtered by D4 invariance.

- **LLM direct grid output is a dead end for ARC-AGI-2.**  
  ARC tasks are defined by compositional, out-of-distribution transformations. A 4B LLM fine-tuned on 139 examples is interpolating over surface patterns. It has no mechanism for exact counting, object tracking, conditional branching, or relational reasoning. The token-prediction objective does not enforce execution correctness.

- **TTT on 2–5 examples is statistically meaningless for a 4B model.**  
  You cannot update enough parameters to capture arbitrary transformations without destroying pretrained structure. LoRA rank is too small to represent the needed program space. TTT here is likely overfitting to spurious visual features in the few training grids, giving a false sense of adaptation.

- **D4 invariant filtering is mathematically misguided.**  
  The D4 group acts on spatial rotations/reflections of square grids. Requiring candidate transformations to be invariant under D4 assumes the task commutes with all spatial symmetries. Many ARC-AGI-2 tasks are not D4-equivariant: e.g., “move object left,” “gravity,” “count objects,” “color permutation.” Your filter will systematically reject correct non-equivariant transformations.

- **Monotonic Attempt-2 DSL injection is a bias amplifier.**  
  If Attempt-1 is wrong, injecting its output into Attempt-2 under a monotonic constraint forces agreement with a wrong prior. This can lock you into an incorrect solution space.

**You are deceiving yourself if you think you are 2–3 tasks from Top 10 and therefore close to the podium.** Top 10 is 33.89%, but Top 1 is 83.61%. That discontinuity is not a tuning gap; it indicates a completely different solver class. Your method is local to the LLM few-shot paradigm and will not cross that chasm.

### What Leaders Are Doing

- **Neural-guided program synthesis with execution verification.**  
  Top solutions likely generate candidate programs in a DSL or Python, execute them on training examples, and keep only candidates that match exactly. The LLM is used only to propose programs, not to output grids directly.

- **Object-centric graph rewriting.**  
  They segment objects, detect relations, and search over transformations at the object level, not pixel level. This drastically reduces the search space.

- **Massive synthetic training and RL/evolution.**  
  They train on millions of procedurally generated ARC-like tasks with compositional program structure, learning a library of reusable concepts. Test-time search is guided by learned value functions or MDL priors.

### Specific Failure Modes

- Counting, comparing lengths, color permutations, occlusion, and conditional branching are almost certainly failed.
- TTT may overfit to the few examples and produce confident but wrong outputs on the test grid.
- D4 filtering rejects valid non-symmetric transformations.
- Attempt-2 DSL injection can propagate errors from Attempt-1.

### Top 2–3 Highest-Leverage Breakthroughs

1. **Replace direct grid output with execution-verified program synthesis.**  
   Use the LLM to generate candidate DSL/Python programs. Execute on training examples. Discard any program that fails. Rank survivors by MDL or simplicity. This alone could move you from 31% to 50%+.

2. **Build object-centric representations and graph transformations.**  
   Stop treating grids as pixel arrays. Segment objects, extract properties (color, shape, position, relation), and search over object-level transformations. This is the core abstraction humans use.

3. **Train on synthetic ARC-like tasks with compositional program generation.**  
   Create a generator that produces tasks from known primitive transformations (rotation, reflection, color swap, splitting, counting, etc.). Fine-tune or RL-train the LLM to propose programs, not grids. Use execution feedback as reward.

---

## 2. Enveda CASMI26 Molecule ID from Mass Spectra

**Current:** 0.421 MRR, Rank 425/2,837, Top 5 0.455, Top 1 0.484

### Fundamental Ceiling & Self-Deception

Your pipeline is **rule-based analog propagation + MetFrag-lite fragment parsimony + PubChem candidate join + POP_MU popularity prior + RDKit tautomer canonicalization**.

- **No learned representation of spectra or molecular structure.**  
  MRR is dominated by ranking. Your scoring is a linear combination of heuristics with a global popularity prior. This cannot capture the complex relationship between fragmentation spectra and molecular structure. Top solutions use deep learning to predict molecular fingerprints or directly score candidates.

- **PubChem candidate join limits coverage.**  
  CASMI26 may include compounds absent from PubChem or with low popularity. Your popularity prior actively penalizes rare molecules, which are exactly the challenging unknowns in CASMI. If the true candidate is not in your candidate set, no ranking can save you.

- **MetFrag-lite fragment parsimony is a weak approximation.**  
  In silico fragmentation rules do not model bond dissociation energies, rearrangements, or adduct-specific fragmentation. It can assign high scores to wrong candidates that share common fragments.

- **Analog propagation can amplify noise.**  
  If similarity is based on Tanimoto fingerprints, propagating scores across analogs can boost incorrect structural neighbors with similar spectra.

**You are deceiving yourself if you think MRR 0.421 is close to Top 5.** The gap to 0.455 means moving the average reciprocal rank from 2.375 to 2.198. That requires many queries where the correct candidate moves from rank 2–3 to rank 1. Your heuristic pipeline lacks the discriminative power to do that.

### What Leaders Are Doing

- **Deep learning-based fingerprint prediction.**  
  They use models like SIRIUS/CSI:FingerID, MIST, or transformer-based encoders trained on large mass spectra databases (NIST, GNPS) to predict molecular fingerprints from spectra. Candidates are ranked by fingerprint similarity.

- **Expanded candidate generation.**  
  They enumerate all structures from the molecular formula using generative models or structure enumeration, include stereoisomers, and search beyond PubChem. They do not apply popularity as a hard filter.

- **Graph neural networks for direct candidate scoring.**  
  They model the molecular graph and the spectrum jointly, learning to score candidate structures directly from spectral peaks and fragmentation trees.

### Specific Failure Modes

- True candidate missing from PubChem or filtered out by popularity prior.
- Incorrect structural analogs boosted by analog propagation.
- MetFrag fragment parsimony assigns high score to wrong candidate with common fragments.
- Tautomer canonicalization may collapse distinct structures incorrectly if not carefully handled.

### Top 2–3 Highest-Leverage Breakthroughs

1. **Integrate a learned fingerprint predictor.**  
   Use a pretrained model (CSI:FingerID, MIST) or train your own on public mass spectra data to predict molecular fingerprints from spectra. Rank candidates by fingerprint similarity combined with spectral matching. This alone could lift MRR by 0.03–0.05.

2. **Expand candidate generation and remove popularity prior.**  
   Enumerate all structures from the molecular formula, include PubChem, ChemSpider, and generative models. Use the popularity prior only as a weak tie-breaker, not a multiplicative factor.

3. **Train a graph neural network on fragmentation trees.**  
   Model the molecular graph and fragmentation spectrum jointly. Use contrastive learning to align spectra and structures. This learns bond dissociation probabilities and can discriminate isomers.

---

## 3. RSNA Knee Abnormality Detection

**Current:** 0.943 AUC, Rank 1,242/5,546, Top 5 0.963, Top 1 0.964

### Fundamental Ceiling & Self-Deception

Your pipeline is **32-slice volumetric depth + multi-resolution (r224+r336) + CoAtNet/Raptor backbones + intra-column quantile rank normalization + Kolmogorov Monotonicity Projection**.

- **32-slice volumetric depth is not full 3D.**  
  Knee MRI volumes often contain >100 slices. Using only 32 slices can miss abnormalities located outside the selected range or requiring long-range context. Top solutions use full 3D volumes or multi-plane fusion.

- **r224+r336 is low resolution.**  
  Top solutions likely use 512×512 or higher. Small lesions (meniscal tears, bone marrow edema) may be invisible at low resolution.

- **CoAtNet/Raptor are strong but not enough alone.**  
  Without pretraining on medical images or large-scale self-supervised learning, these models may not extract the subtle features needed for high AUC.

- **Post-processing projections are unlikely to improve AUC.**  
  Quantile rank normalization within columns destroys cross-column scale information. Kolmogorov Monotonicity Projection assumes P(Abnormal) >= max P_k. If true, it can improve calibration, but it does not change ranking. If the model outputs are noisy, projection can introduce ties or bias, potentially hurting AUC.

**You are deceiving yourself if you think 0.943 is close to Top 5.** The gap of 0.021 AUC at this level is large. It requires a substantial reduction in false positives/negatives. Your single-model 2.5D approach is not competitive with the ensemble of full 3D models used by leaders.

### What Leaders Are Doing

- **Full 3D multi-plane models.**  
  They process entire volumes with 3D CNNs or Transformers, often fusing sagittal, coronal, and axial branches. This captures contextual information across all slices and planes.

- **Large ensembles with diverse architectures.**  
  Top solutions likely ensemble 10+ models with different architectures, resolutions, seeds, and TTA. They stack predictions using logistic regression on OOF predictions.

- **Auxiliary tasks and pretraining.**  
  They use segmentation of knee structures, slice-level classification, or contrastive learning to improve representations. Pretraining on RadImageNet or Med3D gives a significant boost.

### Specific Failure Modes

- Missing small meniscal tears or bone marrow lesions that appear on only a few slices or planes.
- Overfitting to public LB due to small dataset; private gap could be larger.
- Quantile rank normalization may remove informative scale differences between columns.
- Monotonicity projection may be wrong if abnormal prediction relies on global context not captured by max of sub-probabilities.

### Top 2–3 Highest-Leverage Breakthroughs

1. **Move to full 3D multi-plane models.**  
   Process entire volumes with 3D ResNet/CoAtNet. Fuse sagittal, coronal, axial branches. Use all slices. Pretrain on medical imaging datasets.

2. **Ensemble diverse models with TTA.**  
   Train multiple architectures at different resolutions (e.g., 384, 512) with different seeds. Use test-time augmentation (flips, rotations, intensity scaling). Stack predictions with logistic regression on OOF predictions.

3. **Incorporate auxiliary segmentation tasks.**  
   Use available annotations or generate pseudo-labels for knee structures and abnormalities. Multi-task learning improves feature learning and generalization.

---

## 4. ARC Prize 2026: ARC-AGI-3 Interactive Agent

**Current:** 0.26 best, recent 0.10–0.12, Rank 2,481/4,017, Top 1 55.89%

### Fundamental Ceiling & Self-Deception

Your pipeline is **Directed Affordance Rarity Search + SplitMix64 Zobrist state hashing + 1-cycle/2-cycle/3-6 cycle Markov anti-cycle penalties on Kaggle CPU**.

- **This is brute-force random search with novelty bias.**  
  Directed Affordance Rarity Search is essentially a randomized graph search. Zobrist hashing is just efficient state caching. Markov anti-cycle penalties are tabu search heuristics. None of these provide semantic understanding, goal inference, or hierarchical planning.

- **The state space is astronomically large.**  
  For tasks requiring long action sequences, random search has negligible success probability. The branching factor and depth make exhaustive search impossible on Kaggle CPU.

- **Score collapse from 0.26 to 0.10–0.12 indicates instability and overfitting.**  
  Your hyperparameters were likely tuned to specific tasks. The method is not robust across the task distribution.

**You are deceiving yourself if you think this is a viable path.** Top 1 is 55.89%; you are at 0.26 best. This is not a tuning gap; it is a paradigm gap. Your method is not in the same class as the leaders.

### What Leaders Are Doing

- **LLM-based agents with environment feedback.**  
  They use large pretrained models to understand task instructions and plan actions. The LLM proposes actions, receives observations, and adjusts. Search is used only as backup or verification.

- **Model-based reinforcement learning.**  
  They learn a world model of the environment and use MCTS or model-predictive control to plan. This allows long-horizon reasoning.

- **Hierarchical decomposition and skill reuse.**  
  They segment tasks into subgoals, learn reusable skills, and apply them across tasks.

### Specific Failure Modes

- Random search fails on tasks requiring long action sequences.
- Anti-cycle penalties may trap in local optima; no goal-directedness.
- No learning from past episodes; no transfer across tasks.
- Score collapse suggests hyperparameters are brittle.

### Top 2–3 Highest-Leverage Breakthroughs

1. **Integrate an LLM-based planner/agent.**  
   Use a pretrained LLM to propose actions based on observations and instructions. Use environment feedback to correct errors. This is the most direct path to competitive performance.

2. **Learn a world model or use model-based RL.**  
   Train on interactions to predict state transitions and rewards. Use MCTS or model-predictive control to plan actions. This enables long-horizon reasoning.

3. **Develop hierarchical decomposition with subgoal generation.**  
   Segment tasks into subgoals, use symbolic operators, and reuse skills across tasks. This reduces the effective depth of search.

---

## Portfolio-Level Truths

- **You are spread too thin.** As a solo competitor, you cannot compete with teams that have specialized expertise and compute. Focus on one or two competitions where you have a real chance.

- **Your methods are either too heuristic (ARC-AGI-3, Enveda) or too small-model (ARC-AGI-2, RSNA).** You need to adopt the dominant paradigm in each field: program synthesis for ARC, deep learning for mass spectra and medical imaging, and LLM agents for interactive tasks.

- **Post-processing tricks (D4 filtering, monotonicity projection, popularity prior, anti-cycle penalties) are band-aids.** They cannot compensate for fundamental architectural limitations. You need to replace the core, not tune the edges.

- **Your current ranks are not close to podium.** Top 5 in any of these competitions requires a step change in method, not incremental improvement. Be honest about that.