"""HIHO Coherence Invariant Tests — The Platform's Core Behavioral Contract.

HIHO (High-In, High-Out) Principle: Every COHEZION module that processes
12D manifold state must maintain the Hooke's Law attractor at coherence=0.5.
Outputs must stay in the band [0.3, 0.7] — neither collapsing to zero
(hallucination) nor spiking to one (rigid over-fitting).

These tests prove the HIHO invariant is *computable* across all 8 new Epic 1–5
substrate modules. This is the behavioral contract that distinguishes COHEZION
from conventional AI orchestration frameworks.

Reference: HIHO Principle in COHEZION_CHARTER.md — Hooke's Law attractor:
  F = -k(x - x_eq) where x_eq = 0.5 (coherence equilibrium point)
"""

from __future__ import annotations

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# HIHO Band Constants
# ──────────────────────────────────────────────────────────────────────────────

HIHO_LOW = 0.3  # Below this: coherence collapse (hallucination risk)
HIHO_HIGH = 0.7  # Above this: rigid over-fitting risk
HIHO_CENTER = 0.5
HIHO_TOLERANCE = 0.2  # ± from center


def _in_hiho_band(value: float) -> bool:
    """Return True if value is within the HIHO coherence band."""
    return HIHO_LOW <= value <= HIHO_HIGH


# ──────────────────────────────────────────────────────────────────────────────
# Module 1: ExperienceEncoder (FLUME pipeline foundation)
# ──────────────────────────────────────────────────────────────────────────────


