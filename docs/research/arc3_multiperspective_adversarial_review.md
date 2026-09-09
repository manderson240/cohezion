# 🛡️ ARC-AGI-3 Multi-Perspective Adversarial Review & Solver Blueprint

**Date**: 2026-08-24  
**Review Fleet**: Local Radeon 8060S (`gpt-oss-20b`), DeepSeek-V4 Pro Cloud (1.6T), Qwen-397B Cloud  

## Perspective: Adversarial Kaggle Competitor & ARC Grandmaster
**Model**: `gpt-oss-20b-mxfp4-GGUF` (lemonade) | **Duration**: 31.58s

**Three concrete failure modes**

| # | Transformation | Why the synthesizer trips |
|---|----------------|-----------------------------|
| 1 | **Diagonal symmetry** – a pattern that is invariant under a 90° rotation about the grid centre. | The search treats the rotated state as a new node; invariant checks that only compare raw pixel arrays miss the symmetry, so the solver explores a 4× larger search space and never re‑uses the same sub‑solution. |
| 2 | **Gravity with obstacles** – a “fall” operation that stops when an obstacle is hit, but the solver assumes free‑fall to the bottom. | The AST invariant only checks final positions, not intermediate “collision” states. The search therefore accepts programs that would crash on a real run because the obstacle‑aware fall is not encoded. |
| 3 | **Color re‑indexing** – the same semantic colour is encoded with

---

## Perspective: Formal Verification & AutoHarness Architect
**Model**: `deepseek-v4-pro:cloud` (ollama_cloud) | **Duration**: 15.53s

1. **Total Typing & Shape Closure Invariant**  
   For every AST node \(n\), infer a static type \(\tau(n)\) from the finite set  
   \[
   \tau \in \{\text{Grid}(h,w)\mid 0\le h,w\le 30\} \cup \{\text{Int}[0,9]\} \cup \{\text{Bool}\} \cup \{\text{List}(\tau)\}
   \]
   and require every operator application to be total for its operand types.  
   No partial functions — e.g. `head`, `/`, `sqrt`, `reshape` with mismatched cardinality — are allowed unless guarded by a statically proved precondition.  
   *Violation ⇒ reject.* This eliminates `TypeError`, `ValueError`, shape mismatch, and division-by-zero crashes.

2. **Affine Bounds-Safety Invariant**  
   For every grid access \(A[i,j]\) or slice \(A[i_1:i_2,\ j_1:j_2]\), compute interval bounds via lightweight interval arithmetic:
   \[
   i \in [lo_i, hi_i],\quad j \in [lo_j, hi_j]
   \]
   and require
   \[
   0 \le lo_i \le hi_i < h,\qquad 0 \le lo_j \le hi_j < w
   \]
   where \(h,w\) are the static dimensions of \(A\).  
   All coordinate expressions must be affine with coefficients in \(\{-1,0,1\}\) and constants bounded by \(30\).  
   *Violation ⇒ reject.* This eliminates `IndexError` and out-of-bounds slice crashes.

3. **Syntactic Termination & Cost-Bound Invariant**  
   Every loop must be of the form `for x in range(e)` with \(e\) a static constant or affine bound \(\le 30^2\).  
   Every recursion must have a syntactic measure \(m\) that decreases by at least \(1\) per call and has a statically reachable base case.  
   Compute a static cost \(C(n)\) by structural recursion:
   \[
   C(\text{loop}) = \text{trip count} \times C(\text{body}),\qquad C(\text{root}) \le 10^4
   \]
   *Violation ⇒ reject.* This guarantees termination and bounds execution time below the sub-millisecond pruning threshold.

All three rules are checked in a single bottom-up AST pass in \(O(|\text{AST}|)\), so rejection happens before any execution and costs microseconds, not milliseconds.

---

## Perspective: Kaggle Runtime & Compute Efficiency Engineer
**Model**: `qwen3.5:397b-cloud` (ollama_cloud) | **Duration**: 49.05s

1.  **Enforce Iterative Search with Strict Node Budgets**
    Recursion is a stack overflow vulnerability. Ban it. Implement iterative BFS/DFS with a hard cap on expanded nodes per task: $N_{expanded} \leq 5 \times 10^5$. ARC priors exhibit combinatorial explosion ($O(b^d)$); without truncation, worst-case tasks guarantee TLE. If a solution requires exceeding $N_{max}$, your prior is inefficient—discard it, do not scale hardware.

2.  **Maintain Memory Invariance ($\Delta M \leq 0$)**
    `grid.copy()` and dynamic caching are memory leaks. Use pre-allocated buffers and in-place mutations (`out=` parameters). Total heap usage must remain constant throughout the solve loop: $M(t) \approx M_{init}$. OOM occurs when caching intermediate states across tasks; purge all state between tasks. If memory grows linearly with task index, you fail.

3.  **Install Hard Wall-Clock Interrupt (`SIGALRM`)**
    The 9-hour limit is a cliff, not a boundary. Set `signal.alarm(30600)` (8.5 hours) immediately at entry. This forces graceful termination before the Kaggle kernel killer terminates you mid-write, corrupting submission files. Relying on the platform killer is amateur; deterministic self-termination is engineering.

---

