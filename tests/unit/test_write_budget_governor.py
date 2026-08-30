"""Unit tests for Write Budget Governor."""

from __future__ import annotations

from pathlib import Path

from cohezion.core.resource_management.write_budget_governor import WriteBudgetGovernor


def test_write_budget_enforcement(tmp_path: Path) -> None:
    # Set a tiny 100-byte budget
    gov = WriteBudgetGovernor(max_bytes_per_hour=100, max_bytes_per_day=200)

    target = tmp_path / "test_log.txt"

    # Write 60 bytes (should succeed)
    res1 = gov.safe_write_text(target, "A" * 60)
    assert res1["status"] == "written"
    assert res1["bytes_written"] == 60

    # Attempt to write 50 bytes (exceeds 100-byte hourly budget -> should throttle)
    res2 = gov.safe_write_text(target, "B" * 50)
    assert res2["status"] == "throttled"
    assert res2["reason"] == "write_budget_exceeded"


def test_log_rotation_on_size_limit(tmp_path: Path) -> None:
    # Set max single file to 50 bytes
    gov = WriteBudgetGovernor(max_single_file_mb=0.00005)  # ~52 bytes

    target = tmp_path / "app.log"

    # Write 40 bytes
    res1 = gov.safe_write_text(target, "X" * 40, append=True)
    assert res1["status"] == "written"
    assert target.stat().st_size == 40

    # Append 30 bytes (exceeds 50 bytes -> triggers rotation to app.log.1)
    res2 = gov.safe_write_text(target, "Y" * 30, append=True)
    assert res2["status"] == "written"

    rotated = tmp_path / "app.log.1"
    assert rotated.exists()
    assert rotated.stat().st_size == 40
    assert target.stat().st_size == 30
