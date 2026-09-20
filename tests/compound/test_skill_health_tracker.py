"""Tests for SkillHealthTracker and its integration with CompoundExecutor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.skill_health_tracker import SkillHealthRecord, SkillHealthTracker


def _a_registry_skill() -> str:
    """A real registry key: Step 7.4 records health only for registry skills."""
    from cohezion.registry.skill_registry import load_registry

    CompoundExecutor._registry_keys_cache = None
    return next(iter(load_registry()))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def storage_path(tmp_path: Path) -> Path:
    return tmp_path / "skill_health.json"


@pytest.fixture
def tracker(storage_path: Path) -> SkillHealthTracker:
    return SkillHealthTracker(storage_path=storage_path)


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    client = MagicMock()
    client.vault_find_relevant_context.return_value = []
    client.vault_log_experiment.return_value = "experiments/test.md"
    client.vault_log_decision.return_value = "decisions/test.md"
    client.vault_extract_pattern.return_value = "patterns/test.md"
    client.vault_edit.return_value = "success"
    return client


# ---------------------------------------------------------------------------
# SkillHealthRecord unit tests
# ---------------------------------------------------------------------------


class TestSkillHealthRecord:
    def test_success_rate_zero_on_no_invocations(self) -> None:
        record = SkillHealthRecord(skill_name="test")
        assert record.success_rate == 0.0

    def test_success_rate_computation(self) -> None:
        record = SkillHealthRecord(
            skill_name="test",
            total_invocations=10,
            successful_invocations=7,
        )
        assert record.success_rate == pytest.approx(0.7)

    def test_avg_tokens_per_use(self) -> None:
        record = SkillHealthRecord(
            skill_name="test",
            total_invocations=4,
            total_tokens_used=800,
        )
        assert record.avg_tokens_per_use == pytest.approx(200.0)

    def test_avg_tokens_zero_on_no_invocations(self) -> None:
        record = SkillHealthRecord(skill_name="test")
        assert record.avg_tokens_per_use == 0.0

    def test_avg_quality_score(self) -> None:
        record = SkillHealthRecord(
            skill_name="test",
            successful_invocations=5,
            total_quality_score=4.0,
        )
        assert record.avg_quality_score == pytest.approx(0.8)

    def test_avg_quality_zero_on_no_successes(self) -> None:
        record = SkillHealthRecord(skill_name="test", total_invocations=2, failed_invocations=2)
        assert record.avg_quality_score == 0.0

    def test_health_score_zero_on_no_invocations(self) -> None:
        record = SkillHealthRecord(skill_name="test")
        assert record.health_score == 0.0

    def test_health_score_with_recent_use(self) -> None:
        # Used just now → recency ≈ 1.0, health ≈ success_rate
        now = datetime.now(UTC).isoformat()
        record = SkillHealthRecord(
            skill_name="test",
            total_invocations=10,
            successful_invocations=8,
            last_used=now,
        )
        assert record.health_score == pytest.approx(0.8, abs=0.01)

    def test_health_score_with_recency_decay(self) -> None:
        # At the 90-day half-life: recency = 0.5, health = success_rate * 0.5
        old_date = (datetime.now(UTC) - timedelta(days=90)).isoformat()
        record = SkillHealthRecord(
            skill_name="test",
            total_invocations=10,
            successful_invocations=10,
            last_used=old_date,
        )
        # success_rate=1.0, recency≈0.5 at 90d half-life
        assert record.health_score == pytest.approx(0.5, abs=0.05)


# ---------------------------------------------------------------------------
# SkillHealthTracker unit tests
# ---------------------------------------------------------------------------


class TestSkillHealthTrackerRecordUsage:
    def test_record_usage_creates_new_record(self, tracker: SkillHealthTracker) -> None:
        tracker.record_usage("MY_SKILL", success=True)
        record = tracker.get_health("MY_SKILL")
        assert record is not None
        assert record.skill_name == "MY_SKILL"

    def test_record_usage_increments_counts_on_success(self, tracker: SkillHealthTracker) -> None:
        tracker.record_usage("SKILL_A", success=True, tokens_used=100, quality_score=0.9)
        tracker.record_usage("SKILL_A", success=True, tokens_used=200, quality_score=0.8)
        record = tracker.get_health("SKILL_A")
        assert record is not None
        assert record.total_invocations == 2
        assert record.successful_invocations == 2
        assert record.failed_invocations == 0
        assert record.total_tokens_used == 300
        assert record.total_quality_score == pytest.approx(1.7)

    def test_record_usage_increments_counts_on_failure(self, tracker: SkillHealthTracker) -> None:
        tracker.record_usage("SKILL_B", success=False)
        record = tracker.get_health("SKILL_B")
        assert record is not None
        assert record.total_invocations == 1
        assert record.failed_invocations == 1
        assert record.successful_invocations == 0

    def test_record_usage_sets_last_used(self, tracker: SkillHealthTracker) -> None:
        before = datetime.now(UTC)
        tracker.record_usage("SKILL_C", success=True)
        record = tracker.get_health("SKILL_C")
        assert record is not None
        last = datetime.fromisoformat(record.last_used)
        assert last >= before


class TestSkillHealthTrackerQueries:
    def test_get_health_returns_none_for_unknown(self, tracker: SkillHealthTracker) -> None:
        assert tracker.get_health("UNKNOWN") is None

    def test_get_all_health_sorted_by_score(self, tracker: SkillHealthTracker) -> None:
        # Create two records with different success rates (recent use → recency≈1)
        now = datetime.now(UTC).isoformat()
        tracker._records["HIGH"] = SkillHealthRecord(
            skill_name="HIGH",
            total_invocations=10,
            successful_invocations=9,
            last_used=now,
        )
        tracker._records["LOW"] = SkillHealthRecord(
            skill_name="LOW",
            total_invocations=10,
            successful_invocations=3,
            last_used=now,
        )
        all_health = tracker.get_all_health()
        assert all_health[0].skill_name == "HIGH"
        assert all_health[1].skill_name == "LOW"

    def test_get_stale_skills(self, tracker: SkillHealthTracker) -> None:
        old = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        recent = datetime.now(UTC).isoformat()
        tracker._records["STALE"] = SkillHealthRecord(
            skill_name="STALE", total_invocations=1, last_used=old
        )
        tracker._records["FRESH"] = SkillHealthRecord(
            skill_name="FRESH", total_invocations=1, last_used=recent
        )
        stale = tracker.get_stale_skills(days=30)
        assert "STALE" in stale
        assert "FRESH" not in stale

    def test_get_stale_skills_includes_never_used(self, tracker: SkillHealthTracker) -> None:
        tracker._records["NEVER"] = SkillHealthRecord(skill_name="NEVER", total_invocations=1)
        stale = tracker.get_stale_skills(days=30)
        assert "NEVER" in stale

    def test_get_unhealthy_skills(self, tracker: SkillHealthTracker) -> None:
        now = datetime.now(UTC).isoformat()
        tracker._records["BAD"] = SkillHealthRecord(
            skill_name="BAD",
            total_invocations=10,
            successful_invocations=1,
            last_used=now,
        )
        tracker._records["GOOD"] = SkillHealthRecord(
            skill_name="GOOD",
            total_invocations=10,
            successful_invocations=9,
            last_used=now,
        )
        unhealthy = tracker.get_unhealthy_skills(threshold=0.3)
        assert "BAD" in unhealthy
        assert "GOOD" not in unhealthy

    def test_get_unhealthy_skills_excludes_zero_invocations(
        self, tracker: SkillHealthTracker
    ) -> None:
        tracker._records["UNTRACKED"] = SkillHealthRecord(skill_name="UNTRACKED")
        unhealthy = tracker.get_unhealthy_skills(threshold=0.3)
        assert "UNTRACKED" not in unhealthy


class TestSkillHealthTrackerPersistence:
    def test_persistence_save_and_load(self, tmp_path: Path) -> None:
        storage = tmp_path / "health.json"
        tracker1 = SkillHealthTracker(storage_path=storage)
        tracker1.record_usage("PERSIST_SKILL", success=True, tokens_used=500, quality_score=0.85)

        # Load fresh instance from same file
        tracker2 = SkillHealthTracker(storage_path=storage)
        record = tracker2.get_health("PERSIST_SKILL")
        assert record is not None
        assert record.total_invocations == 1
        assert record.successful_invocations == 1
        assert record.total_tokens_used == 500
        assert record.total_quality_score == pytest.approx(0.85)

    def test_persistence_creates_parent_directory(self, tmp_path: Path) -> None:
        storage = tmp_path / "nested" / "dir" / "health.json"
        tracker = SkillHealthTracker(storage_path=storage)
        tracker.record_usage("SKILL", success=True)
        assert storage.exists()

    def test_load_empty_when_file_absent(self, tmp_path: Path) -> None:
        storage = tmp_path / "nonexistent.json"
        tracker = SkillHealthTracker(storage_path=storage)
        assert tracker.get_all_health() == []


# ---------------------------------------------------------------------------
# Executor integration tests
# ---------------------------------------------------------------------------


class TestExecutorSkillHealthIntegration:
    def test_nonblocking_on_tracker_failure(self, mock_mcp_client: MagicMock) -> None:
        """Tracker errors must not crash executor execution."""
        broken_tracker = MagicMock()
        broken_tracker.record_usage.side_effect = RuntimeError("storage full")

        executor = CompoundExecutor(mock_mcp_client, skill_health_tracker=broken_tracker)

        def dummy_task(guidance: dict) -> tuple[str, dict]:
            return "output", {}

        result = executor.execute_task(
            task_description="test",
            skill_name="MY_SKILL",
            operation_type="generate",
            execute_fn=dummy_task,
        )
        assert result.success is True

    def test_tracker_called_on_successful_execution(
        self, mock_mcp_client: MagicMock, storage_path: Path
    ) -> None:
        """Tracker.record_usage is called after successful execution."""
        tracker = SkillHealthTracker(storage_path=storage_path)
        executor = CompoundExecutor(mock_mcp_client, skill_health_tracker=tracker)

        def dummy_task(guidance: dict) -> tuple[str, dict]:
            return "output", {}

        # Step 7.4 records health only for REGISTRY skills (lane labels polluted the store
        # and zeroed the capability matrix's skill axis) — premise the test on a real one.
        skill = _a_registry_skill()
        executor.execute_task(
            task_description="test",
            skill_name=skill,
            operation_type="generate",
            execute_fn=dummy_task,
        )

        record = tracker.get_health(skill)
        assert record is not None
        assert record.total_invocations == 1
        assert record.successful_invocations == 1

    def test_tracker_records_failure(self, mock_mcp_client: MagicMock, storage_path: Path) -> None:
        """Tracker.record_usage is called even on failed execution."""
        tracker = SkillHealthTracker(storage_path=storage_path)
        executor = CompoundExecutor(mock_mcp_client, skill_health_tracker=tracker)

        def failing_task(guidance: dict) -> tuple[str, dict]:
            raise ValueError("boom")

        skill = _a_registry_skill()
        executor.execute_task(
            task_description="test",
            skill_name=skill,
            operation_type="generate",
            execute_fn=failing_task,
        )

        record = tracker.get_health(skill)
        assert record is not None
        assert record.total_invocations == 1
        assert record.failed_invocations == 1
        assert record.successful_invocations == 0

    def test_auto_creates_tracker_by_default(self, mock_mcp_client: MagicMock) -> None:
        """Executor auto-creates a SkillHealthTracker when none provided."""
        executor = CompoundExecutor(mock_mcp_client)
        assert executor._skill_health_tracker is not None
        assert isinstance(executor._skill_health_tracker, SkillHealthTracker)

        def dummy_task(guidance: dict) -> tuple[str, dict]:
            return "output", {}

        result = executor.execute_task(
            task_description="test",
            skill_name="SKILL",
            operation_type="generate",
            execute_fn=dummy_task,
        )
        assert result.success is True


class TestExecutorRecordsOnlyRegistrySkills:
    """Step 7.4 CONSUMPTION invariant. Measured 2026-09-20: the health store held 30 records,
    0 of which canonicalised to a registry skill (29 test fixtures from before COHEZION_STATE_DIR
    isolation + the actioner daemon's lane label 'research-actioner', 1,175 invocations). The
    capability matrix's skill axis therefore read 0. The executor must not write lane labels
    into the skill store; a real registry skill must still be recorded."""

    def _executor(self):
        from unittest.mock import MagicMock

        from cohezion.compound.executor import CompoundExecutor

        tracker = MagicMock()
        ex = CompoundExecutor(MagicMock(), skill_health_tracker=tracker)
        CompoundExecutor._registry_keys_cache = None
        return ex, tracker

    def test_lane_label_is_not_recorded(self):
        ex, _ = self._executor()
        assert ex._is_registry_skill("research-actioner") is False

    def test_registry_skill_is_recorded(self):
        ex, _ = self._executor()
        assert ex._is_registry_skill(_a_registry_skill()) is True

    def test_empty_name_is_not_recorded(self):
        ex, _ = self._executor()
        assert ex._is_registry_skill("") is False

    def test_execute_task_skips_record_usage_for_a_lane_label(self):
        """CONSUMPTION: the gate must sit on the execute_task path, not only exist as a method.
        Neutralising the Step 7.4 guard (recording unconditionally) turns this red."""
        ex, tracker = self._executor()
        ex.execute_task(
            task_description="t",
            skill_name="research-actioner",
            operation_type="generate",
            execute_fn=lambda guidance: ("out", {}),
        )
        tracker.record_usage.assert_not_called()

    def test_execute_task_records_usage_for_a_registry_skill(self):
        ex, tracker = self._executor()
        ex.execute_task(
            task_description="t",
            skill_name=_a_registry_skill(),
            operation_type="generate",
            execute_fn=lambda guidance: ("out", {}),
        )
        assert tracker.record_usage.call_count == 1

    def test_registry_unreadable_fails_open(self, monkeypatch):
        import cohezion.registry.skill_registry as reg

        ex, _ = self._executor()
        monkeypatch.setattr(reg, "load_registry", lambda: (_ for _ in ()).throw(OSError("boom")))
        assert ex._is_registry_skill("anything") is True
