"""Tests for the trust-scored ground-truth hierarchy (Memory OS L3+L7 on cohezion)."""

from __future__ import annotations

from cohezion.memory.trust_hierarchy import GroundTruthHierarchy, TrustedFact, TrustTier


# -- Beta-Bernoulli trust (proper, non-linear) --------------------------------


def test_trust_starts_at_prior_half():
    f = TrustedFact(content="x")
    assert f.trust == 0.5  # Beta(1,1) mean


def test_corroboration_raises_trust_contradiction_lowers():
    f = TrustedFact(content="x")
    f.reinforce(True)
    assert f.trust > 0.5
    g = TrustedFact(content="y")
    g.reinforce(False)
    assert g.trust < 0.5


def test_trust_is_not_a_linear_tally():
    """1/1 corroborated must be LESS trusted than 50/50 — the point of a Beta posterior."""
    weak = TrustedFact(content="weak")
    weak.reinforce(True)  # 1 corroboration
    strong = TrustedFact(content="strong")
    for _ in range(50):
        strong.reinforce(True)
    assert strong.trust > weak.trust
    assert weak.trust < 0.9  # one data point is not near-certain


def test_trust_bounded_open_interval():
    f = TrustedFact(content="x")
    for _ in range(100):
        f.reinforce(True)
    assert 0.0 < f.trust < 1.0  # never reaches certainty


# -- entity resolution / dedup ------------------------------------------------


def test_readding_corroborates_not_duplicates():
    h = GroundTruthHierarchy()
    h.add("The setpoint is 0.5")
    h.add("the  SETPOINT is 0.5")  # case/space variant -> same fact
    assert len(h) == 1
    fact = h.rank()[0]
    assert fact.corroborations == 1  # second add corroborated
    assert fact.trust > 0.5


def test_readding_upgrades_tier():
    h = GroundTruthHierarchy()
    h.add("rule X", TrustTier.SESSION)
    h.add("rule X", TrustTier.GROUND_TRUTH)  # later confirmed authoritative
    assert h.rank()[0].tier is TrustTier.GROUND_TRUTH


# -- authority hierarchy (Layer 7) --------------------------------------------


def test_ground_truth_outranks_higher_trust_recall():
    """A low-trust ground-truth fact still outranks a high-trust recall fact (tier first)."""
    h = GroundTruthHierarchy()
    gt = h.add("authoritative claim", TrustTier.GROUND_TRUTH)
    recall = h.add("recalled claim", TrustTier.VECTOR_RECALL)
    for _ in range(20):
        recall.reinforce(True)  # make recall very high-trust
    assert recall.trust > gt.trust  # recall is more "trusted" numerically
    assert h.rank()[0] is gt  # ...but ground-truth tier wins the authority ordering


def test_resolve_picks_highest_authority():
    h = GroundTruthHierarchy()
    a = h.add("v1", TrustTier.SESSION)
    b = h.add("v2", TrustTier.STRUCTURED_FACT)
    assert h.resolve([a, b]) is b
    assert h.resolve([]) is None


def test_authoritative_for_entity():
    h = GroundTruthHierarchy()
    h.add("temp = 0", TrustTier.SESSION, entity="temperature")
    h.add("temp must be 0 for determinism", TrustTier.GROUND_TRUTH, entity="temperature")
    h.add("unrelated", TrustTier.GROUND_TRUTH, entity="other")
    auth = h.authoritative_for("temperature")
    assert auth is not None and auth.tier is TrustTier.GROUND_TRUTH


# -- context injection (Layer 7 directive) ------------------------------------


def test_inject_context_orders_by_authority_and_has_directive():
    h = GroundTruthHierarchy()
    h.add("low", TrustTier.VECTOR_RECALL)
    h.add("high", TrustTier.GROUND_TRUTH)
    block = h.inject_context()
    assert "authoritative" in block.lower()
    # GROUND_TRUTH line appears before VECTOR_RECALL line
    assert block.index("high") < block.index("low")


def test_inject_context_empty_when_no_facts():
    assert GroundTruthHierarchy().inject_context() == ""


def test_inject_context_respects_min_trust_and_max():
    h = GroundTruthHierarchy()
    for i in range(5):
        h.add(f"fact{i}", TrustTier.SESSION)
    assert h.inject_context(max_facts=2).count("\n") == 2  # header + 2 facts -> 2 newlines


# -- mem0 ingestion (compose with existing stack) -----------------------------


def test_ingest_mem0_facts():
    h = GroundTruthHierarchy()
    n = h.ingest_mem0(
        [{"memory": "user prefers uv"}, {"content": "fleet is local-first"}, {"nope": 1}]
    )
    assert n == 2  # the malformed dict is skipped
    assert len(h) == 2


# -- corroboration hook (e.g. QuadratureNexus consensus) ----------------------


def test_corroborate_existing_and_missing():
    h = GroundTruthHierarchy()
    h.add("claim", TrustTier.STRUCTURED_FACT)
    before = h.rank()[0].trust
    h.corroborate("claim", agree=True)  # e.g. 4-voice consensus agreed
    assert h.rank()[0].trust > before
    assert h.corroborate("does not exist", agree=True) is None


def test_serialization_round_trip_preserves_tier_and_posterior():
    """to_dict/from_dict must be LOSSLESS — tier + full Beta posterior survive (durability claim)."""
    from cohezion.memory.trust_hierarchy import TrustTier

    h = GroundTruthHierarchy()
    h.add("verified base url", TrustTier.STRUCTURED_FACT)
    h.add("verified base url", TrustTier.STRUCTURED_FACT)  # corroborate -> non-default posterior
    h.add("a flaky guard")
    h.corroborate("a flaky guard", agree=False)  # contradiction -> distinct posterior
    before = {f.content: (int(f.tier), round(f.trust, 6)) for f in h.rank()}

    h2 = GroundTruthHierarchy.from_dict(h.to_dict())
    after = {f.content: (int(f.tier), round(f.trust, 6)) for f in h2.rank()}
    assert before == after  # tier AND trust posterior identical across the round-trip
    assert len(h2) == len(h)
