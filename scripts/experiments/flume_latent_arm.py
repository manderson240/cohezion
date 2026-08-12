"""Does the FLUME VAE latent preserve semantic structure better than the alternatives?

READ THIS BEFORE INTERPRETING THE NUMBERS. `FLUMEVAE` is not a variational autoencoder.
It has no learned parameters, no training loop, and no sampling: `encode` splits the state
into `latent_dim` contiguous chunks and returns each chunk's MEAN as mu and its VARIANCE as
log_var, with a FIXED eps=0.1 so `latent_z` is deterministic. `decode` repeats each latent
value back out. `beta` appears only in a loss that is reported and never optimised.

So FLUME's reduction is BLOCK-MEAN POOLING with a variance side-channel. That is a
perfectly reasonable linear reduction and it is exactly what this measures. It is not a
learned representation, and no result here should be read as one.

The object is run natively rather than approximated: FLUMEVAE takes state_dim/latent_dim
as constructor arguments, so FLUMEVAE(768, 12) gives stride 64 and a 12-dim latent at the
same dimensionality as every other arm. Same embeddings, same pairs, same ground truth
(vault [[wikilinks]]), so the arms are directly comparable.

Reuses the embedding cache written by geometric_correspondence_v2.py -- no re-embedding.

CHALLENGED AND CLEARED (2026-08-12, adversarial review lane Gemma-4-26B-A4B-it):
`flume_mu` projects into the Poincare ball BEFORE reducing, while cos12_trunc and cos12_rp
reduce the RAW vector -- so those arms differ in two respects, not one. That is the same
confound class this series exists to avoid, and it was a fair objection.

It is empirically inert for the cosine arm. `PoincareManifoldND.project` is a uniform
per-vector scalar rescale, and cosine is invariant to positive per-vector scaling, so the
pre-projection cancels exactly. Measured by recomputing the arm without it:

    cos12_flume WITH    pre-projection : 0.734641
    cos12_flume WITHOUT pre-projection : 0.734641
    max per-pair score difference      : 3.33e-16   (floating-point noise)
    vectors actually rescaled          : 787/787    (the transform really did apply)

The 787/787 matters: the delta is zero because the scaling cancels, NOT because the
projection was a no-op that never triggered.

SCOPE OF THAT CLEARANCE: it covers the COSINE arm. Hyperbolic distance is not
scale-invariant, so the argument does not transfer to `hyp12_flume` by symmetry --
`hyp_score` applies its own `to_ball` to the 12-dim latent, and the composed effect there
has not been separately measured.
"""

from __future__ import annotations

import json
import random
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometric_correspondence_v2 import (  # noqa: E402
    auroc,
    cosine,
    hyp_score,
    load_pairs,
    make_random_projection,
    project_rp,
    truncate,
)

from cohezion.agi.flume_vae import FLUMEVAE  # noqa: E402
from cohezion.physics.poincare_manifold import PoincareManifoldND  # noqa: E402

VECCACHE = Path("/tmp/claude-1000/geo_v2_veccache.json")
RESULT = Path("/tmp/claude-1000/flume_arm_result.json")
DIM = 12

VAE = FLUMEVAE(state_dim=768, latent_dim=DIM)


def flume_mu(vec: list[float]) -> list[float]:
    """The real object, run natively at 768 -> 12."""
    point = PoincareManifoldND.project(vec, target_dim=768)
    return list(VAE.encode(point).mu)


def block_mean(vec: Sequence[float], dim: int = DIM) -> list[float]:
    """FLUME's reduction, written plainly. Used only to confirm equivalence, below."""
    stride = len(vec) // dim
    return [sum(vec[i * stride : (i + 1) * stride]) / stride for i in range(dim)]


ARMS = ("cos768", "cos12_trunc", "cos12_rp", "cos12_flume", "hyp12_flume")


