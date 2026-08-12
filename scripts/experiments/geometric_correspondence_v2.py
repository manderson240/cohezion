"""Does hyperbolic projection preserve semantic structure -- holding INFORMATION constant?

v1 (geometric_correspondence_overnight.py) measured hyperbolic-12D AUROC 0.695 against
cosine-768D AUROC 0.894 and concluded "projection degrades retrieval by 0.20". That
conclusion was UNSOUND. `to_ball` does `vec[:12]`, discarding 98.4% of the embedding,
while the cosine arm kept all 768 dims. The gap measured dimensionality, not geometry.
v1's numbers are kept as the `cos768` and `hyp12_trunc` arms here so the artefact is
visible rather than quietly dropped.

The fix is a 2x2 on IDENTICAL embeddings in a single pass:

                     truncate[:12]        random-projection 768->12
    hyperbolic       hyp12_trunc          hyp12_rp
    cosine           cos12_trunc          cos12_rp

plus cos768 as the full-information reference. The decisive contrasts:

    hyp12_trunc vs cos12_trunc   geometry effect, information held equal (truncated)
    hyp12_rp    vs cos12_rp      geometry effect, information held equal (proper reduction)
    cos12_rp    vs cos12_trunc   what truncation alone costs
    cos768      vs cos12_rp      what dimensionality reduction alone costs

Only the first two can answer "is hyperbolic geometry buying us anything". A metric
comparison across different input information cannot, no matter how large the gap.

Ground truth is free and unfaked: vault [[wikilinks]] are human-authored assertions that
two notes are related. Positive = linked pair; negative = random pair.

V-MODEL GATES, all abort rather than report a number:
  S1-S3  structural invariants on the projection (norm < 1, d(x,x)=0, symmetry, d>0)
  S4     random projection must actually mix dimensions (a no-op RP would silently
         reduce hyp12_rp to hyp12_trunc and fake an agreement between the two contrasts)
  C1     random vectors must give AUROC ~0.5 in EVERY arm; signal on noise voids the run
  C2     the two reductions must not be identical -- if they are, the 2x2 has one column
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cohezion.data_mesh.daemon_health import DaemonHealth, make_bus_publisher  # noqa: E402
from cohezion.physics.poincare_manifold import PoincareManifoldND  # noqa: E402

VAULT = Path.home() / "vaults" / "cohezion-vault"
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
ENDPOINT = "http://localhost:13305/api/v1/embeddings"
MODEL = "nomic-embed-text-v2-moe-GGUF"
CKPT = Path("/tmp/claude-1000/geo_v2_ckpt.json")
VECCACHE = Path("/tmp/claude-1000/geo_v2_veccache.json")
RESULT = Path("/tmp/claude-1000/geo_v2_result.json")

DIM = 12
ARMS = ("cos768", "cos12_trunc", "hyp12_trunc", "cos12_rp", "hyp12_rp")


# ----------------------------------------------------------------- embeddings
def embed(texts: list[str], timeout: int = 120) -> list[list[float]] | None:
    payload = json.dumps({"model": MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        ENDPOINT, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read())
        return [d["embedding"] for d in body["data"]]
    except (urllib.error.URLError, OSError, KeyError, ValueError, TimeoutError):
        return None


# ----------------------------------------------------------------- geometry
def cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-12
    nb = math.sqrt(sum(y * y for y in b)) or 1e-12
    return num / (na * nb)


def make_random_projection(src_dim: int, dst_dim: int, seed: int = 1729):
    """Seeded Gaussian random projection. Johnson-Lindenstrauss: approximately preserves
    pairwise distances, unlike taking the first k coordinates, which preserves nothing."""
    rng = random.Random(seed)
    scale = 1.0 / math.sqrt(dst_dim)
    return [[rng.gauss(0.0, 1.0) * scale for _ in range(src_dim)] for _ in range(dst_dim)]


def project_rp(vec: list[float], matrix: list[list[float]]) -> list[float]:
    return [sum(w * v for w, v in zip(row, vec)) for row in matrix]


def truncate(vec: list[float], dim: int = DIM) -> list[float]:
    return vec[:dim]


def to_ball(vec: list[float]):
    return PoincareManifoldND.project(vec, target_dim=len(vec))


def hyp_score(a: list[float], b: list[float]) -> float:
    """Negated distance so that, as with cosine, higher == more similar."""
    return -PoincareManifoldND.distance(to_ball(a), to_ball(b))


# ----------------------------------------------------------------- metrics
def auroc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return float("nan")
    scored = [(s, 1) for s in pos] + [(s, 0) for s in neg]
    scored.sort(key=lambda t: t[0])
    ranks: dict[int, float] = {}
    i = 0
    while i < len(scored):
        j = i
        while j + 1 < len(scored) and scored[j + 1][0] == scored[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_sum = sum(ranks[k] for k, (_, lab) in enumerate(scored) if lab == 1)
    n_pos, n_neg = len(pos), len(neg)
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


# ----------------------------------------------------------------- V-model gates
def structural_invariants(rp) -> list[str]:
    fails: list[str] = []

    v = truncate([0.1, -0.2, 0.05] + [0.0] * 20)
    w = truncate([0.3, 0.1, -0.1] + [0.0] * 20)
    p, q = to_ball(v), to_ball(w)

    if not p.norm < 1.0:
        fails.append(f"S1 projected norm {p.norm} not < 1")
    if abs(PoincareManifoldND.distance(p, p)) > 1e-9:
        fails.append("S2 d(x,x) != 0")
    if abs(PoincareManifoldND.distance(p, q) - PoincareManifoldND.distance(q, p)) > 1e-9:
        fails.append("S2 distance not symmetric")
    if not PoincareManifoldND.distance(p, q) > 0:
        fails.append("S3 d(x,y) not > 0 for x != y")

    # S4: a random projection that failed to mix dimensions would silently collapse the
    # 2x2 into one column and manufacture agreement between the two geometry contrasts.
    #
    # Two DISTINCT degeneracies, because the first check alone does not imply the second
    # (flagged by an adversarial review lane, 2026-08-12 -- the original comment claimed
    # "not mixing" while only testing for all-zero output):
    #   S4a the projection must not IGNORE high coordinates, the way truncation does
    #   S4b it must not funnel everything into ONE output dimension, which passes S4a
    #       while still destroying the distances the arm depends on
    probe = [0.0] * 768
    probe[500] = 1.0  # a coordinate truncation throws away entirely
    out = project_rp(probe, rp)
    if max(abs(x) for x in out) < 1e-9:
        fails.append("S4a random projection ignores high coordinates -- not mixing")
    if len(out) != DIM:
        fails.append(f"S4 random projection returned dim {len(out)}, expected {DIM}")

    dense = [random.Random(31).gauss(0, 1) for _ in range(768)]
    proj = project_rp(dense, rp)
    peak = max(abs(x) for x in proj) or 1e-12
    live = sum(1 for x in proj if abs(x) > 0.01 * peak)
    if live < DIM // 2:
        fails.append(f"S4b random projection concentrates into {live}/{DIM} output dims")

    return fails


def controls(rp, n: int = 300, seed: int = 7) -> dict[str, float]:
    """C1. Random vectors must give ~0.5 in EVERY arm, or that arm's metric is an artefact."""
    rng = random.Random(seed)
    acc: dict[str, tuple[list[float], list[float]]] = {a: ([], []) for a in ARMS}
    for _ in range(n):
        a = [rng.gauss(0, 1) for _ in range(768)]
        b = [rng.gauss(0, 1) for _ in range(768)]
        c = [rng.gauss(0, 1) for _ in range(768)]
        for arm, (pos, neg) in acc.items():
            pos.append(score_arm(arm, a, b, rp))
            neg.append(score_arm(arm, a, c, rp))
    return {arm: auroc(pos, neg) for arm, (pos, neg) in acc.items()}


