import pytest
from pydantic import ValidationError
from cohezion.data_mesh.universe_telemetry import UniverseStateEvent

def test_universe_state_event_schema():
    """Verify that UniverseStateEvent can be instantiated with valid data."""
    data = {
        "event_id": "ue_123",
        "universe_id": "uni_alpha",
        "state_12d": [0.1] * 12,
        "coherence": 0.5005,
        "trigger_journey_id": "journey_abc",
        "stability_shift": 0.06
    }
    
    event = UniverseStateEvent(**data)
    assert event.event_id == "ue_123"
    assert event.coherence == 0.5005
    assert len(event.state_12d) == 12

def test_universe_state_event_invalid_12d():
    """Verify that invalid 12D state raises validation error."""
    data = {
        "event_id": "ue_123",
        "universe_id": "uni_alpha",
        "state_12d": [0.1] * 11, # Incorrect length
        "coherence": 0.5005,
        "trigger_journey_id": "journey_abc"
    }
    
    with pytest.raises(ValidationError):
        UniverseStateEvent(**data)
