Done. File at /home/mike-anderson/dev/cohezion/anatomical_copula_coupling.py (self-contained: numpy + pandas only, no scipy).

Verified:
- AST parse clean, write_file syntax check passed
- Unit test ran green — 6 assertions: shape/columns/range, determinism, ~uniform margins, alpha_shrink=0 recovers independent ranking exactly, tie-break boost, true-negative monotonicity
- Boost demo: two rows with identical own ACL score but divergent contusion/effusion re-order 0.433 → 0.547 on ACL

What the module does, in one line each:
1. Independent rank(pct=True) per column discards companion-column signal from each column's ordering; for rank-AUC the tie-break between equal-own-score samples is the only place that signal can enter.
2. Coupling matrix C = (1-shrink)·Spearman(probit(ranks)) + shrink·anatomical-prior (unit coupling on the 6 edges: ACL-Contusion, ACL-Effusion, Contusion-Effusion, MedMen-MedOA, LatMen-LatOA, Effusion-Synovitis), projected PSD.
3. Boost = z_j* = (1-α)z_j + α·C[j,-j](C[-j,-j]+ρI)⁻¹z[-j] (Gaussian-copula conditional mean), then re-rank — monotone in each companion with positive weight, so silent true negatives stay low while companion-heavy candidates lift.

Honest bound: this only adds signal orthogonal to each column's own prediction. If both arms already capture the co-pathology structure, the gain is ~0. The 0.943 → 0.950 target is reachable only to the extent companions carry genuine extra information, and only if alpha_shrink (and shrink) are tuned on out-of-fold validation — I left both as explicit knobs (0.15 and 0.5 defaults) for exactly that. Tune alpha_shrink against OOF macro AUC before touching the live submission.
