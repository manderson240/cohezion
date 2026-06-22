"""Discriminating identity tests: flume orphans wired in round-2/interpretability sweep."""

import numpy as np

from cohezion.flume import ConceptDirection as pkg_ConceptDirection
from cohezion.flume import LatentDirectionProbe as pkg_ldp
from cohezion.flume import SkillStateEncoder as pkg_sse
from cohezion.flume import gvendi_diversity_filter as pkg_gvendi
from cohezion.flume.diversity import ConceptDirection as src_ConceptDirection
from cohezion.flume.diversity import LatentDirectionProbe as src_ldp
from cohezion.flume.diversity import gvendi_diversity_filter as src_gvendi
from cohezion.flume.skill_state_encoder import SkillStateEncoder as src_sse


def test_gvendi_diversity_filter_is_same():
    assert pkg_gvendi is src_gvendi


def test_skill_state_encoder_is_same():
    assert pkg_sse is src_sse


def test_latent_direction_probe_is_same():
    """Identity — wiring points at the real class, not a copy."""
    assert pkg_ldp is src_ldp


def test_concept_direction_is_same():
    assert pkg_ConceptDirection is src_ConceptDirection


def test_latent_direction_probe_discriminates():
    """Discriminating: a vector with high activations on learned directions
    must have higher concept_alignment than the zero vector.
    This would fail if fit() were a no-op or directions were all-zero.
    """
    rng = np.random.RandomState(0)
    samples = rng.randn(100, 256).astype(np.float32)
    samples[:50, :8] += 2.0  # introduce a structured direction

    probe = pkg_ldp(n_directions=3).fit(samples)
    probe.label_direction(0, "structure")

    high = np.zeros(256, dtype=np.float32)
    high[:8] = 3.0
    low = np.zeros(256, dtype=np.float32)

    a_high = probe.concept_alignment(high, "structure")
    a_low = probe.concept_alignment(low, "structure")

    assert probe.fitted
    assert abs(a_high - a_low) > 0.01, (
        f"Probe should discriminate structured vs zero vector: {a_high:.4f} vs {a_low:.4f}"
    )
