"""Vector 1: Property-Based Testing (Hypothesis).
================================================
Generates hundreds of randomized inputs to test fundamental system invariants:
1. Information Entropy Invariance & Monotonicity (My Big TOE).
2. Orch-OR Gravitational Self-Energy & Objective Reduction Bounds.
3. Secret Scrubber Redaction Invariance across arbitrary token contexts.
"""

import math
import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from cohezion.physics.my_big_toe_entropy_engine import MyBigTOEEntropyEngine
from cohezion.physics.orch_or_runtime_service import (
    OrchORRuntimeService,
    SuperposedPolicyBranch,
)
from cohezion.security.secret_scrubber import scrub_text, contains_unredacted_credentials


@pytest.mark.property
class TestPropertyBasedInvariants:
    @settings(max_examples=100, deadline=None)
    @given(
        st.lists(
            st.tuples(
                st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
                st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
            ),
            min_size=3,
            max_size=20,
        ),
        st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False),
    )
    def test_entropy_engine_properties(self, points, coherence):
        """Property: Total entropy is strictly finite, non-negative, and bounded."""
        engine = MyBigTOEEntropyEngine()
        coherences = [coherence] * len(points)

        state = engine.calculate_state_entropy(points, coherences=coherences)

        # Invariant 1: Entropy components must be non-negative and finite
        assert not math.isnan(state.total_system_entropy)
        assert not math.isinf(state.total_system_entropy)
        assert state.total_system_entropy >= 0.0
        assert state.shannon_entropy >= 0.0
        assert state.hiho_dispersion_entropy >= 0.0
        assert state.topological_entropy >= 0.0

        # Invariant 2: Scaling points towards origin (clustering) reduces or preserves volume dispersion
        clustered_points = [(p[0] * 0.5, p[1] * 0.5) for p in points]
        clustered_state = engine.calculate_state_entropy(clustered_points, coherences=coherences)
        assert clustered_state.hiho_dispersion_entropy <= state.hiho_dispersion_entropy + 1e-5

    @settings(max_examples=100, deadline=None)
    @given(
        st.integers(min_value=100, max_value=1_000_000),
        st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_orch_or_energy_and_collapse_bounds(self, tubulin_dimers, separation_nm):
        """Property: Orch-OR gravitational self-energy and collapse time must be strictly positive and finite."""
        service = OrchORRuntimeService()
        event = service.orch_engine.compute_reduction_time(
            tubulin_count=tubulin_dimers,
            separation_distance_nm=separation_nm,
        )

        assert not math.isnan(event.gravitational_self_energy_eg)
        assert not math.isnan(event.reduction_time_tau_s)
        assert event.gravitational_self_energy_eg > 0.0
        assert event.reduction_time_tau_s > 0.0
        assert not math.isinf(event.gravitational_self_energy_eg)
        assert not math.isinf(event.reduction_time_tau_s)

    @settings(max_examples=100, deadline=None)
    @given(
        st.text(min_size=0, max_size=50),
        st.text(min_size=0, max_size=50),
        st.sampled_from(
            [
                "ya29.a0AdMD6EiDsMkIvfgU2-jHgeWVbOcampReyiru0WhOsgEcjSTbziGIRk",
                "1//01lG-M5vge4DRCgYIARAAGAESNwF-L9IrzVcEUOoL9GZZUu2Qox1Y8RmS",
                "sk-1234567890abcdef1234567890abcdef",
                "AKIAIOSFODNN7EXAMPLE",
            ]
        ),
    )
    def test_secret_scrubber_invariance(self, prefix, suffix, secret_token):
        """Property: scrub_text must eliminate credential signatures regardless of arbitrary framing text."""
        raw_text = f"{prefix} {secret_token} {suffix}"
        assert contains_unredacted_credentials(raw_text)

        cleaned = scrub_text(raw_text)
        assert not contains_unredacted_credentials(cleaned)
        assert secret_token not in cleaned
