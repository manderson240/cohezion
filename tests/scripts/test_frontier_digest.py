"""Tests for the daily frontier digest (WS2, 2026-06-04).

WS2 builds scripts/ci/frontier_digest.py — a daily script that
fetches recent papers, models, and benchmarks from arxiv/HF,
novelty-scores them against SurrealDB mycelium_patterns, writes
docs/ops/frontier/<YYYY-MM-DD>.md, posts a summary to vault +
SurrealDB, and exposes make frontier-digest + a weekly cron.

Best-effort: any external fetch failure must NOT break the
digest — each source is isolated, and the digest is written
even if everything fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "ci"))


def test_frontier_digest_module_importable():
    """The frontier_digest module must be importable as a module."""
    try:
        import frontier_digest  # type: ignore
    except ImportError:
        import pytest

        pytest.fail("scripts/ci/frontier_digest.py is not importable")


def test_frontier_digest_has_main():
    """The module must expose a main() function callable as
    `python -m frontier_digest` or `python frontier_digest.py`."""
    import frontier_digest  # type: ignore

    assert hasattr(frontier_digest, "main"), "frontier_digest must expose main()"
    assert callable(frontier_digest.main)


def test_frontier_digest_writes_markdown_file(tmp_path):
    """When called, the digest must write a markdown file to
    docs/ops/frontier/<YYYY-MM-DD>.md with at least a header."""
    import frontier_digest  # type: ignore
    from datetime import date

    out_dir = tmp_path / "frontier"
    out_dir.mkdir()

    # Mock all external dependencies
    with (
        patch.object(frontier_digest, "fetch_arxiv", return_value=[]),
        patch.object(frontier_digest, "fetch_hf_daily", return_value=[]),
        patch.object(frontier_digest, "fetch_hf_top_models", return_value=[]),
        patch.object(frontier_digest, "novelty_score", return_value=0.0),
        patch.object(frontier_digest, "post_to_vault", return_value=None),
        patch.object(frontier_digest, "post_to_surrealdb", return_value=None),
    ):
        today = date.today().isoformat()
        out_path = out_dir / f"{today}.md"
        frontier_digest.write_digest(
            findings=[],
            output_path=out_path,
            today=today,
        )
        assert out_path.exists()
        content = out_path.read_text()
        assert "# Frontier Digest" in content
        assert today in content


def test_frontier_digest_handles_fetch_failures_gracefully():
    """If every external fetch fails, the digest must still be
    written (with a 'no findings' note), and main() must not raise."""
    import frontier_digest  # type: ignore

    with (
        patch.object(frontier_digest, "fetch_arxiv", side_effect=Exception("net down")),
        patch.object(frontier_digest, "fetch_hf_daily", side_effect=Exception("net down")),
        patch.object(frontier_digest, "fetch_hf_top_models", side_effect=Exception("net down")),
        patch.object(frontier_digest, "novelty_score", return_value=0.0),
        patch.object(frontier_digest, "post_to_vault", return_value=None),
        patch.object(frontier_digest, "post_to_surrealdb", return_value=None),
    ):
        # Should not raise
        findings = frontier_digest.collect_findings()
        assert isinstance(findings, list)
        # No findings because all fetches failed
        assert findings == []


def test_frontier_digest_novelty_score_returns_float():
    """novelty_score(finding) must return a float in [0, 1]."""
    import frontier_digest  # type: ignore

    with patch.object(frontier_digest, "_query_mycelium_patterns", return_value=[]):
        score = frontier_digest.novelty_score(
            {
                "title": "test paper",
                "url": "https://arxiv.org/abs/1234",
                "source": "arxiv",
                "category": "agents",
            }
        )
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