def score(arm: str, va: list[float], vb: list[float], fa: list[float], fb: list[float], rp) -> float:
    """`fa`/`fb` are the FLUME latents for `va`/`vb`, passed explicitly rather than looked
    up by id() -- id-keyed caches are only safe while every list stays referenced."""
    if arm == "cos768":
        return cosine(va, vb)
    if arm == "cos12_trunc":
        return cosine(truncate(va), truncate(vb))
    if arm == "cos12_rp":
        return cosine(project_rp(va, rp), project_rp(vb, rp))
    if arm == "cos12_flume":
        return cosine(fa, fb)
    if arm == "hyp12_flume":
        return hyp_score(fa, fb)
    raise ValueError(arm)


def main() -> int:
    if not VECCACHE.exists():
        print("no embedding cache — run geometric_correspondence_v2.py first")
        return 2
    cache_vecs: dict[str, list[float]] = json.loads(VECCACHE.read_text())
    pairs, texts = load_pairs(1200)
    usable = [(a, b) for a, b in pairs if a in cache_vecs and b in cache_vecs]
    stems = [s for s in texts if s in cache_vecs]
    print(f"cached vectors: {len(cache_vecs)}, usable pairs: {len(usable)}")
    if len(usable) < 100 or not stems:
        print("insufficient cached coverage — ABORT rather than report a weak number")
        return 2

    # S-gate: the real object must agree with the plain description of what it does.
    # If FLUMEVAE ever becomes a learned encoder, this fails and the docstring above is
    # stale -- which is exactly when someone must reread it.
    probe = cache_vecs[stems[0]]
    pt = PoincareManifoldND.project(probe, target_dim=768)
    if max(abs(x - y) for x, y in zip(list(VAE.encode(pt).mu), block_mean(pt.coords))) > 1e-9:
        print("S-GATE FAILED: FLUMEVAE.encode no longer equals block-mean pooling.")
        print("The interpretation in this file's docstring is stale. Aborting.")
        return 2
    print("S-gate PASS: FLUMEVAE.encode == block-mean pooling of the projected state\n")

    rp = make_random_projection(768, DIM)
    fcache: dict[str, list[float]] = {}
    pos: dict[str, list[float]] = {a: [] for a in ARMS}
    neg: dict[str, list[float]] = {a: [] for a in ARMS}
    rng = random.Random(23)

    def flume_of(stem: str) -> list[float]:
        if stem not in fcache:
            fcache[stem] = flume_mu(cache_vecs[stem])
        return fcache[stem]

    for n, (a, b) in enumerate(usable, 1):
        c = rng.choice(stems)
        va, vb, vc = cache_vecs[a], cache_vecs[b], cache_vecs[c]
        fa, fb, fc = flume_of(a), flume_of(b), flume_of(c)
        for arm in ARMS:
            pos[arm].append(score(arm, va, vb, fa, fb, rp))
            neg[arm].append(score(arm, va, vc, fa, fc, rp))
        if n % 500 == 0:
            print(f"  {n}/{len(usable)}  " + "  ".join(f"{x}={auroc(pos[x], neg[x]):.3f}" for x in ARMS), flush=True)

    s = {a: auroc(pos[a], neg[a]) for a in ARMS}
    print("\n" + "=" * 74)
    print(f"RESULT over {len(usable)} pairs")
    for a in ARMS:
        print(f"  {a:<14}: {s[a]:.4f}")
    print("\n  CONTRASTS")
    print(f"    FLUME vs truncation   : {s['cos12_flume'] - s['cos12_trunc']:+.4f}")
    print(f"    FLUME vs random proj  : {s['cos12_flume'] - s['cos12_rp']:+.4f}")
    print(f"    geometry on FLUME     : {s['hyp12_flume'] - s['cos12_flume']:+.4f}")
    print(f"    cost of 768 -> FLUME12: {s['cos12_flume'] - s['cos768']:+.4f}")
    print("=" * 74)
    RESULT.write_text(json.dumps({"n": len(usable), "arms": s}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
