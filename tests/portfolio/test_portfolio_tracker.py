"""Tests for the Cohezion Portfolio Tracker module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cohezion.portfolio.models import PortfolioProject, PortfolioSummary
from cohezion.portfolio.tracker import PortfolioTracker


@pytest.fixture()
def tmp_tracker(tmp_path: Path) -> PortfolioTracker:
    store = tmp_path / "portfolio_test.json"
    return PortfolioTracker(store_path=store)


@pytest.fixture()
def sample_project() -> PortfolioProject:
    return PortfolioProject(
        id="test-comp",
        name="Test Competition",
        competition="test-comp-slug",
        deadline=datetime(2026, 12, 31, tzinfo=UTC),
        prize=10_000,
        status="active",
    )


class TestPortfolioTracker:
    def test_upsert_and_get(self, tmp_tracker: PortfolioTracker, sample_project: PortfolioProject):
        result = tmp_tracker.upsert(sample_project)
        assert result.id == "test-comp"

        fetched = tmp_tracker.get("test-comp")
        assert fetched is not None
        assert fetched.name == "Test Competition"

    def test_get_missing_returns_none(self, tmp_tracker: PortfolioTracker):
        assert tmp_tracker.get("nonexistent") is None

    def test_list_sorted_by_deadline(self, tmp_tracker: PortfolioTracker):
        tmp_tracker.upsert(PortfolioProject(
            id="late", name="Late", deadline=datetime(2027, 1, 1, tzinfo=UTC), status="active"
        ))
        tmp_tracker.upsert(PortfolioProject(
            id="early", name="Early", deadline=datetime(2026, 7, 1, tzinfo=UTC), status="active"
        ))
        tmp_tracker.upsert(PortfolioProject(
            id="no-deadline", name="NoDL", deadline=None, status="active"
        ))
        projects = tmp_tracker.list_all()
        ids = [p.id for p in projects]
        assert ids.index("early") < ids.index("late")
        assert ids[-1] == "no-deadline"  # None deadline goes last

    def test_patch_updates_fields(self, tmp_tracker: PortfolioTracker, sample_project: PortfolioProject):
        tmp_tracker.upsert(sample_project)
        updated = tmp_tracker.patch("test-comp", status="submitted", score=0.92)
        assert updated is not None
        assert updated.status == "submitted"
        assert updated.score == 0.92

    def test_patch_missing_returns_none(self, tmp_tracker: PortfolioTracker):
        assert tmp_tracker.patch("ghost", status="active") is None

    def test_add_note(self, tmp_tracker: PortfolioTracker, sample_project: PortfolioProject):
        tmp_tracker.upsert(sample_project)
        result = tmp_tracker.add_note("test-comp", "Kernel finished!")
        assert result is not None
        assert len(result.notes) == 1
        assert "Kernel finished!" in result.notes[0]
        assert "[" in result.notes[0]  # timestamp present

    def test_update_from_session(self, tmp_tracker: PortfolioTracker, sample_project: PortfolioProject):
        tmp_tracker.upsert(sample_project)
        result = tmp_tracker.update_from_session(
            "test-comp",
            session_id="sess-abc",
            status="submitted",
            score=0.87,
            score_label="0.87 public",
            kernel="manderson240/test-kernel",
            note="Submitted v1",
        )
        assert result is not None
        assert result.status == "submitted"
        assert result.score == 0.87
        assert result.kernel == "manderson240/test-kernel"
        assert result.last_session == "sess-abc"
        assert any("Submitted v1" in n for n in result.notes)

    def test_persistence_roundtrip(self, tmp_path: Path, sample_project: PortfolioProject):
        store = tmp_path / "portfolio.json"
        tracker1 = PortfolioTracker(store_path=store)
        tracker1.upsert(sample_project)

        # Load in fresh tracker instance
        tracker2 = PortfolioTracker(store_path=store)
        loaded = tracker2.get("test-comp")
        assert loaded is not None
        assert loaded.name == "Test Competition"
        assert loaded.prize == 10_000

    def test_summaries_returns_summary_objects(self, tmp_tracker: PortfolioTracker, sample_project: PortfolioProject):
        tmp_tracker.upsert(sample_project)
        summaries = tmp_tracker.summaries()
        assert len(summaries) == 1
        s = summaries[0]
        assert isinstance(s, PortfolioSummary)
        assert s.id == "test-comp"
        assert s.days_to_deadline is not None
        assert s.is_urgent is False  # deadline 2026-12-31, not within 7 days


class TestPortfolioProject:
    def test_days_to_deadline_future(self):
        p = PortfolioProject(
            id="x", name="x",
            deadline=datetime(2099, 1, 1, tzinfo=UTC),
            status="active",
        )
        days = p.days_to_deadline()
        assert days is not None and days > 1000

    def test_days_to_deadline_none(self):
        p = PortfolioProject(id="x", name="x", status="active")
        assert p.days_to_deadline() is None

    def test_is_urgent_within_7_days(self):
        from datetime import timedelta

        soon = datetime.now(UTC) + timedelta(days=3)
        p = PortfolioProject(id="x", name="x", deadline=soon, status="active")
        assert p.is_urgent() is True

    def test_is_urgent_far_future(self):
        p = PortfolioProject(
            id="x", name="x",
            deadline=datetime(2099, 1, 1, tzinfo=UTC),
            status="active",
        )
        assert p.is_urgent() is False
