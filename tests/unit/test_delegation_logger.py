"""Unit tests for DelegationLogger."""

import tempfile
from pathlib import Path

from cohezion.inference.delegation_logger import DelegationEvent, DelegationLogger


def test_delegation_event_to_dict() -> None:
    event = DelegationEvent(
        task_name="coding",
        task_importance=0.9,
        quality_gap=0.3,
        escalation_cost=0.25,
        evi_score=1.08,
        source_tier=1,
        target_tier=2,
        escalated=True,
        model_selected="qwen3.5:397b-cloud",
        reason="Tier 2 escalation",
    )
    data = event.to_dict()
    assert data["task_name"] == "coding"
    assert data["evi_score"] == 1.08
    assert data["source_tier"] == 1
    assert data["target_tier"] == 2
    assert data["escalated"] is True


def test_delegation_logger_fallback_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "delegation_log.jsonl"
        logger = DelegationLogger()
        logger.fallback_path = log_path

        event1 = DelegationEvent(
            task_name="reasoning",
            task_importance=0.8,
            quality_gap=0.2,
            escalation_cost=0.25,
            evi_score=0.64,
            source_tier=1,
            target_tier=1,
            escalated=False,
            model_selected="deepseek-r1-0528-8b-FLM",
            reason="Tier 1 selected",
        )

        logger.log_delegation(event1)
        assert log_path.exists()

        events = logger.get_recent_events(limit=5)
        assert len(events) == 1
        assert events[0]["task_name"] == "reasoning"
        assert events[0]["model_selected"] == "deepseek-r1-0528-8b-FLM"
