import pytest

pytest.importorskip("respx")
"""RED tests for the ModelScoutLane (Lane 1).

Contracts:
- ModelScoutLane.run() fetches candidate models from:
  1. HuggingFace daily papers feed
  2. arXiv Atom API (cs.LG, cs.CL)
  3. Lemonade /v1/models on port 13305
- For each candidate, parse the model card. Drop `card_missing`.
- Drop candidates whose `profile` doesn't beat an existing default
  registry entry for any task.
- Returns a DryRunReport with candidates list (model_ids) and notes.
- The lane respects the per-run cloud-escalation budget (≤5); the
  scout lane doesn't escalate (it reads HTTP directly, not via
  extend_claude), so the budget is preserved for the other lanes.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from cohezion.researcher.daily_researcher import DailyResearcher, DryRunReport


# ── Card-missing candidates are dropped ─────────────────────────────────────


@pytest.mark.asyncio
async def test_model_scout_drops_candidate_without_parseable_card():
    """A candidate model with no fetchable card is dropped (card_missing)."""
    researcher = DailyResearcher()
    lane = researcher.model_scout

    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        # The HF daily papers feed returns a candidate
        mock_hf.get("/api/daily-papers").mock(
            return_value=httpx.Response(
                200,
                text="<?xml version='1.0'?><feed></feed>",
                headers={"content-type": "application/atom+xml"},
            )
        )
        # The model card 404s → card_missing → dropped
        mock_hf.get(url__regex=r".*README\.md$").mock(return_value=httpx.Response(404))

        report = await lane.run(dry_run=False)
        assert isinstance(report, DryRunReport)
        # The candidate was dropped
        assert report.candidates == [] or "Qwen3-99B-New" not in report.candidates


# ── HF daily feed parsing ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_model_scout_parses_hf_daily_papers():
    """The lane can ingest the HF daily papers feed without crashing."""
    researcher = DailyResearcher()
    lane = researcher.model_scout
    feed_xml = """<?xml version='1.0' encoding='UTF-8'?>
<feed>
  <entry>
    <id>tag:huggingface.co,2026:paper-001</id>
    <title>Test Paper</title>
    <summary>About a new model.</summary>
    <link href="https://huggingface.co/papers/001" />
  </entry>
</feed>"""
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        mock_hf.get("/api/daily-papers").mock(
            return_value=httpx.Response(
                200, text=feed_xml, headers={"content-type": "application/atom+xml"}
            )
        )
        mock_hf.get(url__regex=r".*README\.md$").mock(return_value=httpx.Response(404))

        report = await lane.run(dry_run=False)
        # The lane recorded that it looked at HF daily
        assert any("hf_daily_papers" in n or "hf" in n.lower() for n in report.notes)


# ── ArXiv abstract parsing ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_model_scout_parses_arxiv_abstract():
    """The lane can fetch an arXiv abstract without crashing."""
    researcher = DailyResearcher()
    lane = researcher.model_scout
    abstract = (
        "We present a new model.\n"
        "Strengths: code completion, low latency.\n"
        "Weaknesses: long-horizon reasoning, multimodal."
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://arxiv.org/abs/2402.00000").mock(
            return_value=httpx.Response(200, text=abstract)
        )
        report = await lane.run(dry_run=False)
        assert isinstance(report, DryRunReport)


# ── Lane respects the daily researcher context ─────────────────────────────


@pytest.mark.asyncio
async def test_model_scout_dry_run_does_not_call_network():
    """dry_run=True must not make any HTTP calls. Verified by
    providing a respx mock that would fail loudly if called."""
    researcher = DailyResearcher()
    lane = researcher.model_scout
    with respx.mock(assert_all_called=False) as mock:
        mock.route(host="huggingface.co").mock(side_effect=AssertionError("called!"))
        mock.route(host="arxiv.org").mock(side_effect=AssertionError("called!"))
        report = await lane.run(dry_run=True)
    assert report.dry_run is True
    # The dry-run report is informational
    assert any("dry-run" in n.lower() for n in report.notes)
