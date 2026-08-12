#!/usr/bin/env python3
r"""Overnight experiment: does hyperbolic/J-space projection PRESERVE semantic structure?

SUPERSEDED 2026-08-12 BY geometric_correspondence_v2.py — ITS HEADLINE IS CONFOUNDED.
=====================================================================================
This script ran to completion and reported:

    hyperbolic 0.6946   cosine 0.8936   VERDICT: projecting DEGRADES retrieval by -0.199

DO NOT CITE THAT NUMBER as a fact about geometry. ``to_ball`` below does ``vec[:dim]``,
so the hyperbolic arm saw 12 of 768 dimensions while the cosine arm saw all 768. The gap
is dominated by DIMENSIONALITY, not by curvature. A metric comparison across unequal input
information cannot answer a question about metrics.

The gates here all passed and none could have caught it: they check the instrument in
isolation (projection invariants, and a random-vector control at 0.494 correctly showing
no signal on noise), while the defect was in what the two arms were FED. Stability was
likewise no protection — both curves converged by ~1500 pairs and held flat for 2700 more.

Kept rather than deleted so the artefact stays reproducible. For an answer, use v2, which
holds information constant across a 2x2 of metric x reduction.

THE QUESTION, stated so it can come back NO
-------------------------------------------
Cohezion projects state into a Poincaré ball and into J-space. Both are load-bearing
vocabulary. Nobody has measured whether either projection preserves the semantic structure
of the thing being projected.

    H: hyperbolic distance in the Poincaré ball ranks semantically-related note pairs
       closer than unrelated pairs, at least as well as raw cosine on the embeddings.

Three outcomes are possible and only one is flattering: hyperbolic BETTER (worth adopting),
EQUAL (the projection costs compute and buys nothing here), or WORSE (we are degrading
retrieval by projecting). The third would be the most valuable result and the experiment is
built so it can be reached.

GROUND TRUTH IS FREE — the vault's own graph
--------------------------------------------
`[[wikilinks]]` between vault notes are a human-authored relatedness signal. A linked pair
is related; a random pair is not. No annotation, no labels, no cloud call. This is the
graph supplying the experiment's labels.

V-MODEL RIGOUR
--------------
STRUCTURAL invariants (checked before any measurement; the run ABORTS if they fail):
  S1  PoincareManifoldND.project returns a point strictly inside the unit ball
  S2  distance(x, x) == 0 and distance is symmetric
  S3  distance(x, y) > 0 for x != y
BEHAVIOURAL invariant (the experiment itself):
  B1  related pairs rank closer than unrelated pairs, measured as AUROC
CONTROL (must FAIL, or the instrument proves nothing):
  C1  the same pipeline on RANDOM vectors must give AUROC ~0.5. If random data "shows"
      the effect, the metric is an artefact and every result is void.

Runs unattended, checkpoints every batch, publishes a heartbeat with failure counters via
DaemonHealth — the module written the same day precisely because two daemons stalled for
7.5 hours without anything noticing. This loop is built not to repeat that.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cohezion.contracts import PoincarePoint  # noqa: E402
from cohezion.data_mesh.daemon_health import DaemonHealth, make_bus_publisher  # noqa: E402
from cohezion.physics.poincare_manifold import PoincareManifoldND  # noqa: E402

VAULT = Path.home() / "vaults" / "cohezion-vault"
CKPT = Path("/tmp/claude-1000/geo_correspondence_ckpt.json")
EMBED_URL = "http://localhost:13305/api/v1/embeddings"
EMBED_MODEL = "nomic-embed-text-v2-moe-GGUF"
WIKILINK = re.compile(r"\[\[([^\]|#]+)")


# ----------------------------------------------------------------- embeddings
def embed(texts: list[str], timeout: int = 120) -> list[list[float]] | None:
    body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        EMBED_URL, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        return [item["embedding"] for item in d["data"]]
    except Exception:
        return None


def cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-12
    nb = math.sqrt(sum(y * y for y in b)) or 1e-12
    return num / (na * nb)


def to_ball(vec: list[float], dim: int = 12) -> PoincarePoint:
    """Project an embedding into the Poincaré ball via the production path."""
    return PoincareManifoldND.project(vec[:dim], target_dim=dim)


def hyperbolic_distance(a: PoincarePoint, b: PoincarePoint) -> float:
    return PoincareManifoldND.distance(a, b)


# ----------------------------------------------------------------- metrics
def auroc(pos: list[float], neg: list[float]) -> float:
    """P(a random positive scores above a random negative). 0.5 == no signal.

    Rank-based, so it is invariant to monotone rescaling — which matters because
    hyperbolic distance and cosine live on different scales and must be comparable.
    """
    if not pos or not neg:
        return 0.5
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks: dict[int, float] = {}
    i = 0
    r = 1
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg = (r + (r + (j - i))) / 2
        for k in range(i, j + 1):
            ranks[k] = avg
        r += j - i + 1
        i = j + 1
    rank_sum = sum(ranks[k] for k, (_, lab) in enumerate(allv) if lab == 1)
    n_pos, n_neg = len(pos), len(neg)
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


# ----------------------------------------------------------------- V-model gates
def structural_invariants() -> list[str]:
    """S1-S3. Failures here ABORT — a broken projection makes every measurement noise."""
    fails = []
    v = [0.1, -0.2, 0.05] + [0.0] * 9
    p = to_ball(v)
    if not (p.norm < 1.0):
        fails.append(f"S1 projected norm {p.norm} not < 1")
    q = to_ball([0.3, 0.1, -0.1] + [0.0] * 9)
    if abs(hyperbolic_distance(p, p)) > 1e-9:
        fails.append("S2 distance(x,x) != 0")
    if abs(hyperbolic_distance(p, q) - hyperbolic_distance(q, p)) > 1e-9:
        fails.append("S2 distance not symmetric")
    if not hyperbolic_distance(p, q) > 0:
        fails.append("S3 distance(x,y) not > 0 for x != y")
    return fails


def control_random(n: int = 200, seed: int = 7) -> float:
    """C1. Random vectors must give AUROC ~0.5. If they do not, the metric is an artefact."""
    rng = random.Random(seed)
    pos, neg = [], []
    for _ in range(n):
        a = [rng.gauss(0, 1) for _ in range(12)]
        b = [rng.gauss(0, 1) for _ in range(12)]
        c = [rng.gauss(0, 1) for _ in range(12)]
        pos.append(hyperbolic_distance(to_ball(a), to_ball(b)))
        neg.append(hyperbolic_distance(to_ball(a), to_ball(c)))
    return auroc([-p for p in pos], [-q for q in neg])  # closer == higher score


# ----------------------------------------------------------------- corpus
def load_pairs(limit_notes: int, seed: int = 11) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Linked pairs (positive) from the vault graph; texts keyed by stem."""
    rng = random.Random(seed)
    texts: dict[str, str] = {}
    links: list[tuple[str, str]] = []
    files = sorted((VAULT / "cortex").rglob("*.md")) + sorted((VAULT / "research").rglob("*.md"))
    rng.shuffle(files)
    for f in files[:limit_notes]:
        try:
            body = f.read_text(errors="replace")
        except Exception:
            continue
        if len(body) < 300:
            continue
        texts[f.stem] = body[:1500]
        for tgt in WIKILINK.findall(body):
            links.append((f.stem, tgt.strip()))
    pairs = [(a, b) for a, b in links if a in texts and b in texts and a != b]
    return pairs, texts


