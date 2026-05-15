"""Adversarial batch Z61: constitutional_enforcer bypass patterns + substrate_governor boundary.

Tests that expose REAL bugs — invariants that SHOULD hold but currently FAIL.
Each test documents a security gap or state-consistency violation.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Module 1: security/constitutional_enforcer.py — security bypass gaps
# ---------------------------------------------------------------------------


class TestConstitutionalEnforcerAdversarial:
    def _make_enforcer(self):
        from cohezion.security.constitutional_enforcer import ConstitutionalEnforcer

        return ConstitutionalEnforcer()

    # --- nmap case-sensitivity gap ---

    def test_nmap_uppercase_blocked(self):
        """Nmap (title-case) must be blocked — attacker controls casing."""
        enforcer = self._make_enforcer()
        # BUG: r"nmap\b" has no (?i) flag — Nmap slips through
        violations = enforcer.check("Nmap -sV 192.168.1.1")
        assert len(violations) > 0, "Nmap (title-case) bypasses infra-attack detection"

    def test_nmap_all_caps_blocked(self):
        """NMAP (all-caps) must be blocked."""
        enforcer = self._make_enforcer()
        violations = enforcer.check("NMAP -p 1-65535 192.168.0.0/24")
        assert len(violations) > 0, "NMAP (all-caps) bypasses infra-attack detection"

    # --- fork bomb variant gap ---

    def test_fork_bomb_with_spaces_around_pipe_blocked(self):
        """Fork bomb with spaces around pipe must be blocked.

        Canonical bash fork bomb: :(){ :|:& };:
        With spaces: :(){ : | : & };:  ← currently bypasses the regex
        """
        enforcer = self._make_enforcer()
        # BUG: r":\(\)\s*\{\s*:\|:\s*&\s*\}" requires :|: with no spaces
        violations = enforcer.check(":(){ : | : & };:")
        assert len(violations) > 0, "Fork bomb with spaced pipe bypasses detection"

    # --- rm -fr (transposed flags) gap ---

    def test_rm_fr_slash_blocked(self):
        """rm -fr / (transposed flags) must be blocked same as rm -rf /."""
        enforcer = self._make_enforcer()
        # BUG: pattern hardcodes -rf order; -fr is the same command
        violations = enforcer.check("rm -fr /")
        assert len(violations) > 0, "rm -fr / (transposed flags) bypasses detection"

    # --- rm with extra flags gap ---

    def test_rm_rf_no_preserve_root_blocked(self):
        """rm -rf --no-preserve-root / must be blocked — it deletes the root filesystem."""
        enforcer = self._make_enforcer()
        # BUG: pattern r"rm\s+-rf\s+/" requires -rf immediately before /
        violations = enforcer.check("rm -rf --no-preserve-root /")
        assert len(violations) > 0, "rm -rf --no-preserve-root / bypasses detection"

    # --- Verify known-safe baseline still works ---

    def test_safe_input_still_passes(self):
        """Benign command must remain unblocked after any fix."""
        enforcer = self._make_enforcer()
        assert enforcer.is_safe("ls -la /tmp")

    def test_rm_rf_tmp_still_allowed(self):
        """rm -rf /tmp/foo must remain ALLOWED — intentional design."""
        enforcer = self._make_enforcer()
        assert enforcer.is_safe("rm -rf /tmp/build_artifacts")

    def test_canonical_nmap_still_blocked(self):
        """Lowercase nmap must still be blocked after any case fix."""
        enforcer = self._make_enforcer()
        violations = enforcer.check("nmap -sS 10.0.0.1")
        assert len(violations) > 0


# ---------------------------------------------------------------------------
# Module 2: core/substrate_governor.py — exact-boundary state inconsistency
# ---------------------------------------------------------------------------


class TestSubstrateGovernorAdversarial:
    def _make_governor(self):
        from cohezion.core.substrate_governor import SubstrateGovernor

        return SubstrateGovernor()

    def test_factor_reset_at_exact_recovery_boundary(self):
        """At exactly the recovery target (0.85), dilation factor must be reset to 1.0.

        BUG: condition is `pressure < recovery_target` (strict less-than).
        At pressure=0.85 exactly, the elif doesn't fire → level=NORMAL but factor≠1.0.
        State inconsistency: NORMAL level with high dilation factor.
        """
        governor = self._make_governor()
        governor.update_pressure(0.92)  # elevate to get factor > 1.0
        assert governor._state.factor > 1.0

        state = governor.update_pressure(0.85)  # exactly at recovery boundary
        # Both MUST be true together — NORMAL level with factor>1.0 is incoherent
        assert state.level.value == "normal"
        assert state.factor == pytest.approx(1.0), (
            f"At exact recovery boundary 0.85, factor should be 1.0 but was {state.factor}"
        )

    def test_level_factor_coherence_invariant(self):
        """NORMAL level must always have factor==1.0 (state coherence invariant)."""
        from cohezion.core.substrate_governor import PressureLevel

        governor = self._make_governor()
        # Elevate then drop to recovery boundary
        governor.update_pressure(0.93)
        state = governor.update_pressure(0.85)

        if state.level == PressureLevel.NORMAL:
            assert state.factor == pytest.approx(1.0), "Invariant violated: NORMAL level must have dilation factor=1.0"

    def test_pulse_interval_matches_level_at_boundary(self):
        """Pulse interval must equal base when level is NORMAL — even at exact boundary."""
        governor = self._make_governor()
        governor.update_pressure(0.91)
        governor.update_pressure(0.85)  # exact boundary

        interval = governor.get_pulse_interval(100.0)
        state = governor.state
        if state.level.value == "normal":
            # NORMAL level must give normal speed
            assert interval == pytest.approx(100.0), (
                f"NORMAL level gives interval {interval}ms instead of 100ms — factor={state.factor}"
            )
