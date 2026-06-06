"""Discriminating tests for skill-adoption telemetry (item 32, 2026-06-06).

`skill_adoption_report(usage_events, registry_skills)` lists registered skills with ZERO usage
events. It NEVER reads SurrealDB — the caller injects the events — so the "no real SurrealDB read
under pytest" guarantee holds by construction.

Each test fails a plausible wrong impl:
  - return every skill (ignore the events) → T_all_adopted,
  - return none / ignore the registry → T_unadopted,
  - read the registry file even when names are injected → T_no_file_read,
  - crash on a malformed event → T_malformed.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound import skill_adoption
from cohezion.compound.skill_adoption import skill_adoption_report


def _ev(name: str) -> dict:
    return {"skill_name": name, "success": True}


def test_unadopted_skills_surface() -> None:
    registry = ["alpha", "beta", "gamma"]
    events = [_ev("alpha"), _ev("gamma")]  # beta never fired
    assert skill_adoption_report(events, registry) == ["beta"]


def test_all_adopted_returns_empty() -> None:
    registry = ["alpha", "beta"]
    events = [_ev("alpha"), _ev("beta")]
    # Every registry skill fired → nothing undertriggering. A wrong impl ignoring events fails.
    assert skill_adoption_report(events, registry) == []


def test_injected_registry_does_not_read_the_registry_file(monkeypatch) -> None:
    # When registry_skills is injected, the registry JSON must NOT be loaded. A wrong impl that
    # always loads the file (ignoring the injected arg) trips this patched exploder.
    def _boom(*_a, **_k):
        raise AssertionError("registry file read despite injected registry_skills")

    monkeypatch.setattr(skill_adoption, "_registry_skill_names", _boom)
    assert skill_adoption_report([_ev("alpha")], ["alpha", "beta"]) == ["beta"]


def test_registry_loaded_from_file_when_not_injected(tmp_path: Path) -> None:
    reg = tmp_path / "skill_registry.json"
    reg.write_text('{"one": {}, "two": {}, "three": {}}')
    events = [_ev("two")]
    got = skill_adoption_report(events, registry_path=reg)
    assert got == ["one", "three"]  # loaded keys minus the fired one


def test_malformed_event_without_skill_name_is_ignored() -> None:
    registry = ["alpha", "beta"]
    events = [{"success": True}, _ev("alpha")]  # first event has no skill_name
    # Must not crash, and must not mark anything adopted from the malformed event.
    assert skill_adoption_report(events, registry) == ["beta"]


def test_live_registry_smoke_reports_many_unadopted() -> None:
    # No events injected → every registered skill is "unadopted". Real registry has 200+ skills.
    out = skill_adoption_report([])
    assert isinstance(out, list)
    assert len(out) > 50  # the real registry is large; an empty result would mean a broken load
