"""Graph health computation logic tied to HIHO equilibrium."""


def compute_graph_hiho(metrics: dict) -> float:
    """Weighted average graph health score.

    Weights: connectivity 0.3, reciprocity 0.2, freshness 0.2, (1 - orphan_ratio) 0.3.
    Target: 0.5 +/- 0.15 (HIHO equilibrium).
    """
    connectivity = metrics.get("connectivity", 0.0)
    reciprocity = metrics.get("reciprocity", 0.0)
    freshness = metrics.get("freshness", 0.0)
    orphan_ratio = metrics.get("orphan_ratio", 1.0)

    return 0.3 * connectivity + 0.2 * reciprocity + 0.2 * freshness + 0.3 * (1.0 - orphan_ratio)


def classify_health(score: float) -> str:
    """Classify graph health based on HIHO equilibrium distance.

    - healthy:  0.35 <= score <= 0.65
    - degraded: 0.2 <= score < 0.35 or 0.65 < score <= 0.8
    - critical: score < 0.2 or score > 0.8
    """
    if score < 0.2 or score > 0.8:
        return "critical"
    if score < 0.35 or score > 0.65:
        return "degraded"
    return "healthy"
