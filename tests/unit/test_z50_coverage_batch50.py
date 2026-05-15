"""Coverage batch Z50: zero_copy_validator, version_traceability_gate, metrics_persistence."""

from __future__ import annotations

import json
import struct
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module 1: core/zero_copy_validator.py
# ---------------------------------------------------------------------------


class TestZeroCopyValidator:
    def _make_validator(self, expected_dim=12):
        from cohezion.core.zero_copy_validator import ZeroCopyValidator

        return ZeroCopyValidator(expected_dim=expected_dim)

    def test_write_returns_shm_buffer(self):
        validator = self._make_validator()
        state = [0.5] * 12
        buf = validator.write(state)
        assert buf.declared_dtype == "float64"
        assert buf.declared_dim == 12
        assert len(buf.data) == 12 * 8

    def test_write_checksum_is_set(self):
        validator = self._make_validator()
        buf = validator.write([0.5] * 12)
        assert len(buf.checksum) > 0

    def test_round_trip_read_write(self):
        validator = self._make_validator()
        state = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.0, -0.1]
        buf = validator.write(state)
        result = validator.validate_and_read(buf)
        assert len(result) == 12
        assert all(abs(r - s) < 1e-10 for r, s in zip(result, state))

    def test_read_wrong_dtype_raises(self):
        from cohezion.core.zero_copy_validator import SHMBuffer, TypeMismatchError

        validator = self._make_validator()
        bad_buf = SHMBuffer(data=b"\x00" * 96, declared_dtype="float32", declared_dim=12)
        with pytest.raises(TypeMismatchError):
            validator.validate_and_read(bad_buf)

    def test_read_wrong_size_raises(self):
        from cohezion.core.zero_copy_validator import SHMBuffer, TypeMismatchError

        validator = self._make_validator()
        # declared_dim=12 means 12*8=96 bytes expected but we only provide 48
        bad_buf = SHMBuffer(data=b"\x00" * 48, declared_dtype="float64", declared_dim=12)
        with pytest.raises(TypeMismatchError):
            validator.validate_and_read(bad_buf)

    def test_checksum_mismatch_uses_snapshot(self):
        from cohezion.core.zero_copy_validator import SHMBuffer

        validator = self._make_validator()
        # First write a good buffer to establish snapshot
        good_state = [0.5] * 12
        good_buf = validator.write(good_state)
        validator.validate_and_read(good_buf)  # sets snapshot

        # Now read a buffer with wrong checksum
        data = struct.pack("12d", *([0.9] * 12))
        corrupt_buf = SHMBuffer(data=data, declared_dtype="float64", declared_dim=12, checksum="bad_checksum")
        result = validator.validate_and_read(corrupt_buf)
        # Falls back to snapshot (the good state)
        assert all(abs(r - 0.5) < 1e-10 for r in result)
        assert len(validator.corruption_events()) == 1

    def test_checksum_mismatch_no_snapshot_raises(self):
        from cohezion.core.zero_copy_validator import ChecksumValidationError, SHMBuffer

        validator = self._make_validator()
        data = struct.pack("12d", *([0.5] * 12))
        corrupt = SHMBuffer(data=data, declared_dtype="float64", declared_dim=12, checksum="wrong")
        with pytest.raises(ChecksumValidationError):
            validator.validate_and_read(corrupt)

    def test_shm_buffer_compute_checksum(self):
        from cohezion.core.zero_copy_validator import SHMBuffer

        buf = SHMBuffer(data=b"hello", declared_dtype="float64")
        checksum = buf.compute_checksum()
        assert len(checksum) == 64  # SHA-256 hex

    def test_shm_buffer_dtype_alias(self):
        from cohezion.core.zero_copy_validator import SHMBuffer

        buf = SHMBuffer(data=b"\x00" * 96, dtype="float64", declared_dim=12)
        assert buf.declared_dtype == "float64"


# ---------------------------------------------------------------------------
# Module 2: registry/version_traceability_gate.py
# ---------------------------------------------------------------------------


