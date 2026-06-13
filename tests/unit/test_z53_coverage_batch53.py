"""Coverage batch Z53: tape_logger, retrospection_validator."""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Module 1: compound/tape_logger.py
# ---------------------------------------------------------------------------


class TestTapeLogger:
    def _make_logger(self, tmp_path, enabled=True):
        from cohezion.compound.tape_logger import TapeLogger

        return TapeLogger(tape_dir=str(tmp_path), enabled=enabled)

    def test_tape_entry_dataclass(self):
        from cohezion.compound.tape_logger import TapeEntry

        entry = TapeEntry(
            sequence=0,
            timestamp="2026-01-01T00:00:00Z",
            model="phi3:mini",
            prompt="hello",
            response="world",
            temperature=0.7,
            tokens_in=5,
            tokens_out=3,
            latency_ms=50.0,
        )
        assert entry.model == "phi3:mini"
        assert entry.tokens_in == 5

    def test_start_tape_creates_file(self, tmp_path):
        logger = self._make_logger(tmp_path)
        path_str = logger.start_tape("exec-001")
        assert path_str != ""
        assert "exec-001" in path_str

    def test_record_and_stop(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.start_tape("exec-001")
        logger.record(
            model="phi3:mini",
            prompt="test prompt",
            response="test response",
            temperature=0.7,
            tokens_in=3,
            tokens_out=2,
            latency_ms=25.0,
        )
        path = logger.stop_tape()
        assert path is not None
        assert Path(path).exists()

    def test_replay_yields_entries(self, tmp_path):

        logger = self._make_logger(tmp_path)
        logger.start_tape("exec-002")
        logger.record("phi3", "prompt1", "resp1", 0.7, 5, 3, 10.0)
        logger.record("phi3", "prompt2", "resp2", 0.7, 4, 2, 8.0)
        path = logger.stop_tape()

        entries = list(logger.replay(path))
        assert len(entries) == 2
        assert entries[0].sequence == 0
        assert entries[1].sequence == 1
        assert entries[0].response == "resp1"

    def test_get_response_by_sequence(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.start_tape("exec-003")
        logger.record("phi3", "p1", "response_zero", 0.7, 5, 3, 10.0)
        logger.record("phi3", "p2", "response_one", 0.7, 5, 3, 10.0)
        path = logger.stop_tape()

        assert logger.get_response(path, 0) == "response_zero"
        assert logger.get_response(path, 1) == "response_one"
        assert logger.get_response(path, 99) is None

    def test_disabled_logger_noop(self, tmp_path):
        logger = self._make_logger(tmp_path, enabled=False)
        path_str = logger.start_tape("exec-004")
        assert path_str == ""
        logger.record("phi3", "p", "r", 0.7, 1, 1, 5.0)
        stop_result = logger.stop_tape()
        assert stop_result is None

    def test_stop_tape_without_start_returns_none(self, tmp_path):
        logger = self._make_logger(tmp_path)
        result = logger.stop_tape()
        assert result is None


# ---------------------------------------------------------------------------
# Module 2: compound/retrospection_validator.py
# ---------------------------------------------------------------------------


class TestRetrospectionValidator:
    def _make_validator(self):
        from cohezion.compound.retrospection_validator import RetrospectionValidator

        return RetrospectionValidator()

    def _make_journey(
        self, n=3, start_coherence=0.4, end_coherence=0.7, start_ts=1000.0, end_ts=1060.0
    ):
        points = []
        for i in range(n):
            frac = i / max(n - 1, 1)
            coh = start_coherence + frac * (end_coherence - start_coherence)
            ts = start_ts + frac * (end_ts - start_ts)
            points.append(
                {"coherence": coh, "timestamp": ts, "metadata": {"success": end_coherence > 0.3}}
            )
        return points

    def test_validation_result_dataclass(self):
        from cohezion.compound.retrospection_validator import ValidationResult

        r = ValidationResult(valid=True, discrepancies=[], confidence=1.0)
        assert r.valid is True
        assert r.confidence == pytest.approx(1.0)

    def test_empty_journey_returns_valid_zero_confidence(self):
        validator = self._make_validator()
        result = validator.validate_summary({"success": True}, journey_points=[])
        assert result.valid is True
        assert result.confidence == pytest.approx(0.0)

    def test_correct_summary_all_checks_pass(self):
        validator = self._make_validator()
        journey = self._make_journey(
            n=5, start_coherence=0.4, end_coherence=0.7, start_ts=1000.0, end_ts=1060.0
        )
        summary = {
            "coherence_delta": 0.3,  # 0.7 - 0.4 = 0.3
            "steps_executed": 5,  # matches n=5
            "success": True,
            "duration_seconds": 60.0,
        }
        result = validator.validate_summary(summary, journey)
        assert result.valid is True
        assert result.confidence == pytest.approx(1.0)

    def test_wrong_coherence_delta_flagged(self):
        validator = self._make_validator()
        journey = self._make_journey(start_coherence=0.4, end_coherence=0.7)
        summary = {"coherence_delta": 0.9}  # wrong: actual is 0.3
        result = validator.validate_summary(summary, journey)
        assert not result.valid
        assert len(result.discrepancies) > 0

    def test_wrong_steps_executed_flagged(self):
        validator = self._make_validator()
        journey = self._make_journey(n=3)
        summary = {"steps_executed": 10}  # wrong: actual is 3
        result = validator.validate_summary(summary, journey)
        assert not result.valid

    def test_success_false_but_high_coherence_passes(self):
        validator = self._make_validator()
        journey = self._make_journey(start_coherence=0.4, end_coherence=0.7)
        summary = {"success": False}  # we claim failure — no contradiction
        result = validator.validate_summary(summary, journey)
        assert result.valid is True

    def test_success_true_but_low_coherence_flagged(self):
        validator = self._make_validator()
        journey = self._make_journey(start_coherence=0.1, end_coherence=0.2)  # low coherence
        summary = {"success": True}  # but low coherence
        result = validator.validate_summary(summary, journey)
        assert not result.valid

    def test_wrong_duration_flagged(self):
        validator = self._make_validator()
        journey = self._make_journey(start_ts=1000.0, end_ts=1060.0)  # 60s
        summary = {"duration_seconds": 120.0}  # wrong: actual is 60s
        result = validator.validate_summary(summary, journey)
        assert not result.valid

    def test_empty_summary_no_checks(self):
        validator = self._make_validator()
        journey = self._make_journey()
        result = validator.validate_summary({}, journey)
        assert result.valid is True
        assert result.confidence == pytest.approx(0.0)

    def test_confidence_partial_match(self):
        validator = self._make_validator()
        journey = self._make_journey(
            n=3, start_coherence=0.4, end_coherence=0.7, start_ts=1000.0, end_ts=1060.0
        )
        # Two checks: one right, one wrong
        summary = {
            "coherence_delta": 0.3,  # correct (0.7 - 0.4 = 0.3)
            "steps_executed": 99,  # wrong: actual is 3
        }
        result = validator.validate_summary(summary, journey)
        assert result.confidence == pytest.approx(0.5)
        assert not result.valid
