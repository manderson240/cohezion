"""Discriminating tests: OuroborosAttribution bridges exhaust → RecursiveTraceLoop."""

import numpy as np

from cohezion.learning import OuroborosAttribution as pkg_attr
from cohezion.learning.ouroboros import ExecutionExhaust
from cohezion.learning.ouroboros import OuroborosAttribution as src_attr


def _make_exhaust(**kwargs) -> ExecutionExhaust:
    defaults = dict(
        task_id="t1", error_message=None, coherence_drop=0.0, token_usage=100, diagnostics={}
    )
    defaults.update(kwargs)
    return ExecutionExhaust(**defaults)


def test_attribution_is_same():
    assert pkg_attr is src_attr


def test_error_exhaust_class():
    """Exhaust with error_message → failure_class 'error'."""
    a = src_attr.from_exhaust(_make_exhaust(error_message="OOM"))
    assert a.failure_class == "error"
    assert "reduce_context" in a.recommended_strategies


def test_coherence_drop_class():
    """Exhaust with high coherence_drop → 'coherence_drop' class."""
    a = src_attr.from_exhaust(_make_exhaust(coherence_drop=0.7))
    assert a.failure_class == "coherence_drop"


def test_token_spike_class():
    """Exhaust with high token_usage → 'token_spike' class."""
    a = src_attr.from_exhaust(_make_exhaust(token_usage=9000))
    assert a.failure_class == "token_spike"
    assert "summarize_first" in a.recommended_strategies


def test_unknown_class():
    """Nominal exhaust → 'unknown' class with retry fallback."""
    a = src_attr.from_exhaust(_make_exhaust())
    assert a.failure_class == "unknown"
    assert "retry_with_fallback" in a.recommended_strategies


def test_latent_probe_enrichment():
    """When a fitted probe is supplied with a latent vector, latent_concepts are populated
    and failure_class is refined from 'unknown' to 'latent_drift:<concept>'.

    Discriminating: if probe integration were a no-op, latent_concepts would be empty
    and failure_class would stay 'unknown'.
    """
    from cohezion.flume.diversity import LatentDirectionProbe

    rng = np.random.RandomState(7)
    samples = rng.randn(80, 256).astype(np.float32)
    samples[:40, :8] += 3.0

    probe = LatentDirectionProbe(n_directions=2).fit(samples)
    probe.label_direction(0, "token_overload")

    vec = np.zeros(256, dtype=np.float32)
    vec[:8] = 5.0  # high activation on direction 0

    a = src_attr.from_exhaust(_make_exhaust(), latent_vector=vec, probe=probe)

    assert len(a.latent_concepts) > 0
    assert "latent_concepts" in a.evidence
    # failure class should be refined for unknown → latent_drift:token_overload
    assert a.failure_class.startswith("latent_drift:")


def test_failure_map_integration():
    """OuroborosAttribution integrates cleanly with RecursiveTraceLoop.failure_map.

    The recommended_strategies list must be a valid failure_map value.
    """
    from cohezion.recursive_trace.core import RecursiveTraceLoop, TraceTask

    exhaust = _make_exhaust(coherence_drop=0.8)
    attribution = src_attr.from_exhaust(exhaust)

    # Use attribution to build a failure_map entry
    failure_map = {attribution.failure_class: attribution.recommended_strategies}
    all_strategies = list(dict.fromkeys(attribution.recommended_strategies + ["escalate"]))

    loop = RecursiveTraceLoop(strategies=all_strategies, failure_map=failure_map)
    task = TraceTask(
        task_id="t1",
        failure_class=attribution.failure_class,
        solving_strategy=attribution.recommended_strategies[0],
    )

    picks = []
    result = loop.run(task, scorer_fn=lambda t, s: picks.append(s) or s == t.solving_strategy)

    assert result.solved
    # First pick must be the mapped strategy (not list-order fallback)
    assert picks[0] == attribution.recommended_strategies[0]
