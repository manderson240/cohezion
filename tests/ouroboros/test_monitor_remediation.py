import pytest
from unittest.mock import patch
from cohezion.ouroboros.card_alignment_monitor import CardAlignmentMonitor
from cohezion.precipitation.events import PrecipitationKind

def test_monitor_model_id_tracking():
    """Verify monitor initializes with model_id and includes it in emitted HEALING_EVENT payload."""
    monitor = CardAlignmentMonitor(threshold=0.5, window_size=5, model_id="qwen3-coder:30b")
    assert monitor.model_id == "qwen3-coder:30b"
    
    # Push 5 failures to trigger HEALING_EVENT
    for _ in range(5):
        monitor.record_execution(card_aligned=False)
        
    with patch("cohezion.precipitation.bus.emit") as mock_emit:
        verdict = monitor.check()
        assert verdict.dipped
        mock_emit.assert_called_once()
        event = mock_emit.call_args[0][0]
        
        assert event.kind == PrecipitationKind.HEALING_EVENT
        assert event.payload["model_id"] == "qwen3-coder:30b"
        assert event.payload["rate"] == 0.0
        assert event.payload["threshold"] == 0.5
        assert "timestamp" in event.payload
