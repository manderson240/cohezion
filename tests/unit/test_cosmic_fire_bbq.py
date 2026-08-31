from cohezion.compound.cosmic_fire_protocol import CosmicFireEvent, CosmicFireProtocol


def test_cosmic_fire_bbq_ignition_cascade():
    cfp = CosmicFireProtocol(threshold=0.45, notify_telegram=False)

    # Test below threshold -> No ignition
    cascade_below = cfp.ignition_cascade(quality_score=0.30)
    assert cascade_below == []

    # Test above threshold -> Ignite BBQ Low and Slow Mode
    cascade = cfp.ignition_cascade(quality_score=0.50)
    assert len(cascade) == 5
    assert cascade[0] == "enter_bbq_low_slow_mode"
    assert cascade[1] == "spawn_r0_adversarial_review"
    assert cascade[2] == "escalate_to_cpu_cloud_tier"
    assert cascade[3] == "persist_cosmic_fire_event"

    event = cfp.ignite(quality_score=0.85, redshift=25.0)
    assert isinstance(event, CosmicFireEvent)
    assert event.coherence == 0.85
    assert event.redshift == 25.0
