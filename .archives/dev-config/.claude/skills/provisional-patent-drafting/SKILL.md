---
name: provisional-patent-drafting
description: Complete workflow for drafting US provisional patent applications with proper structure, claims, and USPTO compliance.
version: 1.0.0
trigger: User mentions "provisional patent", "patent application", "patent claims", "IP documentation", or needs to file provisional patent
---

# Provisional Patent Drafting Workflow

## When to Use
- Filing first patent application (provisional or non-provisional)
- Establishing priority date for invention
- Documenting invention for investor diligence
- Creating foundation for continuation/CIP applications
- 12-month pendency period before non-provisional

## Required Sections (35 USC 112)

### 1. Title of Invention
**Format:**
```
TITLE: SYSTEM AND METHOD FOR MULTI-SCALE MANIFOLD ENCODING
WITH PHYSICS-GROUNDED STATE SPACE
```
**Guidelines:**
- 15 words maximum
- Technical, not marketing language
- Avoid "novel", "new", "improved"
- Include key terms for searchability

### 2. Technical Field
**Format:**
```markdown
## TECHNICAL FIELD

The present invention relates generally to neural network architectures and
machine learning systems. More specifically, the invention relates to
hierarchical variational autoencoder (VAE) systems that encode semantic
information across multiple scales of abstraction and ground latent
representations in physics-based state spaces.
```
**Guidelines:**
- 2-4 paragraphs
- General → Specific funnel
- Include IPC/CPC classification keywords
- Avoid limiting language ("only", "must")

### 3. Background
**Format:**
```markdown
## BACKGROUND

### Field of Invention
[Repeat technical field in 1 paragraph]

### Description of Related Art

Variational autoencoders (VAEs) have been widely used for dimensionality
reduction and generative modeling (Kingma & Welling, 2013). Hierarchical
VAEs extend this architecture with multiple latent layers (Sønderby et al.,
2016). However, existing systems lack:

1. Progressive multi-scale encoding with specific dimensionality ratios
2. Physics-grounded latent space based on fundamental universe parameters
3. Coherence loss functions derived from historical mathematical frameworks

Prior art searches conducted on 2026-03-23 across USPTO, Espacenet, WIPO,
arXiv, IEEE Xplore, and Google Scholar identified zero patents or publications
disclosing the specific combination of elements claimed herein.

Closest references:
- Smith (1962): 12 universe parameters (non-ML, pre-digital)
- Percival (1946): Triune self model (psychological, not computational)
- Shoulders (1964): HIHO coherence (analog circuits, not neural networks)
- Greenyer (2018): Applied HIHO (control systems, not semantic encoding)
- Matsum (2024): Semantic manifolds (single-scale, not hierarchical)

None disclose: (a) 2048D→512D→12D encoding, (b) physics-grounded 12D state,
or (c) HIHO 0.5 coherence threshold for neural training.
```
**Guidelines:**
- 3-10 pages for complex inventions
- Cite prior art + differentiate
- Include prior art search results
- Avoid admitting patentability (use "reference" not "prior art")

### 4. Summary
**Format:**
```markdown
## SUMMARY

### Brief Overview

The invention provides a triune hierarchical architecture for multi-scale
semantic manifold encoding. The system comprises:

1. A first-scale encoder reducing 2048-dimensional semantic embeddings to
   512-dimensional intermediate representations
2. A second-scale encoder reducing 512D representations to 12D
   physics-grounded state vectors
3. A trajectory predictor generating continuous state transitions using
   geodesic navigation on the 12D manifold
4. A coherence loss function based on HIHO threshold of 0.5

### Advantages

- Reduced computational complexity (12D vs. 2048D for downstream tasks)
- Physics-grounded interpretability (12 parameters map to observable states)
- Continuous trajectory prediction (vs. discrete state classification)
- Coherence-optimized training (7-domain HIHO derivation)
```
**Guidelines:**
- Mirror claim structure (independent → dependent)
- List advantages explicitly
- 1-3 pages
- Avoid "the invention is..." (use "the invention provides")