# ----------------------------------------------------------------- main loop
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", type=int, default=1200)
    ap.add_argument("--batch", type=int, default=24)
    ap.add_argument("--max-hours", type=float, default=8.0)
    args = ap.parse_args()

    health = DaemonHealth(
        "geo_correspondence_experiment",
        publish_fn=make_bus_publisher(),
        watch_artifact=CKPT,
        stale_after_s=1800,
    )

    print("=" * 74)
    print("V-MODEL GATES — abort on failure, because a broken instrument measures nothing")
    print("=" * 74)
    fails = structural_invariants()
    for f in fails:
        print("  STRUCTURAL FAIL:", f)
    if fails:
        health.record_failure("structural invariants failed")
        health.heartbeat()
        return 2
    print("  S1-S3 structural invariants PASS")

    ctrl = control_random()
    print(f"  C1 control (random vectors) AUROC = {ctrl:.3f}  (must be ~0.5)")
    if not (0.42 <= ctrl <= 0.58):
        print("  CONTROL FAILED — the metric shows signal on RANDOM data. Every result void.")
        health.record_failure(f"control AUROC {ctrl:.3f}")
        health.heartbeat()
        return 2
    print("  C1 control PASS\n")

    pairs, texts = load_pairs(args.notes)
    print(f"corpus: {len(texts)} notes, {len(pairs)} linked pairs (vault graph ground truth)")
    if len(pairs) < 30:
        print("too few linked pairs to measure — ABORT rather than report a weak number")
        health.record_failure("insufficient pairs")
        health.heartbeat()
        return 2

    stems = list(texts)
    rng = random.Random(23)
    state = {"hyp_pos": [], "hyp_neg": [], "cos_pos": [], "cos_neg": [], "done": 0}
    if CKPT.exists():
        try:
            state = json.loads(CKPT.read_text())
            print(f"resumed from checkpoint at {state['done']} pairs")
        except Exception:
            pass

    t0 = time.time()
    cache: dict[str, list[float]] = {}

    def vec(stem: str) -> list[float] | None:
        if stem in cache:
            return cache[stem]
        e = embed([texts[stem]])
        if e is None:
            return None
        cache[stem] = e[0]
        return e[0]

    i = state["done"]
    while i < len(pairs):
        if time.time() - t0 > args.max_hours * 3600:
            print("time budget reached — stopping cleanly")
            break
        batch = pairs[i : i + args.batch]
        made_progress = False
        for a, b in batch:
            va, vb = vec(a), vec(b)
            if va is None or vb is None:
                health.record_failure("embedding call failed")
                continue
            c = rng.choice(stems)
            vc = vec(c)
            if vc is None:
                health.record_failure("embedding call failed")
                continue
            state["hyp_pos"].append(-hyperbolic_distance(to_ball(va), to_ball(vb)))
            state["hyp_neg"].append(-hyperbolic_distance(to_ball(va), to_ball(vc)))
            state["cos_pos"].append(cosine(va, vb))
            state["cos_neg"].append(cosine(va, vc))
            health.record_success()
            made_progress = True
        if not made_progress:
            health.record_idle()
        i += args.batch
        state["done"] = i
        CKPT.write_text(json.dumps(state))
        h = auroc(state["hyp_pos"], state["hyp_neg"])
        c_ = auroc(state["cos_pos"], state["cos_neg"])
        print(f"  {i:>5}/{len(pairs)}  hyperbolic AUROC={h:.3f}  cosine AUROC={c_:.3f}  "
              f"fail_rate={health.failure_rate:.1%}", flush=True)
        health.heartbeat()
        if health.is_degraded:
            print("  DEGRADED — failure rate over threshold; stopping rather than grinding")
            break

    h = auroc(state["hyp_pos"], state["hyp_neg"])
    c_ = auroc(state["cos_pos"], state["cos_neg"])
    n = len(state["hyp_pos"])
    print("\n" + "=" * 74)
    print(f"RESULT over {n} pairs")
    print(f"  hyperbolic (Poincare) AUROC : {h:.4f}")
    print(f"  raw cosine AUROC            : {c_:.4f}")
    print(f"  control (random)            : {ctrl:.4f}")
    delta = h - c_
    if abs(delta) < 0.02:
        verdict = "EQUAL — projection buys nothing here; it costs compute for no ranking gain"
    elif delta > 0:
        verdict = f"HYPERBOLIC BETTER by {delta:+.3f} — projection preserves structure"
    else:
        verdict = f"HYPERBOLIC WORSE by {delta:+.3f} — projecting DEGRADES retrieval"
    print(f"  VERDICT: {verdict}")
    print("=" * 74)
    health.heartbeat()
    json.dump(
        {"n": n, "hyperbolic_auroc": h, "cosine_auroc": c_, "control_auroc": ctrl,
         "verdict": verdict, "counters": health.counters()},
        open("/tmp/claude-1000/geo_correspondence_result.json", "w"), indent=1,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
