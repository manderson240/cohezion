"""The capability matrix's skill axis must join to the registry, not carry raw
health-record names.

Graph-engineering framing (the open finding from 2026-08-27): the skill-health
store and the skill registry are two node namespaces that were never joinable.
Health records key on ``ANIMATIONS_PRIME``; the registry keys on ``animations``.
``_load_static_skills`` admitted health names VERBATIM, so:

  * real skills never matched the registry (measured: 0 of 73 old records, 0 of
    28 new by exact match) -- the axis was disconnected from the library, and
  * test fixtures (``BAD_SKILL``, ``failing_skill``, ``CHAOTIC_SKILL``) written
    by an old shared-file test suite would enter the matrix as ROUTING entities.

The fix is the missing edge: a canonical-key normalization, used as an admission
gate. A health record enters the matrix only if its canonical key resolves to a
real registry skill. That both un-blinds the axis with real skills and blocks the
fixtures. Measured live on the old 73-record file: the join populates the axis
with 31 real skills (it was 0-blind before) and admits zero test fixtures.
"""

from __future__ import annotations

from cohezion.registry.skill_discovery import canonical_skill_key


def test_canonical_key_strips_prime_and_lowercases() -> None:
    """DISCRIMINATING: the historical mismatch, both directions."""
    assert canonical_skill_key("ANIMATIONS_PRIME") == "animations"
    assert canonical_skill_key("HIHO_REALITY_SIM_PRIME") == "hiho_reality_sim"


def test_canonical_key_normalises_dashes() -> None:
    assert canonical_skill_key("agentic-design-prime") == "agentic_design"


def test_canonical_key_is_idempotent() -> None:
    """An already-canonical registry key must map to itself."""
    assert canonical_skill_key("animations") == "animations"
    assert canonical_skill_key(canonical_skill_key("ANIMATIONS_PRIME")) == "animations"


def test_only_prime_suffix_is_stripped_not_substrings() -> None:
    """`_prime` is stripped only as a trailing token, not mid-name."""
    assert canonical_skill_key("PRIMER_SKILL") == "primer_skill"
    assert canonical_skill_key("PRIME_MOVER") == "prime_mover"


def _matrix_with_health(monkeypatch, health_names, registry_keys):
    """Build a CapabilityMatrix whose tracker returns *health_names* and whose
    registry contains *registry_keys*, without touching real state."""
    from cohezion.compound import capability_matrix as cm
    from cohezion.compound.skill_health_tracker import SkillHealthRecord

    class _FakeTracker:
        def __init__(self, *a, **k):
            self._records = {
                n: SkillHealthRecord(skill_name=n, total_invocations=3, successful_invocations=3)
                for n in health_names
            }

    monkeypatch.setattr(cm, "SkillHealthTracker", _FakeTracker, raising=False)
    monkeypatch.setattr("cohezion.compound.skill_health_tracker.SkillHealthTracker", _FakeTracker)
    monkeypatch.setattr(cm, "load_registry", lambda: {k: {} for k in registry_keys})
    return cm.CapabilityMatrix()


def test_registry_matching_health_record_populates_the_axis(monkeypatch) -> None:
    """A real skill's health record must appear on the skill axis, joined."""
    matrix = _matrix_with_health(
        monkeypatch, health_names=["ANIMATIONS_PRIME"], registry_keys=["animations"]
    )
    skills = matrix.get_matrix()["skill"]
    assert any(getattr(e, "entity_id", "") == "animations" for e in skills), (
        "a health record whose canonical key resolves in the registry must join and populate"
    )


def test_test_fixture_names_are_rejected_from_the_axis(monkeypatch) -> None:
    """DISCRIMINATING: red while health names are admitted verbatim.

    BAD_SKILL / failing_skill do not resolve to any registry skill and must NOT
    become routing entities -- the exact hazard the verbatim loader created.
    """
    matrix = _matrix_with_health(
        monkeypatch,
        health_names=["BAD_SKILL", "failing_skill", "CHAOTIC_SKILL"],
        registry_keys=["animations", "hiho_reality_sim"],
    )
    skills = matrix.get_matrix()["skill"]
    ids = {getattr(e, "entity_id", "") for e in skills}
    assert not ({"BAD_SKILL", "failing_skill", "CHAOTIC_SKILL"} & ids), (
        "unregistered health-record names must not enter the matrix as routing entities"
    )
