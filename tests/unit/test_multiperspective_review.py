from cohezion.governance.multiperspective_review import (
    MultiperspectiveReviewEngine,
    MultiperspectiveReviewReport,
)


def test_multiperspective_review_engine_pass():
    engine = MultiperspectiveReviewEngine(pass_score_threshold=0.85)
    ctx = {
        "vram_available_gb": 35.0,
        "ring_coherence": 0.92,
        "zk_verified": True,
        "evi_score": 0.88,
    }

    report = engine.review("BBQ_Master_Plan", ctx)
    assert isinstance(report, MultiperspectiveReviewReport)
    assert len(report.findings) == 4
    assert report.overall_pass is True
    assert report.review_score == 1.0


def test_multiperspective_review_engine_fail():
    engine = MultiperspectiveReviewEngine(pass_score_threshold=0.85)
    ctx = {
        "vram_available_gb": 12.0,  # CRITICAL
        "ring_coherence": 0.30,  # HIGH
        "zk_verified": False,  # CRITICAL
        "evi_score": 0.50,
    }

    report = engine.review("Broken_Plan", ctx)
    assert report.overall_pass is False
    assert report.review_score < 0.85
