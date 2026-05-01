# Nemotron Symbolic Solver — Optimization Plan
## Target: Break 54.6% → 60%+ baseline (prize: $106K, deadline: 2026-06-15)

---

## Current Baseline (Audit)

| Type | Count (est.) | Symbolic Accuracy | Impact on Total |
|------|-------------|-------------------|-----------------|
| Numeral | ~1,600 | **100%** | ~16.8 pts |
| Unit Conversion | ~1,900 | **82.5%** | ~16.5 pts |
| Gravity | ~1,500 | **72.2%** | ~11.4 pts |
| Bit Manip | ~2,000 | **30.7%** | ~6.5 pts |
| Encryption | ~1,800 | **32.1%** | ~6.1 pts |
| Equations | ~700 | **~0.5%** | ~0.0 pts |
| **Total** | **~9,500** | **~54.6%** | **~58 pts of 95** |

*Note: There is a discrepancy in the codebase — `kaggle_pure_symbolic.py` claims ~63.1%, while `README_SUBMISSION.md` reports ~54.6%. The latter is assumed more recent and validated.*

**Model fallback (Gemma-4 26B 4-bit via Lemonade) adds only +0.8%**, confirming that local model serving is not viable on Kaggle CPU and the symbolic solver is the only practical path.

---

## High-Impact Opportunities (Ranked by Expected Δ)

### 1. BIT MANIP — 30.7% → Target: 55-70% (Expected: **+5 to +8 pts overall**)

**Why it's low:**
- Only unary ops + 2-op compositions are searched.
- Missing: bitwise MUX, per-bit table (LUT 8→8), multi-input gates, non-trivial permutations.
- Affine search is narrow (only XOR/AND/OR/ADD with constant).

**Optimizations:**

a) **LUT-8 search** — For each of the 8 output bits, compute its truth table from all 8 input bits. With only a few (2-4) examples, every bit position can be expressed as a 8-input Boolean function → truth table of 256 entries. We can brute-force all 2^(2^8) = 2^256 impossible, but for each output bit we can enumerate all 2^(2^k) where k are actually-referenced input bits. With k≤3 that's 2^8 = 256 per bit, trivial.

b) **Widen unary op list** — Add: `popcount`, `parity`, `nibble swap`, `bit reversal in nibble`, `gray_code`, `degray_code`, `leading_zero_count` (mod 8), `mod_n` ops.

c) **3-op composition search** — Current 2-op is ~400 combos. 3-op is ~8,000 but only for cases where 2-op failed and we have time budget.

d) **Per-bit truth-table synthesis** — Instead of trying to map each output bit to a single input bit, synthesize each output bit as any Boolean expression over input bits up to depth 2 (AND/OR/NOT/XOR of input bits and constants).

e) **Known common bit-manip patterns** — Pre-populate a lookup table of known competition patterns: `x ^ ROTL(x, n)`, `x & ~x`, `bitwise complement of nibbles`, `parity byte`, `swap adjacent bits`, etc.

**Implementation priority:** LUT-8 per-bit truth table (highest expected return, lowest runtime cost).

---

### 2. ENCRYPTION — 32.1% → Target: 50-60% (Expected: **+3 to +5 pts overall**)

**Why it's low:**
- Vocabulary list is small (~200 words) and static.
- Word-level substitution fails when word boundaries shift or punctuation changes.
- No frequency analysis or constraint propagation beyond single-letter mapping.
- Dictionary completion picks `matches[0]` arbitrarily without confidence ordering.

**Optimizations:**

a) **Expand vocabulary** — Auto-extract vocabulary from known example outputs during runtime (not static list). This alone captures domain-specific words.

b) **Bigram/trigram completion** — Use character n-gram frequencies from example outputs to score candidate words, not just static vocabulary.

c) **Constraint propagation with backtracking** — Current greedy assignment can lock in wrong early mappings. Implement backtracking when ambiguous letters exist.

d) **Handle multi-word shifts** — Some encryptions may use Caesar/per-word rotation. Test character-shift offsets per position.

e) **Frequency-ordered candidate selection** — Instead of `matches[0]`, score by English letter frequency (etaoinshrdlu) and example-output frequency.

---

### 3. EQUATIONS — ~0.5% → Target: 15-25% (Expected: **+2 to +4 pts overall**)

**Why it's low:**
- Only 10 hardcoded arithmetic digit operations are tried.
- Symbol equations only try 10 structural rules (reverse, first+last, etc.).
- No expression tree search, no arithmetic with mixed operators.

**Optimizations:**

a) **Expression tree enumeration** — For number equations with 2 inputs, enumerate all binary trees of depth ≤2 over ops {+, −, ×, //, %, |, &, ^, max, min, concat, digit_sum, rev_concat}. That's ~15 ops × 2 orderings × few structures = ~90 candidates. Trivial to test.

b) **Digit-wise operations** — Try digit-wise add/sub/mul, mod 10, with and without carry. Also try taking max/min digit, sorting digits.

c) **Position-dependent symbol substitution** — For non-digit equations, try position-specific substitution (1st char→X, 2nd char→Y, repeating patterns).

d) **Arithmetic expression via Python eval with validation** — If the format looks like `expr = value`, evaluate expression candidates against known values.

