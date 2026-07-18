"""GAP-0 fix (2026-07-18): CapabilityMatrix must see the skill CATALOG.

The matrix advertises "models, skills, and agents" but pre-fix loaded 0 skills
and 0 agents at runtime: skills entered only via execution history (the 96 PRIME
registry skills had no path in), and agents loaded from a cwd-relative path.

These tests are DISCRIMINATING: they fail against the pre-fix code and pass only
when the catalog loader / cwd-independent agent path actually populate entries.
"""

from __future__ import annotations

from cohezion.compound.capability_matrix import CapabilityEntry, CapabilityMatrix


def test_catalog_skills_loaded_from_registry():
    # DISCRIMINATING: fresh matrix, zero execution history recorded, yet the skill
    # axis MUST be non-empty because the PRIME registry catalog is loaded.
    # Pre-fix this was 0 (the bug the whole gap-loop started from).
    m = CapabilityMatrix()
    skills = m.get_matrix().get("skill", [])
    assert len(skills) > 0, "matrix loaded 0 skills — catalog loader not wired"
    assert any(e.source == "catalog" for e in skills), (
        "no catalog-sourced skills — registry not read"
    )


def test_catalog_skill_has_capabilities():
    # Every catalog skill must carry at least one capability string (its concepts,
    # or the ['skill'] fallback) — an empty capability list would make the entry
    # useless for gap analysis / recommend_for_task.
    m = CapabilityMatrix()
    catalog = [e for e in m.get_matrix().get("skill", []) if e.source == "catalog"]
    assert catalog, "no catalog skills present"
    assert all(e.capabilities for e in catalog)


def test_agents_load_independent_of_cwd(tmp_path, monkeypatch):
    # DISCRIMINATING: run from a foreign cwd that has NO .claude/agents. Pre-fix
    # (cwd-relative Path(".claude/agents")) this yielded 0 agents; post-fix the
    # repo-root-derived path finds them regardless of where the process runs.
    monkeypatch.chdir(tmp_path)
    m = CapabilityMatrix()
    agents = m.get_matrix().get("agent", [])
    assert len(agents) > 0, "agents empty from foreign cwd — path still cwd-relative"


def test_execution_history_not_clobbered_by_catalog():
    # DISCRIMINATING: pick a skill the catalog ACTUALLY loads, overwrite it with a
    # richer execution-history entry, then re-run the catalog loader. The
    # `if key in self._entries: continue` guard must skip it. Using a REAL catalog
    # key (not a synthetic one) is what makes this exercise the guard — a synthetic
    # key is never constructed by the loop, so the guard would never run and the
    # test would pass even if the guard were deleted.
    m = CapabilityMatrix()
    catalog_keys = [
        k for k, e in m._entries.items() if k.startswith("skill:") and e.source == "catalog"
    ]
    assert catalog_keys, "no catalog skills — cannot exercise the clobber guard"
    key = catalog_keys[0]
    m._entries[key] = CapabilityEntry(
        entity_type="skill",
        entity_id=key.split(":", 1)[1],
        source="execution-history",
        quality_score=0.9,
    )
    m._load_catalog_skills()  # re-run: the guard must NOT overwrite the history entry
    assert m._entries[key].source == "execution-history"
    assert m._entries[key].quality_score == 0.9