class TestVersionTraceabilityGate:
    def _make_gate(self):
        from cohezion.registry.version_traceability_gate import VersionTraceabilityGate

        return VersionTraceabilityGate()

    def test_version_contract_dataclass(self):
        from cohezion.registry.version_traceability_gate import VersionContract

        vc = VersionContract(package="pydantic", version_spec=">=2.0", story_id="S1", epic_id="E1")
        assert vc.package == "pydantic"
        d = vc.to_dict()
        assert d["package"] == "pydantic"

    def _register(self, gate, package, version_spec, story_id, epic_id):
        from cohezion.registry.version_traceability_gate import VersionContract

        gate.register_contract(
            VersionContract(package=package, version_spec=version_spec, story_id=story_id, epic_id=epic_id)
        )

    def test_register_contract(self):
        gate = self._make_gate()
        self._register(gate, "numpy", ">=1.24", "S1", "E1")
        contracts = gate.all_contracts()
        assert len(contracts) == 1
        assert contracts[0]["package"] == "numpy"

    def test_check_epic_gate_passes(self):
        gate = self._make_gate()
        self._register(gate, "pkg1", ">=1.0", "S1", "E1")
        self._register(gate, "pkg2", ">=2.0", "S2", "E1")
        result = gate.check_epic_gate("E1", expected_stories=["S1", "S2"])
        assert result.blocked is False
        assert result.missing_contracts == []

    def test_check_epic_gate_blocked(self):
        gate = self._make_gate()
        self._register(gate, "pkg1", ">=1.0", "S1", "E1")
        result = gate.check_epic_gate("E1", expected_stories=["S1", "S2"])
        assert result.blocked is True
        assert "S2" in result.missing_contracts
        assert len(result.remediation_steps) > 0

    def test_generate_release_report(self):
        gate = self._make_gate()
        self._register(gate, "numpy", ">=1.24", "S1", "E1")
        report = gate.generate_release_report("1.2.0", story_ids=["S1"])
        assert report.release_version == "1.2.0"
        assert len(report.version_changes) == 1

    def test_generate_release_report_breaking_change(self):
        gate = self._make_gate()
        self._register(gate, "numpy", "!>=2.0", "S1", "E1")
        report = gate.generate_release_report("2.0.0", story_ids=["S1"])
        assert len(report.breaking_changes) > 0

    def test_incident_response_query(self):
        gate = self._make_gate()
        self._register(gate, "requests", ">=2.28", "S1", "E1")
        result = gate.incident_response_query("requests", "2.28")
        assert "S1" in result["affected_stories"]
        assert "E1" in result["affected_epics"]
        assert result["query_duration_s"] >= 0

    def test_incident_response_no_match(self):
        gate = self._make_gate()
        result = gate.incident_response_query("unknown_pkg", "1.0")
        assert result["affected_stories"] == []

    def test_epic_completion_gate_to_dict(self):
        from cohezion.registry.version_traceability_gate import EpicCompletionGate

        eg = EpicCompletionGate(epic_id="E1", blocked=False, missing_contracts=[], remediation_steps=[])
        d = eg.to_dict()
        assert d["epic_id"] == "E1"
        assert d["blocked"] is False


# ---------------------------------------------------------------------------
# Module 3: compound/metrics_persistence.py
# ---------------------------------------------------------------------------


class TestMetricsPersistence:
    def _make_persistence(self, tmp_path):
        from cohezion.compound.metrics_persistence import MetricsPersistence

        return MetricsPersistence(metrics_dir=tmp_path)

    def test_save_snapshot_creates_file(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        mock_collector = MagicMock()
        mock_collector.to_snapshot.return_value = {"total_executions": 5, "total_tokens": 1000}
        path_str = persistence.save_snapshot(mock_collector)
        assert Path(path_str).exists()

    def test_save_snapshot_content(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        mock_collector = MagicMock()
        mock_collector.to_snapshot.return_value = {"total_executions": 10}
        path_str = persistence.save_snapshot(mock_collector)
        content = json.loads(Path(path_str).read_text())
        assert content["total_executions"] == 10
        assert "saved_at" in content

    def test_load_latest_snapshot_returns_dict(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        mock_collector = MagicMock()
        mock_collector.to_snapshot.return_value = {"key": "value"}
        persistence.save_snapshot(mock_collector)
        loaded = persistence.load_latest_snapshot()
        assert loaded["key"] == "value"

    def test_load_latest_snapshot_no_files_returns_none(self, tmp_path):
        persistence = self._make_persistence(tmp_path / "empty_dir")
        result = persistence.load_latest_snapshot()
        assert result is None

    def test_save_compound_scores(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        scores = [
            {"skill_name": "code_review", "compound_score_delta": 0.05, "timestamp": time.time()},
            {"skill_name": "test_gen", "compound_score_delta": 0.03, "timestamp": time.time()},
        ]
        count = persistence.save_compound_scores(scores)
        assert count == 2

    def test_load_compound_score_history(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        scores = [
            {"skill_name": "s1", "compound_score_delta": 0.1, "timestamp": 1000.0},
            {"skill_name": "s2", "compound_score_delta": 0.2, "timestamp": 2000.0},
        ]
        persistence.save_compound_scores(scores)
        history = persistence.load_compound_score_history()
        assert len(history) == 2
        assert history[0]["timestamp"] == pytest.approx(2000.0)  # most recent first

    def test_load_compound_score_history_empty(self, tmp_path):
        persistence = self._make_persistence(tmp_path)
        history = persistence.load_compound_score_history()
        assert history == []
