from cohezion.ouroboros.detector import AnomalyDetector


def test_detector_initialization():
    """Test that AnomalyDetector initializes with correct thresholds."""
    detector = AnomalyDetector(coherence_threshold=0.1)
    assert detector.coherence_threshold == 0.1
    assert detector.target_coherence == 0.5

def test_detect_degradation_true():
    """Test that significant deviation from 0.5 is detected as an anomaly."""
    detector = AnomalyDetector(coherence_threshold=0.1)
    # Deviation is 0.2 (abs(0.3 - 0.5)), which is > 0.1
    assert detector.is_anomaly(coherence=0.3) is True
    # Deviation is 0.3 (abs(0.8 - 0.5)), which is > 0.1
    assert detector.is_anomaly(coherence=0.8) is True

def test_detect_degradation_false():
    """Test that values close to 0.5 are not detected as anomalies."""
    detector = AnomalyDetector(coherence_threshold=0.1)
    # Deviation is 0.05 (abs(0.45 - 0.5)), which is < 0.1
    assert detector.is_anomaly(coherence=0.45) is False
    # Deviation is 0.05 (abs(0.55 - 0.5)), which is < 0.1
    assert detector.is_anomaly(coherence=0.55) is False

def test_analyze_batch_degradation():
    """Test batch analysis for sustained degradation."""
    detector = AnomalyDetector(coherence_threshold=0.1)
    
    # Majority of batch is anomalous
    trajectories = [
        {"coherence": 0.3},
        {"coherence": 0.2},
        {"coherence": 0.5},
        {"coherence": 0.3},
    ]
    report = detector.analyze_batch(trajectories)
    assert report["is_degraded"] is True
    assert report["anomaly_count"] == 3

def test_analyze_batch_stable():
    """Test batch analysis for stable state."""
    detector = AnomalyDetector(coherence_threshold=0.1)
    
    # Majority of batch is within threshold
    trajectories = [
        {"coherence": 0.45},
        {"coherence": 0.52},
        {"coherence": 0.3}, # Single anomaly
        {"coherence": 0.48},
    ]
    report = detector.analyze_batch(trajectories)
    assert report["is_degraded"] is False
    assert report["anomaly_count"] == 1
