"""Provenance / pseudoarchaeology-marker remediation for the worldviews module.

Context: Richards et al. 2026 (Australian Archaeology, doi:10.1080/03122417.2026.2706246),
analysed against this module in the vault digest
``research/digests/20260921-richards-pacific-pseudoarchaeology-genai-vs-worldviews.md``.

Each test below is discriminating: it failed against the pre-remediation module
(fringe entry in the traditions registry, no provenance, no interpretive notice,
moiety/section conflation) and passes after it.
"""

from __future__ import annotations

import asyncio

from cohezion.api.services import worldviews as api
from cohezion.worldviews import tradition_data as td


def test_stealthskater_not_listed_among_traditions():
    slugs = {t.slug for t in td.get_traditions()}
    assert "stealthskater" not in slugs


def test_step_comparison_excludes_speculative_frameworks():
    slugs = {row["slug"] for row in td.get_step_across_traditions(0)}
    assert "stealthskater" not in slugs


def test_stealthskater_kept_as_speculative_framework_with_content_intact():
    frameworks = {f.slug: f for f in td.get_speculative_frameworks()}
    assert "stealthskater" in frameworks
    entry = frameworks["stealthskater"]
    assert entry.category == "speculative-physics"
    assert len(entry.step_mappings) == 10
    assert len(entry.unique_contributions) == 4
    # Harness S2 backward-compatible lookup still resolves.
    assert td.get_tradition("stealthskater") is entry


def test_every_step_mapping_has_non_empty_provenance():
    entries = td.get_traditions() + td.get_speculative_frameworks()
    for t in entries:
        for s in t.step_mappings:
            assert s.provenance.strip(), f"{t.slug} step {s.step_index} has no provenance"
            assert s.to_dict()["provenance"] == s.provenance


def test_physics_parallel_is_a_deprecated_alias_of_cohezion_analogy():
    s = td.get_tradition("lakota").step_mappings[7]
    assert s.cohezion_analogy
    assert s.physics_parallel == s.cohezion_analogy


def test_aboriginal_four_fabrics_row_does_not_conflate_moiety_with_four_section():
    row = td.get_tradition("aboriginal").step_mappings[3]
    text = f"{row.indigenous_term} {row.description}".lower()
    # The old row paired "Four-section kinship (moieties)" with "Dual moiety system".
    assert "four-section kinship (moieties)" not in text
    assert "dual moiety system" not in text
    assert "section" in text and "moiet" in text  # both named, and distinguished
    assert "two" in text and "four" in text


def test_pan_regional_entries_carry_scope_notes():
    for slug in ("aboriginal", "amazonian", "andean", "inuit"):
        assert td.get_tradition(slug).scope_note.strip(), slug


def test_convergences_labelled_as_interpretive():
    for c in td.get_convergences():
        assert "interpretive" in c.to_dict()["basis"].lower()


def _run(coro):
    return asyncio.run(coro)


def test_api_responses_carry_interpretive_notice():
    """Covers the handler functions directly.

    NOTE: ``worldviews_router`` is not mounted in ``cohezion.api:app`` (2026-09-21), so
    there is no live route to exercise; this tests the handlers, not a served endpoint.
    """
    responses = [
        _run(api.list_traditions()),
        _run(api.get_tradition_detail("aboriginal")),
        _run(api.list_convergences()),
        _run(api.get_step_comparison(3)),
        _run(api.list_speculative_frameworks()),
    ]
    for body in responses:
        assert body["notice"] == td.INTERPRETIVE_NOTICE
    assert "unreviewed" in td.INTERPRETIVE_NOTICE
    listed = {t["slug"] for t in responses[0]["traditions"]}
    assert "stealthskater" not in listed
