"""Tests for AutoresearchDriver — K-Search UCB1 loop with SurrealDB persistence."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.research.autoresearch_driver import (
    AutoresearchDriver,
    ExperimentOutcome,
    _extract_metric,
    _load_tree,
    _ucb1_select,
    _update_tree,
)


# ---------------------------------------------------------------------------
# _extract_metric — pure function, no mocking needed
# ---------------------------------------------------------------------------


class TestExtractMetric:
    def test_colon_format(self):
        assert _extract_metric("val_loss: 0.123\n", "val_loss") == pytest.approx(0.123)

    def test_equals_format(self):
        assert _extract_metric("total_loss=0.456\n", "total_loss") == pytest.approx(0.456)

    def test_scientific_notation(self):
        assert _extract_metric("val_loss: 1.23e-4\n", "val_loss") == pytest.approx(1.23e-4)

    def test_embedded_in_noise(self):
        stdout = "epoch 10/10\ntotal_loss: 0.789\nother_stat: 999\n"
        assert _extract_metric(stdout, "total_loss") == pytest.approx(0.789)

    def test_returns_none_when_absent(self):
        assert _extract_metric("epoch 5 complete\n", "val_loss") is None

    def test_case_insensitive(self):
        assert _extract_metric("VAL_LOSS: 0.5\n", "val_loss") == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# AutoresearchDriver — regression / improvement classification
# ---------------------------------------------------------------------------


class TestExperimentClassification:
    """Tests for status classification logic in run_experiment."""

    def _make_driver(self) -> AutoresearchDriver:
        return AutoresearchDriver(
            target="jepa",
            budget_seconds=10,
            hypotheses=["learning_rate=1e-4"],
        )

    @pytest.mark.asyncio
    async def test_first_result_is_improvement(self):
        """First experiment always sets the baseline → 'improvement'."""
        driver = self._make_driver()
        fake_proc = MagicMock(stdout="total_loss: 0.5\n", stderr="")

        with (
            patch("subprocess.run", return_value=fake_proc),
            patch(
                "cohezion.research.autoresearch_driver._persist_to_surreal",
                new_callable=AsyncMock,
            ),
        ):
            outcome = await driver.run_experiment("learning_rate=1e-4")

        assert outcome.status == "improvement"
        assert outcome.metric_value == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_better_metric_is_improvement(self):
        """Loss strictly lower than baseline → 'improvement'."""
        driver = self._make_driver()
        driver._baseline = 0.5  # pre-set baseline

        fake_proc = MagicMock(stdout="total_loss: 0.400\n", stderr="")  # 20% better

        with (
            patch("subprocess.run", return_value=fake_proc),
            patch(
                "cohezion.research.autoresearch_driver._persist_to_surreal",
                new_callable=AsyncMock,
            ),
        ):
            outcome = await driver.run_experiment("learning_rate=1e-4")

        assert outcome.status == "improvement"
        assert driver._baseline == pytest.approx(0.400)

    @pytest.mark.asyncio
    async def test_worse_metric_is_regression(self):
        """Loss worse than baseline by > 0.5% → 'regression'."""
        driver = self._make_driver()
        driver._baseline = 0.5

        fake_proc = MagicMock(stdout="total_loss: 0.510\n", stderr="")  # 2% worse

        with (
            patch("subprocess.run", return_value=fake_proc),
            patch(
                "cohezion.research.autoresearch_driver._persist_to_surreal",
                new_callable=AsyncMock,
            ),
        ):
            outcome = await driver.run_experiment("learning_rate=1e-4")

        assert outcome.status == "regression"
        assert driver._baseline == pytest.approx(0.5)  # baseline unchanged

    @pytest.mark.asyncio
    async def test_missing_metric_is_error(self):
        """No metric in stdout → status='error', metric_value=nan."""
        driver = self._make_driver()
        fake_proc = MagicMock(stdout="Training started\n", stderr="")

        with (
            patch("subprocess.run", return_value=fake_proc),
            patch(
                "cohezion.research.autoresearch_driver._persist_to_surreal",
                new_callable=AsyncMock,
            ),
        ):
            outcome = await driver.run_experiment("learning_rate=1e-4")

        assert outcome.status == "error"
        assert math.isnan(outcome.metric_value)


# ---------------------------------------------------------------------------
# SurrealDB persistence — verify the async path is called
# ---------------------------------------------------------------------------


class TestSurrealPersistence:
    @pytest.mark.asyncio
    async def test_persist_called_after_experiment(self):
        """_persist_to_surreal is called once per run_experiment invocation."""
        driver = AutoresearchDriver(
            target="flume_vae",
            budget_seconds=10,
            hypotheses=["batch_size=32"],
        )
        fake_proc = MagicMock(stdout="val_loss: 0.25\n", stderr="")

        with (
            patch("subprocess.run", return_value=fake_proc),
            patch(
                "cohezion.research.autoresearch_driver._persist_to_surreal",
                new_callable=AsyncMock,
            ) as mock_persist,
        ):
            await driver.run_experiment("batch_size=32")

        mock_persist.assert_called_once()
        outcome: ExperimentOutcome = mock_persist.call_args[0][0]
        assert outcome.target == "flume_vae"
        assert outcome.metric_name == "val_loss"
        assert outcome.metric_value == pytest.approx(0.25)
        assert outcome.run_id.startswith("ar_")


# ---------------------------------------------------------------------------
# K-Search tree — UCB1 exploration + update mechanics
# ---------------------------------------------------------------------------


class TestKSearchTree:
    def test_unexplored_node_selected_first(self, tmp_path, monkeypatch):
        """UCB1 must always select an unexplored node before any explored node."""
        monkeypatch.setattr("cohezion.research.autoresearch_driver.KSEARCH_DIR", tmp_path)
        hypotheses = ["lr=1e-4", "lr=3e-4", "lr=1e-3"]
        tree = _load_tree("test_target", hypotheses)

        # Mark first two as already explored
        _update_tree(tree, "lr=1e-4", reward=0.8)
        _update_tree(tree, "lr=3e-4", reward=0.7)

        selected = _ucb1_select(tree)
        assert selected == "lr=1e-3"  # only unexplored one

    def test_update_increments_trials(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cohezion.research.autoresearch_driver.KSEARCH_DIR", tmp_path)
        tree = _load_tree("test_target2", ["lr=1e-4"])
        _update_tree(tree, "lr=1e-4", reward=0.6)

        node = tree["nodes"]["lr=1e-4"]
        assert node["trials"] == 1
        assert node["metric_values"] == [0.6]
        assert tree["total_trials"] == 1
