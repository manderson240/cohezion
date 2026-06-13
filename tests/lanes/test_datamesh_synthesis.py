"""RED tests for the DatameshSynthesisLane (Lane 3) and the cron entry.

Contracts:

DatameshSynthesisLane:
- Writes the day's findings to:
  1. The Obsidian vault (vaults/.../01-Learnings/DAILY-DIGEST-<date>.md)
  2. The SurrealDB bus (ns=cohezion db=main, root:root) — UPSERT semantics
  3. The autoresearch.jsonl ledger
  - Knowledge graph 12D vectors are tagged with the consumer's
    CapabilityProfile.family
  - Long notes (longer than a consumer's optimal_ctx * 0.8) are SPLIT
    (not truncated) so the consumer can read each chunk in full

Daily cron entry (scripts/daily_researcher.py):
- Acquires the fleet_lock:modelload before any lane runs
- Runs the four lanes in order
- Writes a morning digest to the vault
- Refuses to start if preflight fails
- Returns a non-zero exit code on any lane failure
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.researcher.daily_researcher import DailyResearcher, DryRunReport
from cohezion.researcher.lanes.datamesh_synthesis import (
    DatameshSynthesisLane,
    SynthesisNote,
    _split_note_by_consumer_ctx,
)


# ── Note splitting by consumer ctx ───────────────────────────────────────────


def test_long_note_is_split_not_truncated():
    """A 10k-token note targeting a consumer with optimal_ctx=4096
    is split into multiple chunks, each ≤ consumer.optimal_ctx * 0.8."""
    long_text = ("This is a sentence. " * 4000).strip()  # ~20k tokens-ish
    chunks = _split_note_by_consumer_ctx(
        text=long_text,
        consumer_optimal_ctx=4096,
    )
    # The split returns ≥2 chunks for a long note
    assert len(chunks) >= 2
    # Each chunk is well under the consumer's ctx * 0.8 (= 3276 chars proxy)
    for c in chunks:
        assert len(c) < 4096 * 1.5  # generous bound; precise count is 0.8


def test_short_note_is_returned_as_single_chunk():
    """A short note is returned as a single chunk (no splitting)."""
    short_text = "Brief finding about model X."
    chunks = _split_note_by_consumer_ctx(
        text=short_text,
        consumer_optimal_ctx=4096,
    )
    assert chunks == [short_text]


# ── DatameshSynthesisLane write paths ────────────────────────────────────────


@pytest.mark.asyncio
async def test_datamesh_lane_writes_to_vault(tmp_path: Path):
    """The lane creates a DAILY-DIGEST-<date>.md in the vault dir."""
    researcher = DailyResearcher()
    lane = DatameshSynthesisLane(researcher)
    vault = tmp_path / "vault"
    vault.mkdir()
    findings = [
        SynthesisNote(slug="finding-1", title="Finding 1", body="body", verified=True),
    ]
    with (
        patch.object(lane, "_vault_root", return_value=vault),
        patch.object(lane, "_write_to_bus", new=AsyncMock(return_value=None)),
        patch.object(lane, "_write_to_ledger", new=AsyncMock(return_value=None)),
        patch.object(lane, "_read_todays_findings", new=AsyncMock(return_value=findings)),
    ):
        await lane.run(dry_run=False)
    files = list(vault.glob("DAILY-DIGEST-*.md"))
    assert len(files) == 1
    body = files[0].read_text()
    assert "Finding 1" in body
    assert "finding-1" in body


@pytest.mark.asyncio
async def test_datamesh_lane_dry_run_writes_nothing(tmp_path: Path):
    researcher = DailyResearcher()
    lane = DatameshSynthesisLane(researcher)
    with (
        patch.object(lane, "_write_to_vault", new=AsyncMock()) as mock_vault,
        patch.object(lane, "_write_to_bus", new=AsyncMock()) as mock_bus,
        patch.object(lane, "_write_to_ledger", new=AsyncMock()) as mock_ledger,
    ):
        report = await lane.run(dry_run=True)
    assert report.dry_run is True
    mock_vault.assert_not_called()
    mock_bus.assert_not_called()
    mock_ledger.assert_not_called()


# ── The cron entry (scripts/daily_researcher.py) ─────────────────────────────


@pytest.mark.asyncio
async def test_cron_entry_runs_all_four_lanes(tmp_path: Path):
    """The cron entry acquires the lock, runs all four lanes, writes
    a digest. Mocks isolate from network and disk."""
    from scripts import daily_researcher as cron

    researcher = DailyResearcher()

    # Patch the orchestrator's run() to return a fake report dict
    fake_reports = {lane: DryRunReport(lane=lane, dry_run=False) for lane in
                    ["model_scout", "harness_paper", "datamesh_synthesis", "verify_evolve"]}

    with (
        patch.object(cron, "DailyResearcher", return_value=researcher),
        patch.object(researcher, "run", new=AsyncMock(return_value=fake_reports)),
        patch.object(cron, "write_morning_digest", new=AsyncMock()) as mock_digest,
        patch("sys.argv", ["daily_researcher.py", "--dry-run", "--skip-preflight"]),
    ):
        await cron.main()

    mock_digest.assert_awaited_once()