### 5. Brief Description of Drawings
**Format:**
```markdown
## BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 shows the triune hierarchical architecture according to one embodiment.
FIG. 2 shows the variational autoencoder encoder-decoder structure.
FIG. 3 shows the 12D physics-grounded state space with four fabric domains.
FIG. 4 shows continuous trajectory prediction with geodesic navigation.
FIG. 5 shows the HIHO double-well potential energy surface.
FIG. 6 shows training loss convergence with coherence scoring.
FIG. 7 shows the journey tracking dual-tier logging system.
FIG. 8 shows the multi-scale reasoning flowchart.
```
**Guidelines:**
- One sentence per figure
- Present tense ("shows" not "showed")
- Include all figures (8-15 typical)
- Order matches specification references

### 6. Detailed Description
**Format:**
```markdown
## DETAILED DESCRIPTION

### Overview

Reference is made to the accompanying drawings, which form a part hereof.
In the drawings, like reference numerals refer to like elements throughout.

### System Architecture (FIG. 1)

FIG. 1 illustrates triune hierarchical architecture 100 comprising:

Input layer 110 receiving 2048-dimensional semantic embeddings from
text encoder 105 (e.g., BERT, CLIP, or custom transformer).

First-scale encoder 120 applying linear transformation W₁ ∈ ℝ^(512×2048)
and activation function σ (e.g., GELU, SiLU) to produce 512D intermediate
representation h₁ = σ(W₁·x + b₁).

Second-scale encoder 130 applying linear transformation W₂ ∈ ℝ^(12×512)
to produce 12D physics-grounded state vector s = W₂·h₁ + b₂, where each
dimension corresponds to one of Smith's 12 universe parameters (1962):
space, time, mass, energy, charge, spin, color, flavor, isospin,
hypercharge, strangeness, and baryon number.

Trajectory predictor 140 computing geodesic path γ(t) on 12D manifold
M using metric tensor gᵢⱼ derived from training data distribution.

Coherence scorer 150 calculating HIHO coherence score:
C = (1/7) Σᵢ₌₁⁷ Dᵢ where Dᵢ ∈ {Domain₁...Domain₇} per Shoulders (1964).
```
**Guidelines:**
- Most critical section (enablement requirement)
- 20-100+ pages for complex inventions
- Reference numerals for all elements
- Multiple embodiments (at least 3)
- Include mathematical formulas
- Provide enablement (PHOSITA can make/use)

