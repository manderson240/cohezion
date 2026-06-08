"""Item 272: dorahacks_feed_summary() — parse DORAHACKS_FEED.md by score tier (2026-06-08).

``dorahacks_feed_summary(feed_path) -> dict``:
Parses DORAHACKS_FEED.md and returns entries grouped into three tiers:
- top (score >= 9), good (7 <= score <= 8), marginal (score < 7)
Returns {"total": int, "top": list[dict], "good": list[dict], "marginal": list[dict]}.
Empty feed -> all-empty lists. Pure parser (no network, no LLM).

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: tier counts are correct (top=>=9, good=7-8, marginal=<7).
     Kills impl that puts all entries in "top".
  2. Empty feed -> all-empty lists without raising.
     Kills impl that raises on empty/missing file.
  3. entry URL is non-empty for each parsed entry.
     Kills impl that loses the URL field.
  4. total == len(top) + len(good) + len(marginal).
     Verifies partition covers all entries.
  5. Return type is dict with exactly four keys.
     Kills impl returning a list.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(REPO / "scripts"))


SAMPLE_FEED = """# DoraHacks Hackathon Feed

## AI Agents World Cup
- **URL:** https://dorahacks.io/hackathon/ai-agents-world-cup
- **AI-relevance score:** 10/10
- **Prize:** $50k
- **Deadline:** 2026-08-01
- **Tags:** AI, LLM, agents
- **Added:** 2026-06-08 00:00 UTC
- **Status:** OPPORTUNITY

## LLM Innovation Sprint
- **URL:** https://dorahacks.io/hackathon/llm-sprint
- **AI-relevance score:** 8/10
- **Prize:** $10k
- **Deadline:** 2026-09-01
- **Tags:** LLM, generative
- **Added:** 2026-06-08 00:00 UTC
- **Status:** OPPORTUNITY

## Open Source Tools Jam
- **URL:** https://dorahacks.io/hackathon/oss-tools
- **AI-relevance score:** 7/10
- **Prize:** $5k
- **Deadline:** 2026-07-15
- **Tags:** open source
- **Added:** 2026-06-08 00:00 UTC
- **Status:** OPPORTUNITY

## Cooking With Code
- **URL:** https://dorahacks.io/hackathon/cooking
- **AI-relevance score:** 2/10
- **Prize:** $1k
- **Deadline:** 2026-07-01
- **Tags:** food
- **Added:** 2026-06-08 00:00 UTC
- **Status:** OPPORTUNITY
"""


def test_tier_counts_are_correct() -> None:
    """Entries are bucketed into top (>=9), good (7-8), marginal (<7).

    PRIMARY DISCRIMINATOR: kills impl that puts all entries in top.
    Sample: score=10 -> top, score=8 -> good, score=7 -> good, score=2 -> marginal.
    """
    from dorahacks_feed_summary import dorahacks_feed_summary

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_FEED)
        tmp = Path(f.name)
    result = dorahacks_feed_summary(tmp)
    assert len(result["top"]) == 1, "score=10 -> top; got " + str(len(result["top"]))
    assert len(result["good"]) == 2, "score=8,7 -> good; got " + str(len(result["good"]))
    assert len(result["marginal"]) == 1, "score=2 -> marginal; got " + str(len(result["marginal"]))
    tmp.unlink(missing_ok=True)


def test_empty_feed_returns_empty_lists() -> None:
    """Empty or missing feed -> all-empty lists without raising.

    Kills impl that raises on empty/missing file.
    """
    from dorahacks_feed_summary import dorahacks_feed_summary

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# DoraHacks Hackathon Feed\n\n")
        tmp = Path(f.name)
    result = dorahacks_feed_summary(tmp)
    assert result["total"] == 0
    assert result["top"] == []
    assert result["good"] == []
    assert result["marginal"] == []
    tmp.unlink(missing_ok=True)


def test_entry_url_is_non_empty() -> None:
    """Each parsed entry has a non-empty URL field.

    Kills impl that loses the URL during parsing.
    """
    from dorahacks_feed_summary import dorahacks_feed_summary

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_FEED)
        tmp = Path(f.name)
    result = dorahacks_feed_summary(tmp)
    for tier in ("top", "good", "marginal"):
        for entry in result[tier]:
            assert entry.get("url"), f"URL must be non-empty in {tier} entry: {entry}"
    tmp.unlink(missing_ok=True)


def test_total_equals_sum_of_tiers() -> None:
    """total == len(top) + len(good) + len(marginal).

    Verifies the partition covers all entries.
    """
    from dorahacks_feed_summary import dorahacks_feed_summary

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_FEED)
        tmp = Path(f.name)
    result = dorahacks_feed_summary(tmp)
    total_in_tiers = len(result["top"]) + len(result["good"]) + len(result["marginal"])
    assert result["total"] == total_in_tiers, (
        f"total={result['total']} must equal sum of tiers {total_in_tiers}"
    )
    tmp.unlink(missing_ok=True)


def test_return_type_is_dict_with_four_keys() -> None:
    """Return type is dict with exactly four keys.

    Kills impl returning a list or dict with wrong keys.
    """
    from dorahacks_feed_summary import dorahacks_feed_summary

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_FEED)
        tmp = Path(f.name)
    result = dorahacks_feed_summary(tmp)
    assert isinstance(result, dict), "Must return dict"
    assert set(result.keys()) == {"total", "top", "good", "marginal"}, (
        "Must have exactly four keys; got " + str(set(result.keys()))
    )
    tmp.unlink(missing_ok=True)
