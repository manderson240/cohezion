"""Tests for the Ouroboros Bridge — physics-layer integration."""

import pytest

from cohezion.learning.ouroboros import OuroborosEngine
from cohezion.learning.ouroboros_trigger import OuroborosTrigger, TriggerState
from cohezion.physics.ouroboros_bridge import (
    COHERENCE_DROP_THRESHOLD,
    HealingEvent,
    HealingPhase,
    OuroborosBridge,
    PhysicsAnomaly,
)


@pytest.fixture
def engine():
    return OuroborosEngine(target_coherence=0.5)


@pytest.fixture
def trigger():
    return OuroborosTrigger(patience=3)


@pytest.fixture
def bridge(engine, trigger):
    return OuroborosBridge(engine=engine, trigger=trigger)


class TestCoherenceChecks:
    @pytest.mark.asyncio
    async def test_coherence_below_threshold_no_anomaly(self, bridge):
        """Coherence drop within limits should not trigger anomaly."""
        result = await bridge.check_coherence(0.1, task_id="t1")
        assert result is None
        assert len(bridge.anomalies) == 0
        assert len(bridge.healing_events) == 0

    @pytest.mark.asyncio
    async def test_coherence_at_threshold_no_anomaly(self, bridge):
        """Coherence drop exactly at threshold should not trigger."""
        result = await bridge.check_coherence(COHERENCE_DROP_THRESHOLD, task_id="t2")
        assert result is None

    @pytest.mark.asyncio
    async def test_coherence_above_threshold_triggers_anomaly(self, bridge):
        """Coherence drop above threshold triggers anomaly and healing."""
        result = await bridge.check_coherence(0.5, task_id="t3")
        assert result is not None
        assert isinstance(result, PhysicsAnomaly)
        assert result.source == "coherence_monitor"
        assert result.metric_value == 0.5
        assert result.threshold == COHERENCE_DROP_THRESHOLD
        assert len(bridge.anomalies) == 1
        assert len(bridge.healing_events) == 1

    @pytest.mark.asyncio
    async def test_coherence_triggers_ouroboros_rewrite(self, bridge, engine):
        """High coherence drop should trigger Ouroboros rewrite cycle."""
        await bridge.check_coherence(0.8, task_id="rewrite_test")
        rules = engine.get_latest_system_rules()
        assert len(rules) == 1
        assert "rewrite_test" in rules[0]


class TestJEPAChecks:
    @pytest.mark.asyncio
    async def test_jepa_below_threshold_no_anomaly(self, bridge):
        """JEPA error within limits should not trigger."""
        result = await bridge.check_jepa_error(0.2, task_id="j1")
        assert result is None

    @pytest.mark.asyncio
    async def test_jepa_above_threshold_triggers_anomaly(self, bridge):
        """JEPA error spike triggers anomaly and VAE fine-tuning."""
        result = await bridge.check_jepa_error(0.8, task_id="j2")
        assert result is not None
        assert result.source == "jepa_predictor"
        assert result.metric_name == "prediction_error"
        assert len(bridge.anomalies) == 1
        assert len(bridge.healing_events) == 1

    @pytest.mark.asyncio
    async def test_jepa_triggers_vae_training(self, bridge, trigger):
        """JEPA spike should trigger OuroborosTrigger with training state."""
        await bridge.check_jepa_error(0.9, task_id="j3")
        events = trigger.events
        assert len(events) == 1
        assert events[0].trigger_source == "coherence_collapse"
        assert events[0].state == TriggerState.TRAINING


class TestHealingEvents:
    @pytest.mark.asyncio
    async def test_healing_event_maps_to_cosmogony(self, bridge):
        """Healing events should include cosmogony interpretation."""
        await bridge.check_coherence(0.6, task_id="cosmo1")
        event = bridge.healing_events[0]
        assert isinstance(event, HealingEvent)
        assert event.cosmogony_interpretation == "manifold_coherence_correction"
        assert event.phase == HealingPhase.PATCHING

    @pytest.mark.asyncio
    async def test_health_summary_structure(self, bridge):
        """Health summary should include all expected fields."""
        await bridge.check_coherence(0.5, task_id="summary_test")
        summary = bridge.get_health_summary()
        assert summary["status"] == "anomalous"
        assert summary["total_anomalies"] == 1
        assert summary["total_healings"] == 1
        assert isinstance(summary["ouroboros_rules"], list)
        assert isinstance(summary["trigger_history"], list)
        assert isinstance(summary["recent_anomalies"], list)

    @pytest.mark.asyncio
    async def test_multiple_anomalies_accumulate(self, bridge):
        """Multiple anomalies should accumulate in history."""
        await bridge.check_coherence(0.5, task_id="a1")
        await bridge.check_jepa_error(0.7, task_id="a2")
        assert len(bridge.anomalies) == 2
        assert len(bridge.healing_events) == 2
        assert bridge.anomalies[0].source == "coherence_monitor"
        assert bridge.anomalies[1].source == "jepa_predictor"


class TestPhysicsAnomalyModel:
    def test_severity_capped_at_one(self, bridge):
        """Severity should be capped at 1.0."""
        anomaly = PhysicsAnomaly(
            source="test",
            severity=1.5,
            metric_name="test",
            metric_value=1.5,
            threshold=0.3,
        )
        # Severity from check_coherence is min(drop/1.0, 1.0)
        assert anomaly.to_dict()["source"] == "test"

    @pytest.mark.asyncio
    async def test_severity_calculation_from_coherence(self, bridge):
        """Severity should scale with coherence drop magnitude."""
        await bridge.check_coherence(0.5, task_id="sev1")
        await bridge.check_coherence(0.9, task_id="sev2")
        assert bridge.anomalies[0].severity == 0.5
        assert bridge.anomalies[1].severity == 0.9
