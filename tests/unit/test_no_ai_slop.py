"""Unit tests for No AI Slop verifier and style auditor."""

from cohezion.text.no_ai_slop_verifier import NoAiSlopVerifier


def test_clean_text_passes_with_perfect_score():
    verifier = NoAiSlopVerifier()
    text = (
        "We built a deterministic compiler for ARC-AGI rules. "
        "It caches intermediate state vectors in SQLite and evaluates tasks in 14ms."
    )
    report = verifier.audit_text(text)
    assert report.is_clean
    assert report.score == 1.0
    assert len(report.violations) == 0


def test_detects_banned_buzzwords():
    verifier = NoAiSlopVerifier()
    text = "We delve into this transformative realm to leverage cutting-edge tools and empower our users."
    report = verifier.audit_text(text)
    assert not report.is_clean
    categories = {v.category for v in report.violations}
    assert "banned_word" in categories
    words = {v.snippet.lower() for v in report.violations if v.category == "banned_word"}
    assert "delve" in words
    assert "transformative" in words
    assert "leverage" in words
    assert "cutting-edge" in words
    assert "empower" in words


def test_detects_throat_clearing_and_faux_insight():
    verifier = NoAiSlopVerifier()
    text = (
        "Here's the thing: What most people get wrong is simple.\n"
        "Let me be clear: At the end of the day, it's worth noting that data matters."
    )
    report = verifier.audit_text(text)
    assert not report.is_clean
    categories = {v.category for v in report.violations}
    assert "throat_clearing" in categories
    assert "faux_insight" in categories


def test_detects_importance_puffery():
    verifier = NoAiSlopVerifier()
    text = "This benchmark stands as a testament to our progress and marks a pivotal moment."
    report = verifier.audit_text(text)
    assert not report.is_clean
    categories = {v.category for v in report.violations}
    assert "importance_puffery" in categories


def test_ignores_code_blocks():
    verifier = NoAiSlopVerifier()
    text = """# Architecture Notes
This is a standard description of the module.

```python
def leverage_connection():
    # We utilize a robust connection pool here
    return True
```

The module handles connections directly.
"""
    report = verifier.audit_text(text)
    # The words 'leverage', 'utilize', and 'robust' inside code block should be ignored
    assert report.is_clean
    assert report.score == 1.0


def test_ignores_frontmatter():
    verifier = NoAiSlopVerifier()
    text = """---
name: robust-pipeline
description: leverage existing data
---

# Title
Real content with no slop words here.
"""
    report = verifier.audit_text(text)
    assert report.is_clean


def test_clean_text_applies_deterministic_fixes():
    verifier = NoAiSlopVerifier()
    text = "We utilize this method to leverage speed and streamline operations."
    cleaned, changes = verifier.clean_text(text)
    assert "use" in cleaned
    assert "simplify" in cleaned
    assert len(changes) >= 3
