"""Item 270: DoraHacks hackathon monitor — unit tests (2026-06-08).

Tests for ``scripts/dorahacks_monitor.py`` (report-only intelligence monitor).
Sign-up is human-gated (Google OAuth required); tests only verify the
keyword scorer, HTML parser, feed-append logic, and error-resilience.
No live network calls are made.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: parser extracts hackathon entries from mock HTML
     containing /hackathon/ href links.
     Kills impl that returns [] for any HTML input, or fails to strip
     query-params / trailing slashes from URLs.
  2. AI-tagged hackathon scores ≥ 7 via keyword scorer.
     Kills impl that uses a flat count with multiplier < 2, or uses
     the wrong keyword set (e.g. only "AI" not "llm"/"agent").
  3. Cooking/sports hackathon scores < 7 (specifically 0) via keyword scorer.
     Kills impl that returns a non-zero score for irrelevant content.
  4. feed append does NOT truncate existing content.
     Kills impl that opens the feed with "w" instead of "a".
  5. fetch_hackathons returns [] (no crash) when DORAHACKS_COOKIE is unset.
     Kills impl that raises EnvironmentError or tries a network call
     without the cookie guard.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts/ dir to import path so we can import dorahacks_monitor directly
_SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import dorahacks_monitor as dm  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 (PRIMARY DISC.): HTML parser extracts entries from mock HTML
# ---------------------------------------------------------------------------


_MOCK_HTML = """
<!DOCTYPE html>
<html><body>
  <a href="/hackathon/ai-agents-2026">
    <span class="hackathon-title">AI Agents 2026</span>
    <span class="hackathon-prize">$50,000</span>
    <span class="hackathon-tag">AI</span>
    <span class="hackathon-tag">LLM</span>
  </a>
  <a href="/hackathon/web3-build?ref=home">
    <span class="hackathon-title">Web3 Build</span>
    <span class="hackathon-tag">blockchain</span>
  </a>
  <!-- should be ignored: not a hackathon link -->
  <a href="/hackathon">Top-level link — no slug</a>
  <a href="https://external.com/hackathon/other">External link — ignored</a>
</body></html>
"""


def test_parser_extracts_entries_from_mock_html() -> None:
    """PRIMARY DISC.: parser returns entries from /hackathon/<slug> hrefs.

    Kills impl that returns [] for any HTML, or fails to filter
    the bare /hackathon href.
    """
    parser = dm._DoraHacksParser()
    parser.feed(_MOCK_HTML)
    hackathons = parser.hackathons
    urls = [h["url"] for h in hackathons]
    # Must find the two /hackathon/<slug> entries
    assert any("ai-agents-2026" in u for u in urls), (
        "parser must extract /hackathon/ai-agents-2026; got: " + repr(urls)
    )
    assert any("web3-build" in u for u in urls), (
        "parser must extract /hackathon/web3-build; got: " + repr(urls)
    )
    # Query-string must be stripped from URL
    for h in hackathons:
        assert "?" not in h["url"], "URL must not contain query params; got: " + repr(h["url"])
    # The bare /hackathon href must NOT produce an entry
    assert not any(h["url"].rstrip("/") == "https://dorahacks.io/hackathon" for h in hackathons), (
        "bare /hackathon href must not become an entry"
    )


# ---------------------------------------------------------------------------
# Test 2: AI-tagged hackathon scores ≥ 7 via keyword scorer
# ---------------------------------------------------------------------------


def test_ai_hackathon_scores_high_via_keyword() -> None:
    """AI hackathon with multiple AI keywords scores ≥ 7.

    Kills impl with multiplier < 2, or wrong keyword set (case-insensitive
    mismatch, missing "agent"/"llm" etc.).
    """
    hackathon = {
        "title": "LLM Agents Challenge",
        "tags": ["AI", "LLM", "open source"],
        "prize": "$10,000",
        "deadline": "2026-07-01",
    }
    score = dm.score_keyword(hackathon)
    assert score >= 7, f"LLM/AI/open-source hackathon must score ≥ 7; got {score}"


# ---------------------------------------------------------------------------
# Test 3: Cooking/sports hackathon scores 0 via keyword scorer
# ---------------------------------------------------------------------------


def test_irrelevant_hackathon_scores_zero_via_keyword() -> None:
    """Cooking and sports hackathons score 0 (no matching AI keywords).

    Kills impl that applies a non-zero base score, or wrongly matches
    unrelated words against the AI_KEYWORDS set.
    """
    hackathon = {
        "title": "Cooking & Sports Innovate",
        "tags": ["food", "sports", "wellness"],
        "prize": "$1,000",
        "deadline": "2026-07-01",
    }
    score = dm.score_keyword(hackathon)
    assert score == 0, f"Cooking/sports hackathon must score 0; got {score}"


# ---------------------------------------------------------------------------
# Test 4: Feed append does NOT truncate existing content
# ---------------------------------------------------------------------------


def test_feed_append_does_not_truncate(tmp_path: Path) -> None:
    """append_to_feed must append, never overwrite, existing feed content.

    Kills impl that opens with mode 'w' instead of 'a'.
    """
    feed = tmp_path / "DORAHACKS_FEED.md"
    # Write sentinel content that must survive the append
    sentinel = "# Sentinel content — must not be lost\n\n"
    feed.write_text(sentinel, encoding="utf-8")

    # Monkeypatch FEED_PATH to use our temp file
    original_feed = dm.FEED_PATH
    dm.FEED_PATH = feed
    try:
        hackathon = {
            "title": "New AI Hackathon",
            "url": "https://dorahacks.io/hackathon/new-ai",
            "prize": "$5,000",
            "deadline": "2026-08-01",
            "tags": ["AI"],
        }
        dm.append_to_feed(hackathon, score=8, ts="2026-06-08 00:00 UTC")
    finally:
        dm.FEED_PATH = original_feed

    content = feed.read_text(encoding="utf-8")
    assert sentinel in content, (
        "Existing feed content must be preserved after append; sentinel lost"
    )
    assert "New AI Hackathon" in content, "New entry must also appear in feed after append"


# ---------------------------------------------------------------------------
# Test 5: fetch_hackathons returns [] (no crash) when DORAHACKS_COOKIE unset
# ---------------------------------------------------------------------------


def test_fetch_returns_empty_without_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_hackathons() returns [] with no crash when DORAHACKS_COOKIE is unset.

    Kills impl that raises EnvironmentError or attempts a live network
    request without the cookie guard.
    """
    # Ensure the env var is absent
    monkeypatch.delenv(dm.COOKIE_ENV, raising=False)
    result = dm.fetch_hackathons()
    assert result == [], (
        f"fetch_hackathons() must return [] when DORAHACKS_COOKIE is unset; got {result!r}"
    )