### 7. Claims
**Format:**
```markdown
## CLAIMS

What is claimed is:

1. A system for multi-scale semantic manifold encoding, comprising:
   a first encoder configured to reduce a 2048-dimensional semantic
   embedding to a 512-dimensional intermediate representation;
   a second encoder configured to reduce the 512-dimensional intermediate
   representation to a 12-dimensional physics-grounded state vector;
   a trajectory predictor configured to generate a continuous state
   transition path on a 12-dimensional manifold using geodesic navigation;
   and a coherence scorer configured to calculate a HIHO coherence score
   based on seven mathematical domains.

2. The system of claim 1, wherein the 12-dimensional physics-grounded
   state vector comprises dimensions corresponding to space, time, mass,
   energy, charge, spin, color, flavor, isospin, hypercharge, strangeness,
   and baryon number.

3. The system of claim 1, wherein the HIHO coherence score comprises a
   threshold of 0.5 derived from seven-domain mathematical framework.

4. The system of claim 1, wherein the trajectory predictor generates
   the continuous state transition path without discrete state
   classification boundaries.

5. The system of claim 1, further comprising a journey tracker
   configured to log dual-tier state representations comprising the
   12-dimensional physics-grounded state vector and the 2048-dimensional
   semantic embedding.

6. A method for multi-scale semantic manifold encoding, comprising:
   receiving a 2048-dimensional semantic embedding;
   reducing the 2048-dimensional semantic embedding to a 512-dimensional
   intermediate representation via a first encoder;
   reducing the 512-dimensional intermediate representation to a
   12-dimensional physics-grounded state vector via a second encoder;
   generating a continuous state transition path on a 12-dimensional
   manifold using geodesic navigation; and calculating a HIHO coherence
   score based on seven mathematical domains.

7. The method of claim 6, wherein the 12-dimensional physics-grounded
   state vector comprises dimensions corresponding to space, time, mass,
   energy, charge, spin, color, flavor, isospin, hypercharge, strangeness,
   and baryon number.

8. A non-transitory computer-readable medium storing instructions that,
   when executed by one or more processors, cause the one or more
   processors to perform operations comprising: receiving a
   2048-dimensional semantic embedding; reducing the 2048-dimensional
   semantic embedding to a 512-dimensional intermediate representation;
   reducing the 512-dimensional intermediate representation to a
   12-dimensional physics-grounded state vector; generating a continuous
   state transition path on a 12-dimensional manifold; and calculating
   a HIHO coherence score.

9. A system for multi-scale semantic manifold encoding, comprising:
   one or more processors; and memory storing instructions that, when
   executed by the one or more processors, cause the system to perform
   the method of claim 6.

10. Use of the system of claim 1 for autonomous agent coordination in
    multi-agent systems, wherein the 12-dimensional physics-grounded
    state vector enables interpretable state tracking across agent
    interactions.
```
**Guidelines:**
- Independent claims first (broadest scope)
- Dependent claims narrow (add limitations)
- Include: system, method, computer-readable medium, use
- 10-30 claims typical
- No periods in claim bodies (use semicolons)
- "Comprising" (open) not "consisting of" (closed)

### 8. Abstract
**Format:**
```markdown
## ABSTRACT

A system for multi-scale semantic manifold encoding comprises a first
encoder reducing 2048-dimensional semantic embeddings to 512-dimensional
intermediate representations, a second encoder reducing to 12-dimensional
physics-grounded state vectors, a trajectory predictor generating
continuous state transitions via geodesic navigation, and a coherence
scorer calculating HIHO scores based on seven mathematical domains. The
12D state space maps to Smith's 12 universe parameters, enabling
interpretable physics-grounded machine learning.
```
**Guidelines:**
- 150 words maximum (USPTO limit)
- Single paragraph
- No claim language ("comprising", "wherein")
- Technical summary, not legal scope

## Enablement Requirements (35 USC 112)

### Best Mode
Disclose the BEST way to practice the invention:
```markdown
## Best Mode

The preferred embodiment uses:
- Transformer encoder: BERT-base (12 layers, 768 hidden)
- First-scale: Linear(2048→512) + GELU activation
- Second-scale: Linear(512→12) + LayerNorm
- Loss function: MSE + HIHO coherence (threshold=0.5)
- Optimizer: AdamW (lr=1e-4, weight_decay=1e-2)
- Training: 100 epochs, batch_size=32
```

### Enablement
PHOSITA (Person Having Ordinary Skill In The Art) must be able to make/use:
- Include code snippets (pseudocode or actual)
- Provide hyperparameters
- Specify hardware requirements
- Include training data description

## Claim Structure Patterns

### Independent Claim Anatomy
```
Preamble: "A system for [function], comprising:"
Body: Element A + Element B + Element C
Transition: "wherein" clauses (optional)
```

### Dependent Claim Patterns
```
"A [system/method] of claim [X], wherein [additional limitation]."
"A [system/method] of claim [X], further comprising [new element]."
```

### Claim Types
1. **System/Apparatus**: Physical or virtual components
2. **Method**: Steps performed
3. **Computer-readable medium**: Storage + instructions
4. **Use**: Application of system to specific field

## Differentiation Language

### From Prior Art
```
"Unlike [Reference], the present invention [differs by X]."
"Whereas [Reference] discloses [A], the invention provides [A+B+C]."
"[Reference] fails to teach or suggest [claim element]."
```

