#!/usr/bin/env python3
"""Falsifiable test: does the JEPA world-model learn agent-journey surprise
discrimination in the 12D FLUME latent manifold — or just fit noise?

Claim under test
----------------
A JEPA world-model trained on FAMILIAR agent journeys (a fixed 12D latent
dynamics) assigns HIGHER surprise to journeys drawn from a DIFFERENT dynamics
(novel/OOD) than to held-out familiar journeys.

Three arms (falsifiable-eval-harness discipline)
------------------------------------------------
  treatment       : JEPA trained on familiar journeys
  frozen baseline : JEPA at random init (never trained) — must NOT discriminate
  placebo         : trained JEPA scored on shuffled familiar/novel labels

Verdict is FALSIFIABLE: if treatment's discrimination (AUC of surprise separating
novel from familiar) is not clearly above the untrained baseline AND above the
placebo, the claim FAILS and we say so. $0 — CPU only, no cloud, no LLM.
"""

from __future__ import annotations

import numpy as np

from cohezion.world_model.jepa_world_model import JEPAWorldModel

RNG = np.random.RandomState(20260710)
STATE_DIM = 12  # the FLUME manifold dimension


def _familiar_transition(s: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Smooth, structured dynamics the model is allowed to learn."""
    return np.tanh(0.9 * s + 0.3 * a)


def _novel_transition(s: np.ndarray, a: np.ndarray) -> np.ndarray:
    """A DIFFERENT dynamics (rotation + sign flip) the model never saw."""
    rolled = np.roll(s, 3)
    return np.tanh(-0.9 * rolled + 0.3 * a)


def _journeys(transition, n: int) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    out = []
    for _ in range(n):
        s = RNG.randn(STATE_DIM).astype(np.float32) * 0.5
        a = RNG.randn(STATE_DIM).astype(np.float32) * 0.5
        out.append((s, a, transition(s, a).astype(np.float32)))
    return out


def _auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """AUC that surprise(pos=novel) > surprise(neg=familiar). 0.5 = chance."""
    wins = sum(1.0 for p in pos for q in neg if p > q)
    ties = sum(0.5 for p in pos for q in neg if p == q)
    return (wins + ties) / (len(pos) * len(neg))


def _surprise(model: JEPAWorldModel, journeys) -> np.ndarray:
    return np.array([model.surprise_score(s, a, ns) for s, a, ns in journeys])


def main() -> None:
    train = _journeys(_familiar_transition, 400)
    fam_test = _journeys(_familiar_transition, 120)
    nov_test = _journeys(_novel_transition, 120)

    # --- frozen baseline: untrained JEPA (should NOT discriminate) ---
    baseline = JEPAWorldModel(state_dim=STATE_DIM, action_dim=STATE_DIM, embed_dim=64)
    base_auc = _auc(_surprise(baseline, nov_test), _surprise(baseline, fam_test))

    # --- treatment: train on familiar journeys ---
    model = JEPAWorldModel(state_dim=STATE_DIM, action_dim=STATE_DIM, embed_dim=64)
    for _ in range(30):
        model.train_epoch(train)
    treat_auc = _auc(_surprise(model, nov_test), _surprise(model, fam_test))

    # --- placebo: trained model, shuffled labels ---
    all_s = np.concatenate([_surprise(model, nov_test), _surprise(model, fam_test)])
    RNG.shuffle(all_s)
    placebo_auc = _auc(all_s[: len(nov_test)], all_s[len(nov_test) :])

    fam_mean = float(_surprise(model, fam_test).mean())
    nov_mean = float(_surprise(model, nov_test).mean())

    print("=== JEPA journey surprise-discrimination (falsifiable) ===")
    print(f"  frozen-baseline AUC (untrained) : {base_auc:.3f}   (want ~0.5)")
    print(f"  TREATMENT AUC (trained)         : {treat_auc:.3f}   (want >> 0.5)")
    print(f"  placebo AUC (shuffled labels)   : {placebo_auc:.3f}   (want ~0.5)")
    print(f"  mean surprise familiar / novel  : {fam_mean:.4f} / {nov_mean:.4f}")

    # Falsifiable verdict
    lift = treat_auc - base_auc
    passed = treat_auc >= 0.70 and lift >= 0.15 and abs(placebo_auc - 0.5) < 0.1
    print(f"\n  lift over baseline: {lift:+.3f}")
    print(f"  VERDICT: {'CONFIRMED — the world-model learned journey structure' if passed else 'FALSIFIED — no real discrimination (claim does not hold)'}")


if __name__ == "__main__":
    main()
