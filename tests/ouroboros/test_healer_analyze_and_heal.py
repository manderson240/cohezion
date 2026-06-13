"""Tests for OuroborosHealer.analyze_and_heal + bus HEALING_EVENT emission (WS1B, 2026-06-04)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def test_healer_class_exists():
    """OuroborosHealer must be importable from cohezion.ouroboros.healer."""
    from cohezion.ouroboros.healer import HealerAgent

    assert HealerAgent is not None


def test_healer_has_analyze_and_heal_method():
    """HealerAgent must expose analyze_and_heal(failure_log, target) ->
    HealingResult. The method must NOT depend on the LLM (best-effort)."""
    from cohezion.ouroboros.healer import HealerAgent

    # Healer may need a model_name; if it has a default, use it
    try:
        healer = HealerAgent()
    except Exception:
        # Some __init__ paths require a real LLM client. Use a mock.
        with patch(
            "cohezion.agents.base.BaseAgent.__init__",
            return_value=None,
        ):
            healer = HealerAgent()

    assert hasattr(healer, "analyze_and_heal"), (
        "HealerAgent must expose analyze_and_heal(failure_log, target)"
    )


def test_healer_analyze_and_heal_emits_healing_event_to_bus():
    """When analyze_and_heal() runs, it must emit a HEALING_EVENT to the
    precipitation bus with the analysis result in the payload."""
    from cohezion.ouroboros.healer import HealerAgent
    from cohezion.precipitation.bus import get_bus
    from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind

    # Capture bus events
    bus = get_bus()
    captured: list[PrecipitationEvent] = []

    def spy(event: PrecipitationEvent) -> None:
        if event.kind == PrecipitationKind.HEALING_EVENT:
            captured.append(event)

    bus.subscribe(spy, kind=PrecipitationKind.HEALING_EVENT)

    try:
        with patch(
            "cohezion.agents.base.BaseAgent.__init__",
            return_value=None,
        ):
            healer = HealerAgent()
        # Mock synthesize_patch to avoid LLM call
        if hasattr(healer, "synthesize_patch"):
            healer.synthesize_patch = MagicMock(return_value="(patch proposal)")

        log = (
            "RuntimeError: CUDA out of memory. Tried to allocate 2 GiB on device 0. "
            "Consider reducing the batch size, using gradient accumulation, or moving "
            "the model to a smaller precision. The training run aborted at step 1234."
        )
        result = healer.analyze_and_heal(failure_log=log, target="training")

        # Result must be a dict with root_cause + suggested_mutation
        assert isinstance(result, dict)
        assert "root_cause" in result
        assert "suggested_mutation" in result

        # Bus must have received a HEALING_EVENT
        assert len(captured) >= 1, "analyze_and_heal must emit HEALING_EVENT to bus"
        evt = captured[0]
        assert evt.universe_id.startswith("ouroboros.heal.")
        assert "root_cause" in evt.payload
        assert "target" in evt.payload
    finally:
        bus.unsubscribe(spy)


def test_healer_handles_llm_failure_gracefully():
    """If synthesize_patch fails (LLM down), analyze_and_heal must still
    complete + emit HEALING_EVENT (the deterministic FailureAnalyzer
    result is enough; the LLM patch is best-effort)."""
    from cohezion.ouroboros.healer import HealerAgent
    from cohezion.precipitation.bus import get_bus
    from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind

    bus = get_bus()
    captured: list[PrecipitationEvent] = []

    def spy(event: PrecipitationEvent) -> None:
        if event.kind == PrecipitationKind.HEALING_EVENT:
            captured.append(event)

    bus.subscribe(spy, kind=PrecipitationKind.HEALING_EVENT)

    try:
        with patch(
            "cohezion.agents.base.BaseAgent.__init__",
            return_value=None,
        ):
            healer = HealerAgent()
        # Force synthesize_patch to raise
        if hasattr(healer, "synthesize_patch"):
            healer.synthesize_patch = MagicMock(side_effect=RuntimeError("llm down"))

        log = (
            "ModuleNotFoundError: No module named 'cohezion_thing'. The test environment "
            "is missing a dependency. Install via uv pip install cohezion_thing."
        )
        result = healer.analyze_and_heal(failure_log=log, target="test")

        assert isinstance(result, dict)
        assert "root_cause" in result
        # Bus event must STILL fire (the LLM failure is best-effort)
        assert len(captured) >= 1
    finally:
        bus.unsubscribe(spy)