# ----------------------------------------------------------------- arms
def score_arm(arm: str, va: list[float], vb: list[float], rp) -> float:
    if arm == "cos768":
        return cosine(va, vb)
    if arm == "cos12_trunc":
        return cosine(truncate(va), truncate(vb))
    if arm == "hyp12_trunc":
        return hyp_score(truncate(va), truncate(vb))
    if arm == "cos12_rp":
        return cosine(project_rp(va, rp), project_rp(vb, rp))
    if arm == "hyp12_rp":
        return hyp_score(project_rp(va, rp), project_rp(vb, rp))
    raise ValueError(f"unknown arm {arm}")


# ----------------------------------------------------------------- corpus
def load_pairs(limit_notes: int, seed: int = 11):
    rng = random.Random(seed)
    texts: dict[str, str] = {}
    links: list[tuple[str, str]] = []
    files = sorted((VAULT / "cortex").rglob("*.md")) + sorted((VAULT / "research").rglob("*.md"))
    rng.shuffle(files)
    for f in files[:limit_notes]:
        try:
            body = f.read_text(errors="replace")
        except OSError:
            continue
        if len(body) < 300:
            continue
        texts[f.stem] = body[:1500]
        for tgt in WIKILINK.findall(body):
            links.append((f.stem, tgt.strip()))
    pairs = [(a, b) for a, b in links if a in texts and b in texts and a != b]
    return pairs, texts


