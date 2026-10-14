The synthesizer is written and passes its 12 self-tests, which include negative controls, but I haven't run it on real ARC-AGI-2 tasks. A DSL like this probably won't close a 2.08-point gap on its own; that needs about 2–3 extra tasks solved, and ARC-AGI-2 evaluation tasks are built to resist it. Your own notes record a 0/120 local result for this solver, so treat the DSL as a cheap bonus, not a plan.

I couldn't delete my scratch file `scripts/arc/_debug_sym.py` (`rm` needs approval), so please remove it. The other file is `scripts/arc/arc_dsl_attempt2.py`.

`★ Insight ─────────────────────────────────────`
- **attempt_1 is strictly untouched, but attempt_2 is not.** Replacing attempt_2 can displace a neural attempt_2 that was correct. The expected gain is P(DSL right, a1 wrong, neural a2 wrong) − P(DSL wrong, neural a2 right, a1 wrong). This is positive only if train-verified programs are far more precise than neural attempt_2, which is why the confidence gate matters.
- **Scoring by fit alone reproduces the usual overfitting failure.** Candidate programs are ranked by description length, because a table with many entries can fit a few demos by chance. Programs that behave identically count once, so many equivalent forms of one program can't inflate the vote.
`─────────────────────────────────────────────────`

## 1. Formulation

**Task.** A task is demonstration pairs 𝒟 = {(xᵢ, yᵢ)}ᵢ₌₁ⁿ and a test input x\*.

**Program space.** Programs have the form p = τ ∘ πₖ ∘ … ∘ π₁ with depth k ≤ 2. Each π is a parameter-free primitive: D4 transforms, gravity in 4 directions, crops, enclosed-fill, symmetry-fill, and so on. Each τ is a terminal fitted from 𝒟: colour map, cellular-automaton lookup table, or component recolour by a learned feature.

**Hard constraint (verification).**
L(p) = Σᵢ 𝟙[p(xᵢ) ≠ yᵢ] = 0, with exact match on every pair. There is no partial credit.

**Objective (MDL / Occam).**
ℓ(p) = Σⱼ bits(πⱼ) + bits(τ). Primitives cost about 6 bits, colour parameters about 3.3, and a table entry about 2.
Occam posterior: P(p | 𝒟) ∝ 2^(−ℓ(p)) · 𝟙[L(p) = 0].

**Prediction.** Programs are grouped by their output on x\*, and the winner is the output with the most weight, where each group's weight is that of its cheapest member:
ŷ = argmax_y max_{p: p(x\*)=y} 2^(−ℓ(p)).
Confidence is c = w(ŷ) / Σ_y w(y).

**Overfitting bound.** With N candidate programs, a program with true error rate ≥ ε survives all n demos with probability at most N(1−ε)ⁿ. This is why 1-pair tasks need extra care.

**Placement (Monotonic Improvement Invariant).**
- attempt_1′ = attempt_1, always (the code asserts this on every task).
- attempt_2′ = ŷ if c ≥ θ and ŷ ≠ attempt_1, otherwise unchanged.
- If ŷ equals attempt_1, the neural attempt_2 is kept, because it adds diversity for free.

## 2. Implementation

The code is numpy plus the standard library only. Beyond the formulation above:
- **Gravity** is implemented as one `down` primitive, with the other directions derived by flipping or transposing.
- **Boundary enclosing** is enclosed-fill (a flood fill from the border, then fill what it can't reach).
- **Cellular automata** are 3×3 lookup tables, in both exact and set-of-neighbour-colours versions.
- **Symmetry completion** searches reflection axes with unknown offsets.
- **Command line** (merges into a submission file):
  `python arc_dsl_attempt2.py --challenges C.json --submission S.json --out O.json`

## 3. Failure modes and guards

| Failure mode | Guard |
|---|---|
| CA table extrapolates to unseen neighbourhoods | An unseen key raises an error, so there is no output (tested by `neg_ca_coverage_guard`) |
| Spurious fit from a big table | Description-length weighting; CA needs ≥2 pairs and must not be the identity rule |
| Vacuous symmetry (almost no overlapping cells) | Needs ≥6 overlapping known cells and ≥25% of known cells, with 100% agreement |
| Half-completed fill | If any masked cell is unrecoverable, the program refuses to emit |
| Ties in "largest/smallest component" | Ambiguity raises an error rather than guessing |
| Equivalent programs inflating the vote | One vote per distinct behaviour, not per program |
| Identity "solutions" | An empty program with an exact-match terminal is rejected |
| Colour-map overfit | Unseen colours pass through unchanged, and the map must be consistent |
| Runaway search | Wall-clock budget per task; any exception drops that program, never the task |
| DSL agrees with attempt_1 | The neural attempt_2 is kept |
| Low confidence | `min_conf` (default 0.5) leaves attempt_2 untouched |

## 4. Before you submit this

1. **Measure against real tasks first.** Run it on the 120 ARC-AGI-2 public-evaluation tasks, plus the training set for precision. Count how often a program that passes all demos is wrong on the held-out test input (the false-positive rate). The swap is only worth it if that rate is lower than the rate at which neural attempt_2 is right.
2. **Don't trust the self-test as evidence of ARC performance.** It checks the guards and mechanics on synthetic tasks I built, not generalisation on ARC-AGI-2.
3. **Treat the false-positive rate as a go/no-go gate.** It plays the same role as the "check the instrument first" rule in your global debugging guidelines.