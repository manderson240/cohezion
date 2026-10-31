"""ThermalCheckpointManager called two attributes that do not exist (found 2026-10-31).

* ``predictor.predict_30min_ahead()`` -> the real API is ``predict_temperature_ahead(minutes)``
  returning ``(temp_c, confidence)``.  The AttributeError was swallowed by ``except Exception``,
  so the predictive pause never fired and the only trace was a warning per loop.
* ``Checkpoint.checkpoint_id`` -> not a field.  Resuming from ANY existing checkpoint raised.

Both mocks below are ``spec=``'d on the real class, so a call to a name the class lacks raises
instead of silently succeeding.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.thermal_checkpoint_manager import (
    ThermalCheckpointManager,
    ThermalConfig,
    ThermalState,
)
from cohezion.compound.thermal_trend_predictor import ThermalTrendPredictor


def _manager(tmp_path: Path, forecast: tuple[float, float]) -> ThermalCheckpointManager:
    monitor = MagicMock()
    monitor.get_current_metrics.return_value = MagicMock(
        gpu_temp_current=60.0, cpu_temp_current=55.0
    )
    with patch("cohezion.compound.thermal_checkpoint_manager.get_hardware_monitor") as ghm:
        ghm.return_value = monitor
        mgr = ThermalCheckpointManager(ThermalConfig(checkpoint_dir=tmp_path))
    predictor = MagicMock(spec=ThermalTrendPredictor)
    predictor.predict_temperature_ahead.return_value = forecast
    mgr.predictor = predictor
    return mgr


@pytest.mark.asyncio
async def test_confident_hot_forecast_triggers_predictive_pause(tmp_path: Path) -> None:
    mgr = _manager(tmp_path, forecast=(95.0, 0.9))  # pause_temp default is 90
    pause, reason = await mgr._should_pause()
    assert pause is True
    assert reason.startswith("PREDICTED")
    assert mgr.state is ThermalState.ELEVATED


@pytest.mark.asyncio
async def test_low_confidence_or_cool_forecast_does_not_pause(tmp_path: Path) -> None:
    for forecast in [(95.0, 0.0), (70.0, 0.9)]:  # cold-start answer / confident but cool
        pause, _ = await _manager(tmp_path, forecast)._should_pause()
        assert pause is False, forecast


@pytest.mark.asyncio
async def test_resume_from_existing_checkpoint_does_not_raise(tmp_path: Path) -> None:
    mgr = _manager(tmp_path, forecast=(60.0, 0.0))
    (tmp_path / "job.json").write_text(
        json.dumps(
            {
                "timestamp": time.time(),
                "task_id": "job",
                "phase": "hypothesis_3",
                "progress": {"current": 3},
                "thermal_state": "NORMAL",
                "gpu_temp_at_checkpoint": 60.0,
                "cpu_temp_at_checkpoint": 55.0,
                "hypotheses_completed": 3,
                "total_hypotheses": 4,
                "metadata": {},
            }
        )
    )

    async def _one_more() -> None:
        return None

    async with mgr:  # sets start_time / last_cooldown_time; otherwise a scheduled cooldown fires
        stats = await mgr.execute_with_checkpoints(_one_more, task_id="job", total_hypotheses=4)
    assert stats["completed_hypotheses"] >= 3
    assert stats["error"] is None