# ----------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", type=int, default=1200)
    ap.add_argument("--batch", type=int, default=24)
    ap.add_argument("--max-hours", type=float, default=8.0)
    args = ap.parse_args()

    health = DaemonHealth(
        "geo_correspondence_v2",
        publish_fn=make_bus_publisher(),
        watch_artifact=CKPT,
        stale_after_s=1800,
    )
    rp = make_random_projection(768, DIM)

    print("=" * 78)
    print("V-MODEL GATES — abort on failure; a broken instrument measures nothing")
    print("=" * 78)
    fails = structural_invariants(rp)
    for f in fails:
        print("  STRUCTURAL FAIL:", f)
    if fails:
        health.record_failure("structural invariants failed")
        health.heartbeat()
        return 2
    print("  S1-S4 structural invariants PASS")

    ctrl = controls(rp)
    bad = {a: v for a, v in ctrl.items() if not 0.42 <= v <= 0.58}
    for a, v in ctrl.items():
        print(f"  C1 control {a:<12} AUROC = {v:.3f}")
    if bad:
        print(f"  CONTROL FAILED on {list(bad)} — signal on random data. Results void.")
        health.record_failure(f"control failed: {bad}")
        health.heartbeat()
        return 2
    print("  C1 controls PASS (every arm ~0.5 on noise)")

    # C2: the two reductions must genuinely differ, else the 2x2 has a duplicated column.
    probe = [random.Random(99).gauss(0, 1) for _ in range(768)]
    if max(abs(x - y) for x, y in zip(truncate(probe), project_rp(probe, rp))) < 1e-9:
        print("  C2 FAILED — truncation and random projection are identical")
        health.record_failure("reductions identical")
        health.heartbeat()
        return 2
    print("  C2 reductions are distinct PASS\n")

    pairs, texts = load_pairs(args.notes)
    print(f"corpus: {len(texts)} notes, {len(pairs)} linked pairs (vault graph ground truth)")
    if len(pairs) < 30:
        health.record_failure("insufficient pairs")
        health.heartbeat()
        return 2

    state = {"done": 0, "pos": {a: [] for a in ARMS}, "neg": {a: [] for a in ARMS}}
    if CKPT.exists():
        try:
            state = json.loads(CKPT.read_text())
            print(f"resumed at {state['done']} pairs")
        except (OSError, ValueError):
            pass

    cache: dict[str, list[float]] = {}
    if VECCACHE.exists():
        try:
            cache = json.loads(VECCACHE.read_text())
            print(f"embedding cache: {len(cache)} vectors reused (no re-embed cost)")
        except (OSError, ValueError):
            cache = {}

    stems = list(texts)
    rng = random.Random(23)
    t0 = time.time()

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
        made_progress = False
        for a, b in pairs[i : i + args.batch]:
            va, vb = vec(a), vec(b)
            vc = vec(rng.choice(stems))
            if va is None or vb is None or vc is None:
                health.record_failure("embedding call failed")
                continue
            for arm in ARMS:
                state["pos"][arm].append(score_arm(arm, va, vb, rp))
                state["neg"][arm].append(score_arm(arm, va, vc, rp))
            health.record_success()
            made_progress = True
        if not made_progress:
            health.record_idle()
        i += args.batch
        state["done"] = i
        CKPT.write_text(json.dumps(state))
        VECCACHE.write_text(json.dumps(cache))
        scores = {a: auroc(state["pos"][a], state["neg"][a]) for a in ARMS}
        print(
            f"  {i:>5}/{len(pairs)}  "
            + "  ".join(f"{a}={scores[a]:.3f}" for a in ARMS)
            + f"  fail={health.failure_rate:.1%}",
            flush=True,
        )
        health.heartbeat()
        if health.is_degraded:
            print("  DEGRADED — failure rate over threshold; stopping rather than grinding")
            break

    s = {a: auroc(state["pos"][a], state["neg"][a]) for a in ARMS}
    n = len(state["pos"]["cos768"])

    print("\n" + "=" * 78)
    print(f"RESULT over {n} pairs")
    print(f"  cos768       (full information reference) : {s['cos768']:.4f}")
    print(f"  cos12_trunc  (cosine, first 12 dims)      : {s['cos12_trunc']:.4f}")
    print(f"  hyp12_trunc  (hyperbolic, first 12 dims)  : {s['hyp12_trunc']:.4f}")
    print(f"  cos12_rp     (cosine, random-proj 12)     : {s['cos12_rp']:.4f}")
    print(f"  hyp12_rp     (hyperbolic, random-proj 12) : {s['hyp12_rp']:.4f}")

    g_trunc = s["hyp12_trunc"] - s["cos12_trunc"]
    g_rp = s["hyp12_rp"] - s["cos12_rp"]
    cost_trunc = s["cos12_rp"] - s["cos12_trunc"]
    cost_dim = s["cos768"] - s["cos12_rp"]

    print("\n  CONTRASTS (each holds information constant)")
    print(f"    geometry effect, truncated : {g_trunc:+.4f}  (hyp12_trunc - cos12_trunc)")
    print(f"    geometry effect, rand-proj : {g_rp:+.4f}  (hyp12_rp - cos12_rp)")
    print(f"    cost of truncating vs RP   : {cost_trunc:+.4f}")
    print(f"    cost of 768 -> 12          : {cost_dim:+.4f}")

    agree = (g_trunc > 0.02 and g_rp > 0.02) or (g_trunc < -0.02 and g_rp < -0.02)
    if abs(g_trunc) < 0.02 and abs(g_rp) < 0.02:
        verdict = "NO GEOMETRY EFFECT — hyperbolic buys nothing at equal information"
    elif agree and g_rp > 0:
        verdict = f"HYPERBOLIC HELPS ({g_rp:+.3f} at equal information, both reductions agree)"
    elif agree:
        verdict = f"HYPERBOLIC HURTS ({g_rp:+.3f} at equal information, both reductions agree)"
    else:
        verdict = (
            f"REDUCTION-DEPENDENT — trunc {g_trunc:+.3f} vs rp {g_rp:+.3f} disagree; "
            "the effect is an artefact of how dimensions were chosen, not of geometry"
        )
    print(f"\n  VERDICT: {verdict}")
    print("=" * 78)

    health.heartbeat()
    RESULT.write_text(
        json.dumps(
            {
                "n": n,
                "arms": s,
                "controls": ctrl,
                "geometry_effect_trunc": g_trunc,
                "geometry_effect_rp": g_rp,
                "cost_of_truncation": cost_trunc,
                "cost_of_dim_reduction": cost_dim,
                "verdict": verdict,
                "counters": health.counters(),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
