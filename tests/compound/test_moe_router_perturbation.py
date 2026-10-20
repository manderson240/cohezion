"""Perturbation validation of MoESkillRouter (MR1-MR6) and its SkillRefiner consumer (MR4).

Design (after Vojtekova et al. 2026): perturb ONE input -- a single expert's reward -- and
measure where the effect propagates, over (a) the full weight vector and (b) the choice
``SkillRefiner._autodata_select`` makes over a FIXED candidate set.

Claims under test (asserted in harness.md, previously not validated):

L1  Locality: rewarding expert k raises w_k and lowers every other expert.
L2  The other experts move ONLY through the shared normaliser: every untouched w_j is
    scaled by the same factor, so their pairwise ratios -- and hence their ordering -- are
    unchanged.
L3  A perturbation is a no-op on route bookkeeping (update() must not touch route counts).
C1  Consumption: perturbing expert k changes the refiner's choice, and only TOWARD k's
    candidate -- never to a third candidate.
C2  Null perturbation: a router carrying no information (uniform, untouched) must leave the
    refiner's selection sequence identical to having no router at all.

Fresh SkillRefiner instances are used per measurement because ``_autodata_select`` mutates
``_autodata_wins`` (RV2); reusing one would confound the perturbation with the history.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from cohezion.compound.moe_skill_router import MoESkillRouter
from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner


EXPERTS = MoESkillRouter._EXPERT_NAMES
# A non-uniform starting point, so "ordering among untouched experts" is a real ordering
# (at uniform weights every ordering claim is vacuously satisfied by ties).
_SEED_HISTORY = [("quality", 0.9), ("efficiency", 0.4), ("caching", -0.3), ("tier", 0.1)]


def _seeded_router(alpha: float = 0.5) -> MoESkillRouter:
    r = MoESkillRouter(alpha=alpha)
    r.replay(_SEED_HISTORY)
    return r


def _all_perspectives_metrics() -> ExecutionMetrics:
    """Metrics that satisfy every one of the five perspective conditions."""
    return ExecutionMetrics(
        success=True,
        duration_seconds=1.0,
        tokens_used=100,
        token_efficiency=100.0,  # efficiency: < 500
        quality_score=0.9,  # quality: > 0.8
        anomaly_score=0.1,
        cached_hits=3,  # caching: > 0
        tier_used="igpu",  # tier: tier known
        escalation_count=1,
    )


def _winner_expert(router: MoESkillRouter | None) -> str:
    sr = SkillRefiner(moe_router=router)
    m = _all_perspectives_metrics()
    cands = sr._autodata_candidates(m, "read")
    assert len(cands) == len(EXPERTS)  # fixed candidate set: one per expert
    return sr._candidate_expert_map[sr._autodata_select(cands, m)]


def _selection_sequence(router, journey_tracker=None, n: int = 30) -> list[str]:
    sr = SkillRefiner(moe_router=router, journey_tracker=journey_tracker)
    m = _all_perspectives_metrics()
    out = []
    for _ in range(n):
        cands = sr._autodata_candidates(m, "read")
        out.append(sr._candidate_expert_map[sr._autodata_select(cands, m)])
    return out


class TestWeightPerturbationLocality:
    @pytest.mark.parametrize("k", EXPERTS)
    @pytest.mark.parametrize("delta", [0.7, -0.7])
    def test_l1_l2_single_reward_moves_only_through_normaliser(self, k, delta):
        router = _seeded_router()
        w0 = router.weights
        router.update(k, delta)
        w1 = router.weights

        change = {e: w1[e] - w0[e] for e in EXPERTS}
        sign = 1.0 if delta > 0 else -1.0
        # L1: the perturbed expert moves in the reward's direction, all others opposite.
        assert sign * change[k] > 0, change
        for j in EXPERTS:
            if j != k:
                assert sign * change[j] < 0, (j, change)
        assert math.isclose(sum(change.values()), 0.0, abs_tol=1e-12)

        # L2: every untouched expert is scaled by ONE common factor (Z0/Z1)...
        others = [j for j in EXPERTS if j != k]
        ratios = [w1[j] / w0[j] for j in others]
        for r in ratios:
            assert math.isclose(r, ratios[0], rel_tol=1e-12), ratios
        # ...so pairwise ratios, and the ordering among untouched experts, are invariant.
        for a in others:
            for b in others:
                assert math.isclose(w1[a] / w1[b], w0[a] / w0[b], rel_tol=1e-12)
        assert sorted(others, key=lambda e: w0[e]) == sorted(others, key=lambda e: w1[e])

    def test_l2_seed_is_genuinely_non_uniform(self):
        """Guard: if the seed collapsed to ties, L2's ordering check would be vacuous."""
        w = _seeded_router().weights
        assert len({round(v, 12) for v in w.values()}) == len(EXPERTS)

    def test_unknown_expert_perturbation_is_a_zero_change_vector(self):
        router = _seeded_router()
        w0 = router.weights
        router.update("not-an-expert", 1.0)
        assert router.weights == w0

    def test_l3_update_does_not_touch_route_counts(self):
        router = _seeded_router()
        router.route("s", None)
        counts = dict(router._route_counts)
        router.update("caching", 1.0)
        assert router._route_counts == counts


