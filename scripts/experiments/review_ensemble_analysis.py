"""Can an ensemble fix fabrication? Answered offline, at zero inference cost.

THE REFRAME. Across 12 models on real Cohezion code, SENSITIVITY is cheap -- most models
catch most planted defects. What varies is SPECIFICITY: whether a model cries BUG at correct
code. Qwen3-Coder-30B scores 1.00 sensitivity and 0.67 specificity; SmolLM3 and
lfm2.5-230m sit at 0.00 specificity. So the scarce failure is FABRICATION, not blindness.

THE HYPOTHESIS, stated so it can come back false:

    Truths are shared; fabrications are idiosyncratic. A real defect is visible to any
    capable reviewer, so two models agree on it. A fabrication is an artefact of one model's
    particular failure, so two models fabricate on DIFFERENT clean inputs.

    If true, requiring 2-of-2 agreement raises specificity sharply at small sensitivity cost,
    and a dangerous-but-sensitive lane becomes usable when paired.
    If false -- if models fabricate on the SAME clean inputs -- ensembling cannot help, and
    the honest answer is that fabrication is a property of the TASK, not the model.

WHY THIS COSTS NOTHING. The benchmark stored one row per (model, task, rep) over identical
inputs with identical seeds, so every pairwise ensemble is already latent in the data.
Nothing new is run. This is the cheapest possible experiment and it was paid for yesterday.

RESULT (2026-08-14, 242 scored cells, 11 models):

    HYPOTHESIS CONFIRMED, VALUE REFUTED.

    Fabrications ARE idiosyncratic: 15 of 185 fabrication events were shared, ratio 0.081.
    And the rescue is total -- SmolLM3-3B, which flags EVERY clean function as buggy
    (specificity 0.00, balanced accuracy 0.50), reaches 1.00/1.00 when AND-gated with
    gpt-oss-20b, keeping all of its sensitivity.

    AND YET NO PAIR BEATS ITS BEST MEMBER. Every ensemble of two imperfect models scored
    exactly its stronger member; one scored 0.05 WORSE.

    The reason is structural, not an accident of this data. An AND-gate can only REMOVE BUG
    verdicts, so it can only raise specificity and only lower sensitivity: it inherits the
    behaviour of its strictest member. A pair therefore cannot exceed the best member -- it
    can only rescue the worst. Where a member already has specificity 1.00, there is
    nothing left to win.

    ACTIONABLE CONCLUSION: do NOT build a two-model review protocol. It would double
    inference cost for zero measured quality gain. Route to one good model (Qwen3-8B).
    Revisit only on a corpus hard enough that no single model is perfect -- that is the
    regime where the rescue effect could convert into lift, and this analysis re-runs for
    free against any future benchmark rows.

WHAT WOULD MAKE THIS ANALYSIS WRONG, checked explicitly below:
  G1  pairs must be aligned on (task, rep) -- comparing model A rep 0 against model B rep 2
      would silently manufacture independence that is not there
  G2  the DISAGREEMENT RATE on clean tasks is the load-bearing quantity. If it is ~0 the
      hypothesis is dead regardless of what the ensemble scores, so it is reported FIRST and
      on its own, not buried in a ranking
  G3  an ensemble of two perfect models trivially scores 1.00 and proves nothing. The
      interesting cell is pairs containing a LOW-SPECIFICITY model, so those are called out
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

CKPT = Path("/tmp/claude-1000/review_dogfood_ckpt.json")


def load() -> dict[tuple[str, str, int], dict]:
    rows = json.loads(CKPT.read_text())["rows"]
    return {(r["model"], r["task"], r["rep"]): r for r in rows if r["verdict"]}


def solo(cells: dict, model: str) -> tuple[float, float, float, int]:
    rs = [v for k, v in cells.items() if k[0] == model]
    buggy = [r for r in rs if r["buggy"]]
    clean = [r for r in rs if not r["buggy"]]
    if not buggy or not clean:
        return (float("nan"), float("nan"), float("nan"), 0)
    sens = sum(r["verdict"] == "BUG" for r in buggy) / len(buggy)
    spec = sum(r["verdict"] == "CLEAN" for r in clean) / len(clean)
    return sens, spec, (sens + spec) / 2, len(rs)


def ensemble(cells: dict, a: str, b: str) -> tuple[float, float, float, int]:
    """AND-gate: BUG only when BOTH models say BUG, on the SAME (task, rep) [G1]."""
    keys = {(k[1], k[2]) for k in cells if k[0] == a} & {(k[1], k[2]) for k in cells if k[0] == b}
    buggy_hit = buggy_n = clean_ok = clean_n = 0
    for task, rep in keys:
        ra, rb = cells[(a, task, rep)], cells[(b, task, rep)]
        verdict = "BUG" if (ra["verdict"] == "BUG" and rb["verdict"] == "BUG") else "CLEAN"
        if ra["buggy"]:
            buggy_n += 1
            buggy_hit += verdict == "BUG"
        else:
            clean_n += 1
            clean_ok += verdict == "CLEAN"
    if not buggy_n or not clean_n:
        return (float("nan"), float("nan"), float("nan"), 0)
    sens = buggy_hit / buggy_n
    spec = clean_ok / clean_n
    return sens, spec, (sens + spec) / 2, len(keys)


def fabrication_overlap(cells: dict, a: str, b: str) -> tuple[int, int, int]:
    """[G2] On CLEAN inputs: how often do both fabricate on the SAME one?

    Returns (both_fabricated, either_fabricated, shared_clean_cells). If both/either is
    high, fabrications are SHARED and no AND-gate can help.
    """
    keys = {(k[1], k[2]) for k in cells if k[0] == a} & {(k[1], k[2]) for k in cells if k[0] == b}
    both = either = n = 0
    for task, rep in keys:
        ra, rb = cells[(a, task, rep)], cells[(b, task, rep)]
        if ra["buggy"]:
            continue
        n += 1
        fa, fb = ra["verdict"] == "BUG", rb["verdict"] == "BUG"
        both += fa and fb
        either += fa or fb
    return both, either, n


def main() -> int:
    if not CKPT.exists():
        print("no benchmark data")
        return 2
    cells = load()
    models = sorted({k[0] for k in cells})
    solos = {m: solo(cells, m) for m in models}
    print(f"{len(cells)} scored cells, {len(models)} models — no new inference run\n")

    # ---- G2 FIRST: the hypothesis stands or falls here, before any ranking ----
    print("=" * 78)
    print("G2  ARE FABRICATIONS IDIOSYNCRATIC?  (clean inputs only)")
    print("=" * 78)
    print("If two models fabricate on the SAME clean inputs, no AND-gate can help.\n")
    print(f"{'pair':<58} {'both':>6} {'either':>7} {'ratio':>7}")
    print("-" * 78)
    shared_tot = either_tot = 0
    for a, b in itertools.combinations(models, 2):
        both, either, n = fabrication_overlap(cells, a, b)
        if either == 0 or n == 0:
            continue
        shared_tot += both
        either_tot += either
        if either >= 3:
            print(f"{a[:27]:<27} + {b[:27]:<27} {both:>6} {either:>7} {both / either:>7.2f}")
    overall = shared_tot / either_tot if either_tot else float("nan")
    print("-" * 78)
    print(f"OVERALL: {shared_tot} of {either_tot} fabrication events were SHARED  "
          f"(ratio {overall:.3f})")
    print("ratio ~0 => idiosyncratic, AND-gate should work.")
    print("ratio ~1 => shared, fabrication is a property of the TASK and ensembling is futile.")

    # ---- ensembles ----
    print("\n" + "=" * 78)
    print("AND-GATE ENSEMBLES vs their own members")
    print("=" * 78)
    best_solo = max((v[2], m) for m, v in solos.items() if v[3])
    print(f"best single model: {best_solo[1]} at bal={best_solo[0]:.3f}\n")
    print(f"{'pair':<56} {'bal':>5} {'sens':>5} {'spec':>5}  {'lift over best member':>21}")
    print("-" * 78)
    results = []
    for a, b in itertools.combinations(models, 2):
        sens, spec, bal, n = ensemble(cells, a, b)
        if not n or bal != bal:
            continue
        member_best = max(solos[a][2], solos[b][2])
        results.append((bal, sens, spec, a, b, member_best))
    for bal, sens, spec, a, b, mb in sorted(results, reverse=True)[:12]:
        print(f"{a[:26]:<26} + {b[:26]:<26} {bal:>5.2f} {sens:>5.2f} {spec:>5.2f}  {bal - mb:>+21.2f}")

    # ---- G3: the interesting cell — does pairing RESCUE a fabricating lane? ----
    print("\n" + "=" * 78)
    print("G3  DOES PAIRING RESCUE A LOW-SPECIFICITY LANE?")
    print("=" * 78)
    print("Two already-perfect models trivially score 1.00 and prove nothing. These pairs")
    print("each contain a model whose SOLO specificity is below 0.90.\n")
    print(f"{'weak member (solo spec)':<40} {'partner':<26} {'pair bal':>8} {'pair spec':>10}")
    print("-" * 78)
    weak = [m for m in models if solos[m][1] < 0.90 and solos[m][3]]
    for w in sorted(weak, key=lambda m: solos[m][1]):
        best = None
        for bal, sens, spec, a, b, _mb in sorted(results, reverse=True):
            if w in (a, b):
                best = (bal, spec, b if a == w else a)
                break
        if best:
            print(f"{w[:28]:<28} ({solos[w][1]:.2f}){'':<5} {best[2][:26]:<26} "
                  f"{best[0]:>8.2f} {best[1]:>10.2f}")

    # ---- G4: the value question. A rescue is a MECHANISM result; value requires that
    # two IMPERFECT models beat their own best member. If every pair that reaches 1.00
    # already contains a 1.00 model, the ensemble bought nothing on this corpus.
    print("\n" + "=" * 78)
    print("G4  DO TWO IMPERFECT MODELS BEAT THEIR BEST MEMBER?")
    print("=" * 78)
    print("Pairs where BOTH members score below 1.00 solo. This is the only cell where an")
    print("ensemble can demonstrate value rather than inherit it from an already-perfect member.\n")
    print(f"{'pair (both members < 1.00)':<58} {'pair':>5} {'best member':>12} {'lift':>6}")
    print("-" * 78)
    any_lift = False
    rows_g4 = []
    for bal, sens, spec, a, b, mb in results:
        if solos[a][2] < 0.999 and solos[b][2] < 0.999:
            rows_g4.append((bal - mb, bal, mb, a, b))
    for lift, bal, mb, a, b in sorted(rows_g4, reverse=True)[:10]:
        flag = "  <-- LIFT" if lift > 0.01 else ""
        any_lift = any_lift or lift > 0.01
        print(f"{a[:27]:<27} + {b[:27]:<27} {bal:>5.2f} {mb:>12.2f} {lift:>+6.2f}{flag}")
    if not rows_g4:
        print("  (none — every pair contains an already-perfect member)")
    print("-" * 78)
    print(
        "VERDICT: ensembling BEATS its members here."
        if any_lift
        else "VERDICT: NO LIFT over the best member on this corpus. The rescue effect is real\n"
        "         but its VALUE is capped by saturation — several models are already at\n"
        "         1.00, so an AND-gate has nothing left to win. Expect lift only on a\n"
        "         harder corpus where no single model is perfect."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
