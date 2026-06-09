"""Cloud escalation ladder — capability-ascending, premium gated OFF by default.

The triune orchestrator reaches cloud tiers ONLY when a local quality gate fails. The base
ladder is Haiku → Sonnet (cheapest cloud model that clears the gate wins). The premium rungs
(Opus → Fable) are OFF by default because auto-escalating to top-tier models is a
cost-increasing, default-on change (the 2026-06-09 audit's STRAT warning + the user's
'limited budget' / 'sparingly').

`claude-fable-5` (GA 2026-06-09, above the Opus class) is the operator's top "very difficult,
sparingly" rung. It is REAL and lives at the end of the premium ladder — reached only after
Sonnet AND Opus fail, so it is intrinsically sparing.
"""

from __future__ import annotations

from cohezion.inference.triune_orchestrator import _cloud_ladder, build_triune_orchestrator


def _models(tiers):
    return [t[0] for t in tiers if isinstance(t[0], str)]


def test_default_ladder_is_haiku_then_sonnet_and_omits_premium():
    """DISCRIMINATING budget guard: the DEFAULT ladder must be exactly Haiku→Sonnet — NO
    Opus, NO Fable. An impl that defaulted premium ON (the costly mistake) fails here."""
    models = _models(_cloud_ladder())
    assert models == ["claude-haiku-4-5", "claude-sonnet-4-6"]
    assert not any("opus" in m or "fable" in m for m in models)


def test_premium_appends_opus_then_fable_last():
    """DISCRIMINATING ordering: premium ON → Haiku→Sonnet→Opus→Fable. Fable is the FINAL,
    most-capable rung (the operator's 'escalate to Opus, THEN Fable sparingly' intent). An
    impl that dropped Fable, or ordered it before Opus, fails."""
    models = _models(_cloud_ladder(include_premium=True))
    assert models == [
        "claude-haiku-4-5",
        "claude-sonnet-4-6",
        "claude-opus-4-8",
        "claude-fable-5",
    ]
    assert models[-1] == "claude-fable-5"  # the sparing top rung is reached last


def test_default_omits_fable_premium_includes_it():
    """DISCRIMINATING: Fable must be absent by default (budget guard) and present only with
    premium. Kills both an always-on Fable AND a never-wired Fable."""
    assert not any("fable" in m for m in _models(_cloud_ladder()))
    assert "claude-fable-5" in _models(_cloud_ladder(include_premium=True))


def test_build_triune_default_omits_premium_tiers():
    """End-to-end: the default orchestrator's cloud tiers carry Haiku/Sonnet but not the
    premium Opus/Fable rungs."""
    orch = build_triune_orchestrator(include_cloud=True)
    cloud_models = [t[0] for t in orch.tiers if isinstance(t[0], str)]
    assert "claude-sonnet-4-6" in cloud_models
    assert not any("opus" in m or "fable" in m for m in cloud_models)


def test_premium_models_are_priced_for_monitoring():
    """The monitor costs cloud tiers from token_budget._CLOUD_PRICING. Every premium rung
    must be priced — else premium spend silently reads as $0."""
    from cohezion.inference.token_budget import _CLOUD_PRICING

    assert _CLOUD_PRICING["claude-opus-4-8"] == (15.00, 75.00)
    assert _CLOUD_PRICING["claude-fable-5"] == (10.00, 50.00)
    # Only-newest-versions: the superseded Opus 4.7 must be gone.
    assert "claude-opus-4-7" not in _CLOUD_PRICING
