"""Cosmic Fire is LIT by the executor, once, and its ignition is a checked durable record.

Measured 2026-09-20: the only importer of CosmicFireProtocol was a CLI demo; no production
path called ignite(); the five cascade action names had zero executors; the promised
``cosmic_fire_events`` table did not exist. P3 (the cascade returns 5 ordered names) was
green throughout -- a pure protocol nobody lit. These are CONSUMPTION tests: neutralising
the Step 7.5a call turns the first two red.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.cosmic_fire_protocol import (
    CosmicFireEvent,
    CosmicFireProtocol,
    persist_event,
)
from cohezion.compound.executor import CompoundExecutor
from cohezion.storage.surreal_http import SurrealQLError


def _executor(protocol: CosmicFireProtocol) -> CompoundExecutor:
    return CompoundExecutor(
        MagicMock(), cosmic_fire=protocol, skill_health_tracker=MagicMock(), journey_tracker=None
    )


def _run(ex: CompoundExecutor, quality: float | None):
    extra = {} if quality is None else {"quality_score": quality}
    return ex.execute_task(
        task_description="t",
        skill_name="s",
        operation_type="generate",
        execute_fn=lambda guidance: ("out", dict(extra)),
    )


class TestExecutorLightsTheFire:
    def test_DISCRIMINATING_first_band_entry_ignites_and_persists(self):
        persist = MagicMock()
        p = CosmicFireProtocol(notify_telegram=False, persist_fn=persist)
        result = _run(_executor(p), 0.61)
        assert p.ignition_count == 1
        assert result.metrics["cosmic_fire"]["ignited"] is True
        assert result.metrics["cosmic_fire"]["coherence"] == pytest.approx(0.61)
        assert result.metrics["cosmic_fire"]["cascade"][0] == "enter_bbq_low_slow_mode"
        persist.assert_called_once()
        assert isinstance(persist.call_args.args[0], CosmicFireEvent)

    def test_below_band_does_not_ignite(self):
        persist = MagicMock()
        p = CosmicFireProtocol(notify_telegram=False, persist_fn=persist)
        result = _run(_executor(p), 0.30)
        assert p.ignition_count == 0
        assert "cosmic_fire" not in result.metrics
        persist.assert_not_called()

    def test_no_quality_score_is_no_decision(self):
        p = CosmicFireProtocol(notify_telegram=False, persist_fn=MagicMock())
        _run(_executor(p), None)
        assert p.ignition_count == 0

    def test_ignites_once_per_process_irreversible(self):
        persist = MagicMock()
        p = CosmicFireProtocol(notify_telegram=False, persist_fn=persist)
        ex = _executor(p)
        _run(ex, 0.7)
        second = _run(ex, 0.9)
        assert p.ignition_count == 1
        assert "cosmic_fire" not in second.metrics
        persist.assert_called_once()

    def test_executor_autocreates_a_protocol(self):
        ex = CompoundExecutor(MagicMock(), skill_health_tracker=MagicMock(), journey_tracker=None)
        assert isinstance(ex._cosmic_fire, CosmicFireProtocol)


class TestPersistIsChecked:
    """Action 4 reads the SurrealDB verdict: HTTP 200 with status ERR is a failure, not a row."""

    def _event(self) -> CosmicFireEvent:
        return CosmicFireEvent(redshift=0.0, coherence=0.5, sfr_rate=1.0)

    def _resp(self, body):
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = json.dumps(body).encode()
        cm.__exit__.return_value = False
        return cm

    def test_sql_targets_the_promised_table_and_carries_the_record(self):
        captured = {}

        def fake_urlopen(req, timeout=0):
            captured["sql"] = req.data.decode()
            captured["ns"] = req.get_header("Surreal-ns")
            return self._resp([{"status": "OK", "result": [{}]}])

        with patch("urllib.request.urlopen", fake_urlopen):
            persist_event(self._event())
            import time

            time.sleep(0.2)  # daemon thread
        assert captured["sql"].startswith("CREATE cosmic_fire_events SET ")
        assert '"coherence" = 0.5' not in captured["sql"] and "coherence = 0.5" in captured["sql"]
        assert captured["ns"] == "cohezion"

    def test_err_statement_is_logged_not_swallowed(self, caplog):
        with (
            patch(
                "urllib.request.urlopen",
                lambda req, timeout=0: self._resp([{"status": "ERR", "result": "no table"}]),
            ),
            caplog.at_level("WARNING", logger="cohezion.compound.cosmic_fire_protocol"),
        ):
            persist_event(self._event())
            import time

            time.sleep(0.2)
        assert any(
            "persist failed" in r.message and "no table" in r.message for r in caplog.records
        )

    def test_protocol_persist_never_raises(self):
        def boom(_e):
            raise SurrealQLError("down")

        p = CosmicFireProtocol(notify_telegram=False, persist_fn=boom)
        p.persist(self._event())  # must not raise
