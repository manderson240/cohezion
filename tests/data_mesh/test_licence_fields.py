"""Licence as FIELDS, not prose (card 55cb4f3b9de1).

The card exists because a hand-kept tally of this exact question DRIFTED: it reported
"5 of 8" when the truth was "4 of 11". A tally over prose needs a human to re-count and
rots silently; a field is counted mechanically and cannot.

The cases below are the five subjects actually triaged on 2026-08-11. Two of the five
diverged, and both divergences were adoption-blocking — which is the entire argument for
storing the reported tag and the verified terms SEPARATELY rather than as one string.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.data_mesh.research_products import (
    ResearchFinding,
    _normalise_licence,
    parse_brief,
)


def _finding(tag: str = "", actual: str = "") -> ResearchFinding:
    return ResearchFinding(
        finding_id="f",
        title="t",
        source="s",
        date="2026-08-11",
        tags=[],
        model="m",
        verdict_text="Monitor.",
        relevance="",
        body="",
        actionability="monitor",
        licence_tag=tag,
        licence_actual=actual,
    )


class TestRealSubjectsFrom20260811:
    """Each row is a real triage result, not a synthetic example."""

    @pytest.mark.parametrize(
        ("subject", "tag", "actual", "diverges"),
        [
            # The two that diverged — both blocked adoption.
            ("archestra-ai", "NOASSERTION", "AGPL-3.0-only", True),
            ("Physics-Scaling/GeoPT", "NONE", "MIT-derived, own code unlicensed", True),
            # The three that agreed.
            ("matrixorigin/Memoria", "Apache-2.0", "Apache-2.0", False),
            ("Extrality/AirfRANS", "ODbL-1.0", "ODbL-1.0", False),
            ("thuml/Transolver", "MIT", "MIT", False),
        ],
    )
    def test_divergence_matches_the_triaged_truth(
        self, subject: str, tag: str, actual: str, diverges: bool
    ) -> None:
        assert _finding(tag, actual).licence_divergence is diverges, subject

    def test_two_of_five_diverged(self) -> None:
        """The count the prose tally got wrong. Mechanical now, so it cannot drift."""
        rows = [
            ("NOASSERTION", "AGPL-3.0-only"),
            ("NONE", "MIT-derived, own code unlicensed"),
            ("Apache-2.0", "Apache-2.0"),
            ("ODbL-1.0", "ODbL-1.0"),
            ("MIT", "MIT"),
        ]
        assert sum(_finding(t, a).licence_divergence for t, a in rows) == 2


class TestUnverifiedIsNotAgreement:
    """The dangerous default. A missing verification must never read as 'no problem'."""

    def test_missing_actual_is_not_divergence_and_not_verified(self) -> None:
        f = _finding(tag="MIT", actual="")
        assert f.licence_divergence is False
        assert f.licence_verified is False, "unverified must be distinguishable from agreeing"

    def test_missing_tag_is_not_divergence(self) -> None:
        assert _finding(tag="", actual="MIT").licence_divergence is False

    def test_both_missing_is_not_verified(self) -> None:
        f = _finding()
        assert f.licence_verified is False
        assert f.licence_divergence is False

    def test_agreement_and_unverified_are_distinguishable(self) -> None:
        """DISCRIMINATING: an implementation collapsing 'unverified' into 'agrees' passes
        every divergence test above and fails here. That collapse is what makes an
        unchecked repo look safe."""
        agreed = _finding("MIT", "MIT")
        unverified = _finding("MIT", "")
        assert agreed.licence_divergence == unverified.licence_divergence  # both False
        assert agreed.licence_verified != unverified.licence_verified  # but distinguishable


class TestNormalisation:
    def test_cosmetic_differences_are_not_divergence(self) -> None:
        assert _finding("mit", "MIT").licence_divergence is False
        assert _finding("Apache-2.0", " apache-2.0 ").licence_divergence is False

    def test_spdx_only_and_or_later_suffixes_fold(self) -> None:
        assert _normalise_licence("AGPL-3.0-only") == _normalise_licence("AGPL-3.0")
        assert _normalise_licence("GPL-2.0-or-later") == _normalise_licence("GPL-2.0")

    def test_undetermined_synonyms_fold_together(self) -> None:
        for v in ("NOASSERTION", "NONE", "UNKNOWN", "N/A", "-"):
            assert _normalise_licence(v) == "UNDETERMINED"

    def test_genuinely_different_licences_still_diverge(self) -> None:
        """DISCRIMINATING: normalisation must not become 'everything is equal'. An
        over-eager normaliser passes the cosmetic tests and silently hides real conflicts."""
        assert _finding("MIT", "AGPL-3.0").licence_divergence is True
        assert _finding("Apache-2.0", "GPL-3.0").licence_divergence is True
        assert _finding("MIT", "ODbL-1.0").licence_divergence is True

    def test_undetermined_versus_a_real_licence_diverges(self) -> None:
        """The archestra shape: the platform could not tell, a human read it and could."""
        assert _finding("NOASSERTION", "AGPL-3.0-only").licence_divergence is True


class TestParsedFromBriefs:
    _BRIEF = """---
title: Example
source: https://github.com/example/repo
date: 2026-08-11
licence_tag: NOASSERTION
licence_actual: AGPL-3.0-only
---

## Verdict
Monitor — copyleft.
"""

    def _write(self, tmp_path: Path, name: str, text: str) -> Path:
        p = tmp_path / name
        p.write_text(text)
        return p

    def test_frontmatter_fields_are_parsed(self, tmp_path: Path) -> None:
        f = parse_brief(self._write(tmp_path, "a.md", self._BRIEF))
        assert f is not None
        assert f.licence_tag == "NOASSERTION"
        assert f.licence_actual == "AGPL-3.0-only"
        assert f.licence_divergence is True

    def test_american_spelling_also_parsed(self, tmp_path: Path) -> None:
        brief = self._BRIEF.replace("licence_tag", "license_tag").replace(
            "licence_actual", "license_actual"
        )
        f = parse_brief(self._write(tmp_path, "b.md", brief))
        assert f is not None
        assert f.licence_tag == "NOASSERTION"

    def test_prose_section_fallback_for_pre_migration_briefs(self, tmp_path: Path) -> None:
        """Briefs already written in prose must not be silently dropped mid-migration."""
        brief = """---
title: Example
source: https://github.com/example/repo
---

## Licence
- licence_tag: MIT
- licence_actual: MIT

## Verdict
Monitor.
"""
        f = parse_brief(self._write(tmp_path, "c.md", brief))
        assert f is not None
        assert f.licence_tag == "MIT"
        assert f.licence_actual == "MIT"

    def test_brief_without_licence_leaves_fields_empty_not_guessed(self, tmp_path: Path) -> None:
        brief = """---
title: Example
source: https://github.com/example/repo
---

## Verdict
Monitor.
"""
        f = parse_brief(self._write(tmp_path, "d.md", brief))
        assert f is not None
        assert f.licence_tag == ""
        assert f.licence_actual == ""
        assert f.licence_verified is False


class TestBackwardCompatibility:
    def test_fields_default_empty_so_existing_callers_are_unaffected(self) -> None:
        f = ResearchFinding(
            finding_id="f",
            title="t",
            source="s",
            date="d",
            tags=[],
            model="m",
            verdict_text="v",
            relevance="r",
            body="b",
            actionability="monitor",
        )
        assert f.licence_tag == ""
        assert f.licence_actual == ""
        assert f.licence_verified is False