e) **Sequence-based rules** — Check if output is subsequence, supersequence, or specific indices of input.

---

### 4. GRAVITY — 72.2% → Target: 85% (Expected: **+2 pts overall**)

**Why it's not higher:**
- Grid search around `g_ls` and per-example `g = 2d/t²` with steps [0.01, 0.005, 0.002, 0.001].
- If `g` is in a non-standard unit or the formula subtly differs (e.g., includes `t³` component, different gravity constant), this fails.
- Format precision detection is heuristic and occasionally picks wrong decimal places.

**Optimizations:**

a) **Try multiple physical models** — `d = 0.5*g*t²`, `d = g*t²`, `d = 0.5*g*t³` (edge case), `d = g*t`. Pick best fit by MSE.

b) **Precision voting with example-output exact match check** — Instead of purely formatting by most common decimal count, generate candidate outputs for all sensible g values and pick the one whose formatted output matches the *most* example outputs exactly.

c) **Use median g instead of mean** — If noise is present, per-example `g` estimates are outliers; use median not mean as candidate seed.

---

### 5. UNIT CONVERSION — 82.5% → Target: 90%+ (Expected: **+1 to +2 pts overall**)

**Why some fail:**
- Only linear `y = a*x + b` is tried.
- Some conversions could be non-linear (e.g., `y = a/x`, `y = a*sqrt(x)`, `y = a*x²`).

**Optimizations:**

a) **Try non-linear fits** — If linear fit residual is high, try `y = k/x`, `y = k*sqrt(x)`, `y = k*x²`, `y = k*log(x)`. Pick by lowest MSE.

b) **Dimensional suffix preservation** — Ensure output units match example outputs more robustly.

---

## Kaggle Execution Constraints (From `cohezion-kaggle-blackwell` Skill)

- **No GPU** (`"enable_gpu": false` in kernel-metadata.json). Model fallback is impractical.
- **No internet** (`"enable_internet": false`). No API calls.
- **CPU-only execution** → All optimizations must be pure Python, no heavy ML.
- **Time budget**: Pure Equal Division per problem. Currently the notebook runs "under a minute" for 9,500 problems. We have **~1.9s/problem** average budget on CPU (95% of 5 hours = 4h45m = 17,100s / 9,500 ≈ 1.8s/problem). Symbolic solvers are microseconds; we can afford more brute-force search.

---

## Proposed Implementation Order

| Phase | Focus | Expected Δ | Effort | Files |
|-------|-------|-----------|--------|-------|
| **P0** | Bit manip: LUT-8 per-bit truth table | **+4 to +6%** | 1 day | `solve.py`, `kaggle_pure_symbolic.py` |
| **P0** | Equations: expression tree enumeration (depth≤2) | **+2 to +3%** | 1 day | `solve.py`, `kaggle_pure_symbolic.py` |
| **P1** | Encryption: runtime vocab extraction + bigram scoring | **+2 to +3%** | 1-2 days | `solve.py`, `kaggle_pure_symbolic.py` |
| **P1** | Gravity: multi-model fit + median seed + precision voting | **+1 to +2%** | 0.5 day | `solve.py`, `kaggle_pure_symbolic.py` |
| **P2** | Unit conversion: non-linear fallback fits | **+0.5 to +1%** | 0.5 day | `solve.py`, `kaggle_pure_symbolic.py` |
| **P2** | Bit manip: expanded unary ops + 3-op compositions | **+1 to +2%** | 1 day | `solve.py`, `kaggle_pure_symbolic.py` |
| **P3** | Integration test on full training set | — | 0.5 day | `test_model.py` or new `evaluate.py` |

**Cumulative Target**: 54.6% → **62-67%**

---

## Testing & Validation Plan

1. **Local validation** — When `train.csv` becomes available, run `evaluate()` on full 9,500 samples before each submission.
2. **Per-type confusion matrix** — Track accuracy per problem type to confirm each optimization lands.
3. **Kaggle dry-run** — Use `kaggle_pure_symbolic.py` in offline mode, ensure runtime < 90s for 9,500 problems.
4. **Versioning** — Bump kernel version (currently v28) with each proven improvement.

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| LUT-8 search too slow on Kaggle CPU | Limit to k≤3 referenced inputs; use memoization; cap at 1ms/problem |
| Equation tree search explodes combinatorially | Cap depth at 2, inputs at 2; early exit on first match |
| Encryption vocab extraction produces garbage | Only extract words from **example outputs** (ground truth), not test inputs |
| Overfitting to training distribution | Keep solvers general (no hardcoded answers); test on held-out sample |
| Kernel timeout on Kaggle | Add per-iteration time guard; if budget < 0.5s/problem, skip expensive heuristics |

---

## Next Immediate Actions

1. **Implement LUT-8 bit-manip solver** in both `solve.py` and `kaggle_pure_symbolic.py`.
2. **Implement equation expression tree search** (depth ≤ 2, binary ops).
3. **Update encryption solver** to extract vocab from example outputs instead of static list.
4. **Run full training evaluation** (when data available) to quantify exact gain.
5. **Prepare Kaggle kernel v29** with P0 changes and submit.

---

*Plan created: 2026-04-28*
*Deadline: 2026-06-15 (7 weeks remaining)*