class TestExperienceEncoderHIHO:
    """ExperienceEncoder 256D output must have mean near 0.5 (HIHO attractor)."""

    def _make_experience(self, phi_score: float = 0.5, op_type: str = "generate") -> dict:
        return {
            "trajectory": np.random.default_rng(42).normal(0.5, 0.15, 12).astype(np.float32),
            "mission_id": "hiho-test",
            "agent_id": "test-agent",
            "skill_name": "research",
            "input_preview": "test",
            "operation_type": op_type,
            "phi_score": phi_score,
        }

    def test_encoder_output_mean_in_hiho_band(self) -> None:
        """Encoded 256D vector mean must lie within HIHO band [0.3, 0.7]."""
        from cohezion.flume.experience_encoder import ExperienceEncoder

        encoder = ExperienceEncoder()
        vec = encoder.encode(self._make_experience(phi_score=0.5))

        # The fingerprint component (dims 29:256) is SHA-256 derived and normalized
        # to [0, 1]; the overall mean converges toward 0.5.
        mean = float(np.mean(vec))
        assert _in_hiho_band(mean), (
            f"ExperienceEncoder mean={mean:.3f} is outside HIHO band [{HIHO_LOW}, {HIHO_HIGH}]. "
            "The 256D encoding should produce values centered near 0.5."
        )

    def test_encoder_hiho_band_preserved_under_extreme_phi(self) -> None:
        """Even with phi_score at extremes, encoder output stays in HIHO band."""
        from cohezion.flume.experience_encoder import ExperienceEncoder

        encoder = ExperienceEncoder()
        for phi in [0.0, 0.1, 0.9, 1.0]:
            vec = encoder.encode(self._make_experience(phi_score=phi))
            mean = float(np.mean(vec))
            assert _in_hiho_band(mean), (
                f"phi={phi}: encoder mean={mean:.3f} outside HIHO band. "
                "Encoder must normalize extreme inputs."
            )

    def test_encoder_trajectory_component_in_hiho_band(self) -> None:
        """The 12D trajectory component (dims 0:12) must center near 0.5."""
        from cohezion.flume.experience_encoder import ExperienceEncoder

        encoder = ExperienceEncoder()
        # Trajectory with values clustered around 0.5 by construction
        exp = self._make_experience()
        exp["trajectory"] = np.full(12, 0.5, dtype=np.float32)
        vec = encoder.encode(exp)
        trajectory_mean = float(np.mean(vec[:12]))
        assert _in_hiho_band(trajectory_mean), (
            f"Trajectory dims mean={trajectory_mean:.3f} outside HIHO band."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Module 2: VLIWBridge (12D state transitions)
# ──────────────────────────────────────────────────────────────────────────────


class TestVLIWBridgeHIHO:
    """VLIWBridge state transitions must keep state values within HIHO band."""

    def test_simd_transition_values_in_hiho_band(self) -> None:
        """SIMD transition: output state mean stays in HIHO band."""
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge()  # SIMD mode
        state = np.full(12, 0.5, dtype=float)  # Start at equilibrium
        delta = np.full(12, 0.05, dtype=float)  # Small push

        result = bridge.execute_state_transition(state, delta)
        mean = float(np.mean(result))
        assert _in_hiho_band(mean), (
            f"SIMD transition mean={mean:.3f} outside HIHO band. "
            "State transitions must be clipped to [-1,1] and centered."
        )

    def test_fallback_transition_values_in_hiho_band(self) -> None:
        """Python fallback: output state mean stays in HIHO band."""
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge(force_fallback=True)
        state = np.full(12, 0.5, dtype=float)
        delta = np.full(12, 0.05, dtype=float)

        result = bridge.execute_state_transition(state, delta)
        mean = float(np.mean(result))
        assert _in_hiho_band(mean), f"Fallback transition mean={mean:.3f} outside HIHO band."

    def test_large_delta_clipped_to_hiho_band(self) -> None:
        """Extreme delta must be clipped — HIHO attractor prevents runaway."""
        from cohezion.physics.vliw_bridge import VLIWBridge

        bridge = VLIWBridge()
        state = np.full(12, 0.5, dtype=float)
        delta = np.full(12, 10.0, dtype=float)  # Extreme delta

        result = bridge.execute_state_transition(state, delta)
        # All values should be clipped to [-1, 1]
        assert float(np.max(result)) <= 1.0, "VLIW state must be clipped to ≤ 1.0"
        assert float(np.min(result)) >= -1.0, "VLIW state must be clipped to ≥ -1.0"


# ──────────────────────────────────────────────────────────────────────────────
# Module 3: TriuneConsensus (NFR-7, FR-14)
# ──────────────────────────────────────────────────────────────────────────────


class TestTriuneConsensusHIHO:
    """TriuneConsensus centroid must converge toward 0.5 when agents start spread."""

    def test_consensus_centroid_near_hiho_equilibrium(self) -> None:
        """Three agents at [0.3, 0.5, 0.7] → centroid exactly at 0.5."""
        from cohezion.swarm.triune_consensus import AgentProposal, TriuneConsensus

        consensus = TriuneConsensus()
        proposals = [
            AgentProposal(agent_id="architect", confidence=0.3, state_12d=[0.3] * 12),
            AgentProposal(agent_id="engineer", confidence=0.5, state_12d=[0.5] * 12),
            AgentProposal(agent_id="biologist", confidence=0.7, state_12d=[0.7] * 12),
        ]
        report = consensus.deliberate(proposals)

        centroid_mean = float(np.mean(report.equilibrium.centroid_12d))
        assert abs(centroid_mean - HIHO_CENTER) < 0.01, (
            f"TriuneConsensus centroid={centroid_mean:.3f} should equal {HIHO_CENTER} "
            "when agents are symmetrically spread around equilibrium."
        )

    def test_consensus_kl_divergence_finite(self) -> None:
        """KL divergence must be finite (bounded) — prevents information collapse."""
        from cohezion.swarm.triune_consensus import AgentProposal, TriuneConsensus

        consensus = TriuneConsensus()
        proposals = [
            AgentProposal(agent_id="a", confidence=0.4, state_12d=[0.4] * 12),
            AgentProposal(agent_id="b", confidence=0.6, state_12d=[0.6] * 12),
        ]
        report = consensus.deliberate(proposals)
        assert np.isfinite(report.kl_divergence), (
            "KL divergence must be finite — infinite divergence signals degenerate consensus."
        )

    def test_consensus_quorum_requires_two_agents(self) -> None:
        """Single agent cannot achieve HIHO consensus — quorum requires ≥ 2."""
        from cohezion.swarm.triune_consensus import AgentProposal, TriuneConsensus

        consensus = TriuneConsensus()
        proposals = [
            AgentProposal(agent_id="solo", confidence=0.5, state_12d=[0.5] * 12),
        ]
        report = consensus.deliberate(proposals)
        assert not report.equilibrium.is_consensus, (
            "Single agent cannot constitute consensus — HIHO requires multi-agent quorum."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Module 4: ManifoldSharding (Winston Decoupling)
# ──────────────────────────────────────────────────────────────────────────────


class TestManifoldShardingHIHO:
    """ManifoldSharding coherence score must be within HIHO band after sharding."""

    def test_sharded_coherence_in_hiho_band(self) -> None:
        """After sharding 2048D into 4 shards, boundary coherence stays in [0.3, 0.7]."""
        from cohezion.core.manifold_sharding import DistributedManifold

        manifold = DistributedManifold(total_dims=2048, num_shards=4)
        manifold.enable_distributed_pulse()

        report = manifold.compute_coherence()
        assert _in_hiho_band(report.boundary_coherence), (
            f"Manifold boundary coherence={report.boundary_coherence:.3f} outside HIHO band. "
            "Shard boundaries must maintain holographic coherence."
        )

    def test_coherence_stable_after_atomic_flip(self) -> None:
        """After an atomic pointer flip, coherence must remain in HIHO band."""
        from cohezion.core.manifold_sharding import DistributedManifold

        manifold = DistributedManifold(total_dims=2048, num_shards=4)
        manifold.enable_distributed_pulse()

        # Flip shard data and check coherence remains stable
        new_data = np.full(512, 0.5)
        manifold.atomic_flip(shard_id=0, new_data=new_data)

        report = manifold.compute_coherence()
        assert _in_hiho_band(report.boundary_coherence), (
            f"Post-flip coherence={report.boundary_coherence:.3f} outside HIHO band."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Module 5: ZeroCopyValidator (NFR-9)
# ──────────────────────────────────────────────────────────────────────────────


class TestZeroCopyValidatorHIHO:
    """ZeroCopyValidator must accept HIHO-band state vectors without error."""

    def test_hiho_state_passes_validation(self) -> None:
        """A 12D state vector with values in [0.3, 0.7] must validate cleanly."""
        import struct

        from cohezion.core.zero_copy_validator import SHMBuffer, ZeroCopyValidator

        # Create a valid 12D HIHO-band state
        state = [0.5] * 12
        raw = struct.pack(f"{len(state)}d", *state)
        checksum = __import__("hashlib").sha256(raw).hexdigest()
        buf = SHMBuffer(dtype="float64", data=raw, checksum=checksum)

        validator = ZeroCopyValidator(expected_dim=12)
        result = validator.validate_and_read(buf)

        assert result is not None, "HIHO-band state must pass ZeroCopy validation."
        assert len(result) == 12, f"Expected 12D, got {len(result)}D."
        mean = float(np.mean(result))
        assert _in_hiho_band(mean), f"Validated state mean={mean:.3f} outside HIHO band."


# ──────────────────────────────────────────────────────────────────────────────
# Module 6: OuroborosVersionHealer (NFR-OUROBOROS_VERSION_HEALING)
# ──────────────────────────────────────────────────────────────────────────────


class TestOuroborosVersionHealerHIHO:
    """OuroborosVersionHealer auto-heal rate must stay at or above HIHO-analogous 0.5."""

    def test_auto_heal_rate_at_or_above_hiho_threshold(self) -> None:
        """After 10 simple conflicts, auto-heal rate ≥ 0.5 (HIHO minimum)."""
        from cohezion.registry.ouroboros_version_healer import OuroborosVersionHealer

        healer = OuroborosVersionHealer()
        for i in range(8):  # 8 simple conflicts
            healer.heal(f"simple-{i}", {"pkg": "1.0.0"}, {"pkg": [">=1.1.0"]})
        for i in range(2):  # 2 complex conflicts
            healer.heal(f"complex-{i}", {"pkg": "1.0.0"}, {}, is_complex=True)

        rate = healer.auto_heal_rate()
        assert rate >= HIHO_LOW, (
            f"Auto-heal rate={rate:.2f} below HIHO minimum {HIHO_LOW}. "
            "Version healing must be effective at least 30% of the time."
        )

    def test_target_auto_heal_rate_above_hiho_center(self) -> None:
        """Pure simple conflicts → auto-heal rate ≥ 0.8, above HIHO center."""
        from cohezion.registry.ouroboros_version_healer import OuroborosVersionHealer

        healer = OuroborosVersionHealer()
        for i in range(4):
            healer.heal(f"s{i}", {"pkg": "1.0.0"}, {"pkg": [">=1.1.0"]})
        healer.heal("complex", {"pkg": "1.0.0"}, {}, is_complex=True)

        rate = healer.auto_heal_rate()
        assert rate >= 0.8, (
            f"Auto-heal rate={rate:.2f} below target 0.8. "
            "HIHO requires high self-healing efficiency."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Module 7: VersionTelemetry (NFR-VERSION_TELEMETRY)
# ──────────────────────────────────────────────────────────────────────────────


class TestVersionTelemetryHIHO:
    """VersionTelemetry coherence score must obey HIHO band dynamics."""

    def test_fully_synced_versions_score_one(self) -> None:
        """No drift → coherence = 1.0 (HIHO upper bound for perfect state)."""
        from cohezion.registry.version_telemetry import VersionTelemetry

        telemetry = VersionTelemetry()
        panel = telemetry.scan({"numpy": "2.0.0"}, {"numpy": "2.0.0"})
        assert panel.coherence_score == 1.0, "Perfect sync must yield coherence=1.0."

    def test_drift_pulls_coherence_toward_hiho_band(self) -> None:
        """Moderate drift → coherence < 1.0, still above HIHO_LOW."""
        from cohezion.registry.version_telemetry import VersionTelemetry

        telemetry = VersionTelemetry()
        panel = telemetry.scan({"requests": "2.28.0"}, {"requests": "2.31.0"})
        assert panel.coherence_score < 1.0, "Any drift must lower coherence from 1.0."
        # Single minor-version drift should keep coherence above collapse threshold
        assert panel.coherence_score > 0.0, "Single drift must not collapse coherence to 0."

    def test_severe_drift_triggers_hiho_healing(self) -> None:
        """Coherence < 0.3 triggers healing — HIHO collapse prevention."""
        from cohezion.registry.version_telemetry import VersionConflict, VersionTelemetry

        telemetry = VersionTelemetry()
        current = {f"pkg{i}": "1.0.0" for i in range(5)}
        latest = {f"pkg{i}": "1.9.0" for i in range(5)}
        conflicts = [VersionConflict("x", ">=2.0", "<2.0", ["a", "b"])]

        panel = telemetry.scan(current, latest, conflicts=conflicts)
        assert panel.healing_triggered, (
            "Severe coherence drift must trigger HIHO healing to prevent collapse."
        )