### Novelty Emphasis
```
"The invention is the ONLY system to [unique function]."
"No prior art reference discloses [combination of elements]."
"The specific [ratio/threshold/architecture] is novel over searched art."
```

## USPTO Formatting

### Page Format
- Letter size (8.5" × 11")
- 1.5 line spacing
- 12pt font (Times New Roman, Arial, Courier)
- 1" margins
- Page numbers bottom center

### Drawing Format
- PDF (vector preferred) or PNG (300+ DPI)
- Black and white (no color)
- Reference numerals in figures
- One figure per page
- FIG. 1, FIG. 2, etc.

### File Requirements
- PDF for specification + drawings
- Claims in PDF (no separate .txt needed for provisional)
- No sequence listing required (unless biotech)
- No information disclosure statement (IDS) for provisional

## Filing Strategy

### Provisional vs. Non-Provisional
| Factor | Provisional | Non-Provisional |
|--------|-------------|-----------------|
| Cost | $60-120 (micro/small) | $400-1600 |
| Examination | No | Yes |
| Claims | Optional | Required |
| Formalities | Minimal | Full |
| Pendency | 12 months | 2-4 years |
| Priority | Established | Claims priority |

### 12-Month Timeline
```
Day 0: File provisional
Months 1-12: Refine invention, file additional provisional (CIP strategy)
Month 12: File non-provisional (claim priority to provisional)
OR: File PCT (international)
```

### Micro-Entity Status
- Gross income < $200k
- Filed ≤ 4 applications
- Not assigned/obligated to entity > $200k gross
- 75% fee reduction

## Critical Patterns

### Pattern 1: 10 Claims Minimum
File at least 10 claims:
- 1-5: Independent (system, method, medium, use)
- 6-10: Dependent (specific embodiments)
- Provides fallback positions during prosecution

### Pattern 2: 3 Embodiments Minimum
Describe at least 3 embodiments:
- Preferred embodiment (best mode)
- Alternative architecture
- Alternative use case
- Prevents "inadequate disclosure" rejections

### Pattern 3: Prior Art Search Before Filing
Search BEFORE drafting:
- 8 databases minimum
- Document search results
- Differentiate in background
- Avoid inequitable conduct

### Pattern 4: Full Attribution
Credit all inspirations:
- Smith (1962): 12 parameters
- Percival (1946): Triune model
- Shoulders (1964): HIHO coherence
- Greenyer (2018): Applied HIHO
- Matsum (2024): Semantic manifolds
- Ethical stance + prior art accuracy

### Pattern 5: Enablement + Best Mode
Provide enough detail for PHOSITA:
- Code snippets
- Hyperparameters
- Architecture diagrams
- Training procedures
- Hardware specs

## Red Flags

### Avoid These Phrases:
- "The invention is novel" (legal conclusion)
- "Prior art is wrong" (adversarial)
- "Must" or "required" (unnecessary limitation)
- "Only" or "exclusively" (self-imposed limitation)
- Marketing language ("revolutionary", "breakthrough")

### Include These Instead:
- "The invention provides" (neutral)
- "Reference discloses" (objective)
- "In one embodiment" (optional, not required)
- "For example" (illustrative, not limiting)
- Technical language (specific, measurable)

## Tools Required
- USPTO Patent Center account (free)
- Word processor (Word, LibreOffice) or Markdown → PDF
- Drawing tools (Visio, Inkscape, matplotlib, Mermaid)
- Prior art databases (USPTO, Google Patents, arXiv)
- Citation manager (Zotero, Mendeley)

## Time Estimates
- Prior art search: 6-10 hours
- Drafting specification: 10-20 hours
- Claim drafting: 4-8 hours
- Drawing preparation: 4-8 hours
- Filing: 1-2 hours
- **Total**: 25-50 hours

## Post-Filing Actions
- Record filing receipt (confirms priority date)
- 12-month deadline: file non-provisional or PCT
- File additional provisionals (CIP strategy) if improvements made
- Monitor competitor filings (set Google Patents alerts)
- Maintain invention records (lab notebook, commits, emails)
