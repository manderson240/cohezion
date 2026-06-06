"""Discriminating tests for geometric correspondence in the loop (user request 2026-06-06).

`geometric_correspondence(query, corpus, encoder)` operationalizes Learning 311: FLUME-encode a NEW
problem and the prior solved items, measure geometric correspondence (cosine structural overlap), and
surface the top-k PRIOR solutions to compound on. Advisory/report-only — it PROVIDES compound-
engineering context (which prior commit solved a geometrically-similar problem), never auto-applies.

Tests inject a DETERMINISTIC encoder so the contract is exact without the FLUME checkpoint. Each fails
a plausible wrong impl:
  - returns a far item above a near one → test_nearest_prior_surfaces_first,
  - ignores top_k / floor → test_top_k_limits / test_floor_excludes_unrelated,
  - non-deterministic or mutates → test_deterministic,
  - backlog corpus drops the commit ref → test_from_backlog_surfaces_prior_commit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from cohezion.compound.geometric_correspondence import (
    CorrespondenceMatch,
    correspondences_from_backlog,
    geometric_correspondence,
)


_VECS = {
    "alpha": np.array([1.0, 0.0, 0.0]),
    "alpha prime": np.array([0.99, 0.01, 0.0]),
    "beta": np.array([0.0, 1.0, 0.0]),
    "gamma": np.array([0.0, 0.0, 1.0]),
}


def _stub(text: str) -> np.ndarray:
    return _VECS.get(text, np.zeros(3))


def _corpus() -> list[dict]:
    return [
        {"text": "alpha", "ref": "aaa111"},
        {"text": "beta", "ref": "bbb222"},
        {"text": "gamma", "ref": "ccc333"},
    ]


def test_nearest_prior_surfaces_first() -> None:
    out = geometric_correspondence("alpha prime", _corpus(), encoder=_stub)
    assert out[0].ref == "aaa111"  # geometrically nearest prior solution
    assert out[0].score > 0.99
    assert isinstance(out[0], CorrespondenceMatch)


def test_top_k_limits() -> None:
    out = geometric_correspondence("alpha prime", _corpus(), encoder=_stub, top_k=1)
    assert len(out) == 1 and out[0].ref == "aaa111"


def test_floor_excludes_unrelated() -> None:
    out = geometric_correspondence("alpha prime", _corpus(), encoder=_stub, floor=0.5)
    assert [m.ref for m in out] == ["aaa111"]  # beta/gamma cosine ~0 excluded


def test_empty_corpus_empty() -> None:
    assert geometric_correspondence("alpha", [], encoder=_stub) == []


def test_deterministic_no_mutation() -> None:
    corpus = _corpus()
    before = [dict(c) for c in corpus]
    a = geometric_correspondence("alpha prime", corpus, encoder=_stub)
    b = geometric_correspondence("alpha prime", corpus, encoder=_stub)
    assert a == b
    assert corpus == before


def test_from_backlog_surfaces_prior_commit(tmp_path: Path) -> None:
    backlog = tmp_path / "B.md"
    backlog.write_text(
        "| # | Thread | Item | Falsifiable | Gating | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | A | **alpha** thing | check | additive | DONE aaa1111 (did alpha) |\n"
        "| 2 | A | **beta** thing | check | additive | DONE bbb2222 (did beta) |\n"
        "| 3 | A | **gamma** thing | check | additive | TODO |\n"
    )

    # Encoder keyed on the bolded title token so the corpus maps to known vectors.
    def enc(text: str) -> np.ndarray:
        for k in _VECS:
            if k in text:
                return _VECS[k]
        return np.zeros(3)

    out = correspondences_from_backlog("alpha prime", backlog_path=backlog, encoder=enc, top_k=2)
    assert out[0].ref == "aaa1111"  # the DONE commit of the geometrically-corresponding prior item
    # TODO rows have no commit → not in the corpus of prior SOLUTIONS.
    assert "ccc" not in {m.ref[:3] for m in out}


# --- item 67: compound_context_for (wires item 66 into the loop tick) -------------------------

from cohezion.compound.geometric_correspondence import compound_context_for


def _title_enc(text: str) -> np.ndarray:
    for k in _VECS:
        if k in text:
            return _VECS[k]
    return np.zeros(3)


_DONE_BACKLOG = (
    "| 1 | A | **alpha** thing | check | additive | DONE aaa1111 (did alpha) |\n"
    "| 2 | A | **beta** thing | check | additive | DONE bbb2222 (did beta) |\n"
)


def test_compound_context_surfaces_prior_commits(tmp_path: Path) -> None:
    b = tmp_path / "B.md"
    b.write_text(_DONE_BACKLOG)
    advisory = compound_context_for("alpha prime", backlog_path=b, encoder=_title_enc, top_k=2)
    assert "aaa1111" in advisory  # the geometrically-corresponding prior commit
    assert "compound" in advisory.lower()


def test_compound_context_novel_item(tmp_path: Path) -> None:
    # A backlog with only TODO rows → no prior SOLUTIONS → novel advisory.
    b = tmp_path / "B.md"
    b.write_text("| 1 | A | **alpha** thing | check | additive | TODO |\n")
    advisory = compound_context_for("alpha prime", backlog_path=b, encoder=_title_enc)
    assert "novel" in advisory.lower()
    assert "aaa" not in advisory


def test_compound_context_is_string_and_pure(tmp_path: Path) -> None:
    b = tmp_path / "B.md"
    b.write_text(_DONE_BACKLOG)
    a1 = compound_context_for("alpha prime", backlog_path=b, encoder=_title_enc)
    a2 = compound_context_for("alpha prime", backlog_path=b, encoder=_title_enc)
    assert isinstance(a1, str) and a1 == a2
