#!/usr/bin/env python3
"""Recursive-trace value gate — per-domain, non-circular, can return RETIRE.

Designs:
  docs/research/RECURSIVE_TRACE_FALSIFIABLE_GATE_2026-06-05.md      (original gate)
  docs/research/FAILURE_RESOLUTION_COLLECTION_DESIGN_2026-06-05.md  (this corpus + metric)

Reads the real `(failure_class, strategy, success)` corpus collected by
`record_resolution(...)` and, PER DOMAIN, measures whether the resolving strategy is
statistically dependent on the failure class (conditional vs marginal ordering, with a
label-permutation null). No hand-written map — the verdict comes from real outcomes:

    domain has signal (Δ>0, p<0.05)  -> KEEP    (recursive-trace's premise holds here)
    strategy ⊥ failure-class         -> RETIRE  (it's autoresearch with a dedup cache)
    below volume floor               -> UNPROVEN (need more pairs)

Today this prints UNPROVEN for every domain because the corpus is empty — the honest
current state. It flips to KEEP/RETIRE per domain the moment real pairs accumulate, with
zero code change.
"""
from __future__ import annotations

from cohezion.recursive_trace.coupling_analysis import analyze_domain
from cohezion.recursive_trace.resolution_log import (
    VALID_DOMAINS,
    read_resolutions,
)


# Routing pairs are only causally valid for `duration` (other metrics are computed
# upstream of tier dispatch) — see the collection design §2 routing caveat.
CAUSALLY_VALID = {"quality_gate", "skill_mutation", "routing"}


def main() -> int:
    print("# Recursive-Trace VALUE Gate (per-domain, real corpus)\n")
    pairs_by_domain = {
        domain: [
            (r["failure_class"], r["strategy"])
            for r in read_resolutions(domain, successful_only=True)
        ]
        for domain in sorted(VALID_DOMAINS)
    }
    # Bonferroni: a domain is "testable" iff it clears the volume floor; correct alpha
    # by the number of testable domains so KEEP-if-any doesn't inflate family-wise error.
    testable = sum(
        1 for p in pairs_by_domain.values()
        if analyze_domain(p)["verdict"] != "UNPROVEN"
    )
    alpha = 0.05 / testable if testable else 0.05
    if testable > 1:
        print(f"  (Bonferroni: {testable} testable domains -> per-domain alpha={alpha:.4f})\n")

    verdicts: dict[str, str] = {}
    for domain in sorted(VALID_DOMAINS):
        res = analyze_domain(pairs_by_domain[domain], alpha=alpha)
        verdicts[domain] = res["verdict"]
        print(f"## {domain}")
        print(f"  pairs={res['n']}  failure_classes={res['k']}  strategies={res['n_strategies']}")
        print(f"  {res['verdict']}: {res['reason']}\n")

    causal = {d: v for d, v in verdicts.items() if d in CAUSALLY_VALID}
    if "KEEP" in causal.values():
        overall = "KEEP"
    elif causal and all(v == "RETIRE" for v in causal.values()):
        overall = "RETIRE"
    else:
        overall = "UNPROVEN"
    print(f"OVERALL (causally-valid domains): {overall}")
    if overall == "UNPROVEN":
        print("  No domain has enough real (failure_class, strategy) pairs yet.")
        print("  Wire record_resolution() into the remediation hooks and re-run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
