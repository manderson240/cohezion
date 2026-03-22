"""Tests for execution logging hook in ExperienceCollector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.flume.experience_collector import ExperienceCollector


class TestExecutionLogging:
    """Test that compound execution data is appended to JSONL log."""

    def test_log_execution_creates_jsonl_record(self, tmp_path: Path) -> None:
        """log_execution() appends a record with expected fields to JSONL file."""
        collector = ExperienceCollector(
            parquet_dir=tmp_path / "parquet",
            vault_dir=tmp_path / "vault",
            execution_log_dir=tmp_path / "experiences",
        )
        collector.log_execution(
            task_description="Deploy API service",
            operation_type="generate",
            metrics={"phi_score": 0.87, "coherence": 0.72},
            skill_name="api_deploy",
        )

        log_file = tmp_path / "experiences" / "execution_log.jsonl"
        assert log_file.exists(), "execution_log.jsonl should be created"

        record = json.loads(log_file.read_text().strip())
        assert record["task_description"] == "Deploy API service"
        assert record["operation_type"] == "generate"
        assert record["skill_name"] == "api_deploy"
        assert record["metrics"]["phi_score"] == pytest.approx(0.87)

    def test_log_execution_appends_multiple_records(self, tmp_path: Path) -> None:
        """Multiple calls append separate lines."""
        collector = ExperienceCollector(
            parquet_dir=tmp_path / "parquet",
            vault_dir=tmp_path / "vault",
            execution_log_dir=tmp_path / "experiences",
        )
        collector.log_execution("task A", "generate", {"phi_score": 0.5}, "skill_a")
        collector.log_execution("task B", "analyze", {"phi_score": 0.6}, "skill_b")

        log_file = tmp_path / "experiences" / "execution_log.jsonl"
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2
        records = [json.loads(ln) for ln in lines]
        assert records[0]["task_description"] == "task A"
        assert records[1]["task_description"] == "task B"

    def test_log_execution_includes_timestamp(self, tmp_path: Path) -> None:
        """Each record includes an ISO timestamp."""
        collector = ExperienceCollector(
            parquet_dir=tmp_path / "parquet",
            vault_dir=tmp_path / "vault",
            execution_log_dir=tmp_path / "experiences",
        )
        collector.log_execution("timestamped task", "generate", {}, "skill_x")

        log_file = tmp_path / "experiences" / "execution_log.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert "timestamp" in record
        # Should be a valid ISO format string
        from datetime import datetime

        datetime.fromisoformat(record["timestamp"])  # raises if invalid

    def test_log_execution_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Parent directories are created automatically."""
        deep_dir = tmp_path / "a" / "b" / "c"
        collector = ExperienceCollector(
            parquet_dir=tmp_path / "parquet",
            vault_dir=tmp_path / "vault",
            execution_log_dir=deep_dir,
        )
        collector.log_execution("any task", "analyze", {}, "skill_z")
        assert (deep_dir / "execution_log.jsonl").exists()

    def test_default_execution_log_dir(self) -> None:
        """Default execution_log_dir is data/flume/experiences."""
        collector = ExperienceCollector()
        assert collector.execution_log_dir == Path("data/flume/experiences")
