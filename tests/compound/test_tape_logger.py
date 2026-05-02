"""Tests for TapeLogger — deterministic LLM call recording and replay."""

import pytest

from cohezion.compound.tape_logger import TapeEntry, TapeLogger


@pytest.mark.unit
def test_start_stop_creates_file(tmp_path):
    logger = TapeLogger(tape_dir=tmp_path)
    tape = logger.start_tape("exec-1")
    stopped = logger.stop_tape()
    assert tape == stopped
    from pathlib import Path

    assert Path(tape).exists()


@pytest.mark.unit
def test_record_and_replay_roundtrip(tmp_path):
    logger = TapeLogger(tape_dir=tmp_path)
    logger.start_tape("exec-2")
    logger.record(
        "gpt-4o", "hello", "world", temperature=0.7, tokens_in=5, tokens_out=1, latency_ms=42.0
    )
    tape = logger.stop_tape()

    entries = list(logger.replay(tape))
    assert len(entries) == 1
    e = entries[0]
    assert isinstance(e, TapeEntry)
    assert e.model == "gpt-4o"
    assert e.prompt == "hello"
    assert e.response == "world"
    assert e.temperature == 0.7
    assert e.tokens_in == 5
    assert e.tokens_out == 1
    assert e.latency_ms == 42.0
    assert e.sequence == 0


@pytest.mark.unit
def test_get_response_by_sequence(tmp_path):
    logger = TapeLogger(tape_dir=tmp_path)
    logger.start_tape("exec-3")
    logger.record("m1", "p0", "r0")
    logger.record("m1", "p1", "r1")
    logger.record("m1", "p2", "r2")
    tape = logger.stop_tape()

    assert logger.get_response(tape, 0) == "r0"
    assert logger.get_response(tape, 2) == "r2"
    assert logger.get_response(tape, 99) is None


@pytest.mark.unit
def test_disabled_logger_is_noop(tmp_path):
    logger = TapeLogger(tape_dir=tmp_path, enabled=False)
    result = logger.start_tape("exec-4")
    assert result == ""
    logger.record("m", "p", "r")  # should not raise
    stopped = logger.stop_tape()
    assert stopped is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.unit
def test_multiple_entries_ordered(tmp_path):
    logger = TapeLogger(tape_dir=tmp_path)
    logger.start_tape("exec-5")
    for i in range(5):
        logger.record("model", f"prompt-{i}", f"response-{i}")
    tape = logger.stop_tape()

    entries = list(logger.replay(tape))
    assert len(entries) == 5
    assert [e.sequence for e in entries] == list(range(5))
    assert [e.response for e in entries] == [f"response-{i}" for i in range(5)]
