"""Tests for the research-brief → DataProduct/kanban bridge.

All logic under test is pure/offline: brief parsing, verdict→actionability
mapping, the contamination guard, and the idempotent carding DECISION. The
SurrealDB / event side-effects are injectable so these run with no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.data_mesh.research_products import (
    ResearchFinding,
    card_finding,
    ingest_brief,
    parse_brief,
)


# --- fixtures ---------------------------------------------------------------

_CLEAN_ACTIONABLE = """\
---
title: Sample Tool — lemonade research
date: 2026-07-16
tags: [research, lemonade, agentic]
model: deepseek-r1-0528-8b-FLM (XDNA2 NPU via :13305)
source: https://github.com/example/sample-tool
---

## Relevance to Cohezion
Sample Tool provides a function-calling loop that runs on the local :13305 endpoint.
It adds atomic tool execution useful for the agent loop.

## Verdict
Integrate: adopt the function-calling loop with minimal effort.
"""

# Mirrors the real ai-agent-skills hallucination: attributes Cohezion-internal
# artifacts (SkillRefiner / SkillConsensusVoter / 215 PRIME) to the EXTERNAL repo.
_CONTAMINATED = """\
---
title: External Repo — lemonade research
date: 2026-07-16
tags: [research, skills]
model: deepseek-r1-0528-8b-FLM
source: https://github.com/example/external-repo
---

## Relevance to Cohezion
The library uses a curator-driven workflow with SkillRefiner and SkillConsensusVoter for quality control.
It offers 215 skills in PRIME format.

## Verdict
Adopt fully: import the skills into the registry.
"""

# Internal names appear, but framed as comparison to OUR stack ("your"/"existing")
# — must NOT be flagged as contamination (this is the qwen-agent / llm-council shape).
_MARKERS_BUT_CLEAN = """\
---
title: Comparison Tool — lemonade research
date: 2026-07-16
tags: [research, council]
model: deepseek-r1-0528-8b-FLM
source: https://github.com/example/comparison-tool
---

## Relevance to Cohezion
Your existing SkillConsensusVoter already covers voting; this tool complements the compound loop.

### SkillConsensusVoter Integration
Use it alongside your voter.

## Verdict
Watch: monitor for later.
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


# --- parsing ----------------------------------------------------------------


def test_parse_extracts_frontmatter_and_sections(tmp_path: Path) -> None:
    f = parse_brief(_write(tmp_path, "clean.md", _CLEAN_ACTIONABLE))
    assert isinstance(f, ResearchFinding)
    assert f.title == "Sample Tool — lemonade research"
    assert f.source == "https://github.com/example/sample-tool"
    assert f.date == "2026-07-16"
    assert "lemonade" in f.tags and "agentic" in f.tags
    assert "deepseek-r1" in f.model
    assert "function-calling loop" in f.relevance
    assert "integrate" in f.verdict_text.lower()


def test_parse_returns_none_for_non_brief(tmp_path: Path) -> None:
    assert parse_brief(_write(tmp_path, "junk.md", "no frontmatter here")) is None


def test_domain_from_tags_skips_boilerplate(tmp_path: Path) -> None:
    f = parse_brief(_write(tmp_path, "clean.md", _CLEAN_ACTIONABLE))
    # 'research' and 'lemonade' are boilerplate tags — domain is the first real one.
    assert f.domain == "agentic"


# --- verdict → actionability -----------------------------------------------


@pytest.mark.parametrize(
    "verdict,expected",
    [
        ("Integrate: do it now", "actionable"),
        ("**Adopt fully**", "actionable"),
        ("Adopt / Watch Closely", "actionable"),
        ("Worth an experiment on the fleet", "actionable"),
        ("**Watch**", "monitor"),
        ("Bookmark this page as a resource", "monitor"),
        ("yes + rich topic", "monitor"),
        ("Ignore — not relevant to Cohezion", "drop"),
        # options-menu template: the words in the menu must not decide; the
        # real answer ("Context-ONLY") follows and maps to monitor.
        ("**act / watch / context-only / ignore:** Context-ONLY.", "monitor"),
    ],
)
def test_verdict_maps_to_actionability(verdict: str, expected: str) -> None:
    from cohezion.data_mesh.research_products import classify_actionability

    assert classify_actionability(verdict) == expected


def test_headerless_verdict_defaults_to_monitor(tmp_path: Path) -> None:
    text = _CLEAN_ACTIONABLE.replace(
        "## Verdict\nIntegrate: adopt the function-calling loop with minimal effort.\n", ""
    )
    f = parse_brief(_write(tmp_path, "noverdict.md", text))
    assert f.verdict_text == ""
    assert f.actionability == "monitor"  # conservative: no card


# --- contamination guard ----------------------------------------------------


def test_contamination_guard_flags_prompt_echo(tmp_path: Path) -> None:
    f = parse_brief(_write(tmp_path, "bad.md", _CONTAMINATED))
    assert f.actionability == "actionable"  # verdict says adopt...
    assert f.confidence == "low"  # ...but the relevance is a hallucination
    assert f.confidence_reason == "prompt-echo"
    assert f.should_card is False  # low-confidence actionable is NOT carded


def test_clean_actionable_is_high_confidence_and_cards(tmp_path: Path) -> None:
    f = parse_brief(_write(tmp_path, "clean.md", _CLEAN_ACTIONABLE))
    assert f.actionability == "actionable"
    assert f.confidence == "high"
    assert f.confidence_reason == ""
    assert f.should_card is True


def test_internal_markers_with_cohezion_cue_not_flagged(tmp_path: Path) -> None:
    # Markers present but framed as "your existing / complements" comparison.
    f = parse_brief(_write(tmp_path, "cmp.md", _MARKERS_BUT_CLEAN))
    assert f.confidence == "high"
    assert f.confidence_reason == ""
    assert f.actionability == "monitor"  # verdict = watch


# --- DataProduct projection -------------------------------------------------


def test_to_data_product(tmp_path: Path) -> None:
    f = parse_brief(_write(tmp_path, "clean.md", _CLEAN_ACTIONABLE))
    dp = f.to_data_product()
    assert dp.owner_domain == "research"
    assert dp.product_id.startswith("research.")
    assert f.title in dp.name or dp.name == f.title


# --- idempotent carding -----------------------------------------------------


def test_carding_decision_is_idempotent_by_url(tmp_path: Path) -> None:
    f = parse_brief(_write(tmp_path, "clean.md", _CLEAN_ACTIONABLE))
    calls: list[dict] = []

    def fake_persist(item: dict) -> dict[str, bool]:
        calls.append(item)
        return {"surreal": True, "obsidian": True}

    # First card: URL not present in the (injected) existing set → persists once.
    r1 = card_finding(f, existing_urls=set(), persist=fake_persist)
    assert r1 is True
    assert len(calls) == 1
    assert calls[0]["url"] == f.source
    assert calls[0]["type"] == "research-finding"

    # Second card: URL already in the sink → skip, no second persist.
    r2 = card_finding(f, existing_urls={f.source}, persist=fake_persist)
    assert r2 is False
    assert len(calls) == 1


def test_ingest_brief_side_effects_off_returns_finding_without_carding(tmp_path: Path) -> None:
    f = ingest_brief(_write(tmp_path, "clean.md", _CLEAN_ACTIONABLE), do_side_effects=False)
    assert isinstance(f, ResearchFinding)
    assert f.should_card is True  # would card, but side-effects were disabled