class TestConsumptionPerturbation:
    @pytest.mark.parametrize("k", EXPERTS)
    def test_c1_rewarding_k_moves_choice_only_toward_k(self, k):
        base = _winner_expert(MoESkillRouter(alpha=1.0))
        seen = set()
        for n_rewards in range(16):
            r = MoESkillRouter(alpha=1.0)
            r.replay([(k, 1.0)] * n_rewards)
            w = _winner_expert(r)
            seen.add(w)
            # The effect of perturbing k may only propagate to k's candidate.
            assert w in (base, k), (k, n_rewards, w, base)
        # ...and it must actually get there: the router changes the recommendation.
        assert k in seen, (k, seen)

    @pytest.mark.parametrize("k", EXPERTS)
    def test_c1_penalising_k_never_promotes_a_third_candidate(self, k):
        base = _winner_expert(MoESkillRouter(alpha=1.0))
        for n_penalties in range(16):
            r = MoESkillRouter(alpha=1.0)
            r.replay([(k, -1.0)] * n_penalties)
            w = _winner_expert(r)
            if k != base:
                # Penalising a non-winner can only push it further from winning.
                assert w == base, (k, n_penalties, w)
            else:
                assert w != k or n_penalties == 0, (k, n_penalties, w)

    def test_c2_null_router_matches_no_router_on_the_five_perspectives(self):
        assert _selection_sequence(MoESkillRouter()) == _selection_sequence(None)

    def test_c2_null_router_matches_no_router_with_trajectory_candidate(self):
        jt = MagicMock()
        jt.export_trajectories.return_value = [{"operation_type": "read", "coherence": 0.9}] * 5
        without = _selection_sequence(None, journey_tracker=jt)
        assert "trajectory" in without  # precondition: the candidate can win without a router
        assert _selection_sequence(MoESkillRouter(), journey_tracker=jt) == without

    def test_mr7_unknown_expert_gets_uniform_share_not_zero(self):
        """MR7: an expert outside the roster reads the prior share at ANY training state."""
        r = _seeded_router()
        assert r.get_weight("trajectory") == pytest.approx(1.0 / len(EXPERTS))
        assert sum(r.weights.values()) == pytest.approx(1.0)
        assert "trajectory" not in r.weights

    def test_mr7_trajectory_candidate_survives_a_trained_router(self):
        """Discriminating: a trained router must not veto the trajectory candidate.

        With get_weight(unknown) == 0.0 the trajectory candidate's score is zero and it never
        wins, whatever the other experts' weights are.
        """
        jt = MagicMock()
        jt.export_trajectories.return_value = [{"operation_type": "read", "coherence": 0.9}] * 5
        r = MoESkillRouter(alpha=1.0)
        r.replay([("fallback", -1.0)] * 3)
        assert "trajectory" in _selection_sequence(r, journey_tracker=jt)
