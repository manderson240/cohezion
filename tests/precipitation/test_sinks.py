"""Tests for VaultSink, GitLedgerSink, and (if available) SurrealSink."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cohezion.precipitation.bus import PrecipitationBus
from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind
from cohezion.precipitation.sinks import (
    GitLedgerSink,
    SurrealSink,
    VaultSink,
    register_default_sinks,
)


def _mk(
    kind: PrecipitationKind = PrecipitationKind.WITNESS_MARK,
    *,
    universe_id: str = "u1",
    coherence: float = 0.6,
) -> PrecipitationEvent:
    return PrecipitationEvent(
        kind=kind,
        universe_id=universe_id,
        coherence=coherence,
        payload={"note": "unit test"},
    )


@pytest.mark.asyncio
async def test_vault_sink_writes_jsonl_by_day(tmp_path: Path) -> None:
    sink = VaultSink(vault_dir=tmp_path)
    event = _mk()
    await sink.write(event)

    day_file = (
        tmp_path / "precipitation" / f"events-{event.timestamp_valid.date().isoformat()}.jsonl"
    )
    assert day_file.exists()

    lines = day_file.read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event_id"] == event.event_id
    assert data["kind"] == event.kind.value
    assert data["universe_id"] == event.universe_id


@pytest.mark.asyncio
async def test_vault_sink_appends_multiple(tmp_path: Path) -> None:
    sink = VaultSink(vault_dir=tmp_path)
    for _ in range(5):
        await sink.write(_mk())

    files = list((tmp_path / "precipitation").glob("events-*.jsonl"))
    assert len(files) == 1
    assert len(files[0].read_text().strip().splitlines()) == 5


def test_vault_sink_iter_events(tmp_path: Path) -> None:
    sink = VaultSink(vault_dir=tmp_path)
    e1 = _mk()
    asyncio.run(sink.write(e1))

    events = VaultSink.iter_events(day=datetime.now(UTC).date(), vault_dir=tmp_path)
    assert len(events) == 1
    assert events[0]["event_id"] == e1.event_id


@pytest.mark.asyncio
async def test_git_ledger_sink_only_writes_selected_kinds(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    sink = GitLedgerSink(ledger_path=ledger)

    # Selected: WITNESS_MARK, TRAINING_CHECKPOINT, etc. (see _GIT_LEDGER_KINDS)
    await sink.write(_mk(PrecipitationKind.WITNESS_MARK))
    await sink.write(_mk(PrecipitationKind.TRAINING_CHECKPOINT))
    # Not selected: COSMOGONY_PHASE, COHERENCE_PEAK
    await sink.write(_mk(PrecipitationKind.COSMOGONY_PHASE))
    await sink.write(_mk(PrecipitationKind.COHERENCE_PEAK))

    lines = ledger.read_text().strip().splitlines()
    assert len(lines) == 2
    kinds = {json.loads(line)["kind"] for line in lines}
    assert kinds == {"witness_mark", "training_checkpoint"}


@pytest.mark.asyncio
async def test_register_default_sinks_attaches_vault_and_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COHEZION_VAULT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    bus = PrecipitationBus()
    await bus.start()
    sinks = register_default_sinks(bus, enable_surreal=False)
    assert "vault" in sinks
    assert "git" in sinks
    assert "surreal" not in sinks

    await bus.aemit(_mk(PrecipitationKind.WITNESS_MARK))
    await bus.flush()
    await bus.stop()

    vault_files = list((tmp_path / "precipitation").glob("events-*.jsonl"))
    git_files = list((tmp_path / "data" / "precipitation").glob("*.jsonl"))
    assert len(vault_files) == 1
    assert len(git_files) == 1


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("COHEZION_SKIP_SURREAL") == "1",
    reason="SurrealDB test disabled by env",
)
async def test_surreal_sink_happy_path_or_swallows_failure() -> None:
    """If SurrealDB is up at :8001, this inserts a row; otherwise it swallows
    the connection error without raising. Either outcome is acceptable."""
    sink = SurrealSink()
    event = _mk(PrecipitationKind.WITNESS_MARK, universe_id="test-surreal-sink")
    await sink.write(event)  # must not raise
    await sink.close()
