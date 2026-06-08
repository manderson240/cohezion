"""Item 270: dorahacks_monitor.py — hackathon intelligence loop arm (2026-06-08).

Falsifiable checks (unit-testable, no network, no LLM required):

  1. PRIMARY DISC.: score_keyword gives >=7 for AI/LLM-rich hackathon.
     Kills impl whose scorer never exceeds the threshold for relevant hacks.
  2. score_keyword gives 0 for cooking/sports hackathon.
     Kills impl that gives every hackathon the same score.
  3. append_to_feed appends (never truncates) to an existing feed file.
     Kills impl that overwrites the file instead of appending.
  4. fetch_hackathons returns [] without raising when no cookie is set.
     Kills impl that raises on missing auth.
  5. Script exits 0 in dry-run mode (even with no cookie).
     Kills impl that crashes without a live network connection.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
SCRIPT = REPO / "scripts" / "dorahacks_monitor.py"

# Import the module functions directly for unit testing
sys.path.insert(0, str(REPO / "scripts"))


def test_ai_llm_hackathon_scores_high() -> None:
    """score_keyword gives >=7 for an AI/LLM-rich hackathon.

    PRIMARY DISCRIMINATOR: kills impl whose keyword scorer never hits >=7.
    Title with 6 RELEVANCE_KEYWORDS -> min(10, 6*2) = 10.
    """
    from dorahacks_monitor import score_keyword

    hack = {
        "title": "AI LLM neural generative agent inference challenge",
        "tags": ["open source", "deep learning"],
    }
    score = score_keyword(hack)
    assert score >= 7, f"AI/LLM hackathon must score >=7; got {score}"


def test_cooking_hackathon_scores_zero() -> None:
    """score_keyword gives 0 for an irrelevant cooking/sports hackathon.

    Kills impl that returns a non-zero score for clearly irrelevant hacks.
    """
    from dorahacks_monitor import score_keyword

    hack = {
        "title": "Ultimate cooking championship for amateur chefs",
        "tags": ["food", "culinary"],
    }
    score = score_keyword(hack)
    assert score == 0, f"Cooking hackathon must score 0; got {score}"


def test_append_to_feed_appends_not_truncates() -> None:
    """append_to_feed appends to an existing file, not overwrites.

    Kills impl that opens the file in 'w' mode instead of 'a'.
    """
    from dorahacks_monitor import append_to_feed

    # Use a temp file to avoid touching the real feed
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        tmp_path = Path(f.name)
        f.write("# Existing content\n\n")

    import dorahacks_monitor as mod

    original_feed = mod.FEED_PATH
    mod.FEED_PATH = tmp_path
    try:
        hack = {
            "title": "Test Hackathon",
            "url": "https://dorahacks.io/hackathon/test",
            "prize": "$1k",
            "deadline": "2026-07-01",
            "tags": ["AI"],
        }
        append_to_feed(hack, 8, "2026-06-08 00:00 UTC")
        content = tmp_path.read_text(encoding="utf-8")
        assert "# Existing content" in content, "Original content must be preserved"
        assert "Test Hackathon" in content, "New entry must be appended"
    finally:
        mod.FEED_PATH = original_feed
        tmp_path.unlink(missing_ok=True)


def test_fetch_hackathons_returns_empty_without_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_hackathons returns [] without raising when DORAHACKS_COOKIE is unset.

    Kills impl that raises PermissionError or network error when no auth.
    The function handles the missing-cookie case gracefully.
    """
    import dorahacks_monitor as mod

    monkeypatch.delenv("DORAHACKS_COOKIE", raising=False)
    result = mod.fetch_hackathons()
    assert result == [], "No cookie -> []; got " + repr(result)


def test_script_exits_zero_in_dry_run_no_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """Script exits 0 in --dry-run mode even with no cookie.

    Kills impl that crashes without a live network connection.
    """
    env = {k: v for k, v in __import__("os").environ.items() if k != "DORAHACKS_COOKIE"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--no-inference"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert result.returncode == 0, (
        "Script must exit 0 in dry-run with no cookie; got "
        + repr(result.returncode)
        + "\nstderr: "
        + result.stderr[-200:]
    )
