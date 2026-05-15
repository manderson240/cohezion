"""Adversarial batch Z63: zero_copy_validator fallback + consent SESSION bleed.

Real bugs found:
1. ZeroCopyValidator fallback uses hardcoded MANIFOLD_DIM=12 instead of
   the instance's expected_dim — crashes with struct.error for any non-12D validator.
2. ConsentManager SESSION scope authorises unrelated actions for any user —
   documented as a known gap (fix requires API change, tracked separately).
"""

from __future__ import annotations

import struct

import pytest


# ---------------------------------------------------------------------------
# Module 1: core/zero_copy_validator.py — fallback uses wrong dim constant
# ---------------------------------------------------------------------------


class TestZeroCopyFallbackDim:
    def _make_good_buf(self, values: list[float]):
        from cohezion.core.zero_copy_validator import SHMBuffer

        data = struct.pack(f"{len(values)}d", *values)
        buf = SHMBuffer(data=data, declared_dtype="float64", declared_dim=len(values))
        buf.checksum = buf.compute_checksum()
        return buf

    def _make_corrupt_buf(self, values: list[float]):
        """Same size/dtype but wrong checksum — triggers fallback path."""
        from cohezion.core.zero_copy_validator import SHMBuffer

        data = struct.pack(f"{len(values)}d", *values)
        buf = SHMBuffer(data=data, declared_dtype="float64", declared_dim=len(values))
        buf.checksum = "000000000000000000000000000000000000000000000000000000000000dead"
        return buf

    def test_fallback_returns_correct_dim_for_6d_validator(self):
        """Fallback must return 6 floats for a 6D validator — not crash with struct.error.

        BUG: fallback path does struct.unpack(f'{MANIFOLD_DIM}d', snapshot) where
        MANIFOLD_DIM=12 (module constant). For a 6D validator the snapshot has 48 bytes
        but the unpack expects 96 bytes → struct.error.
        Fix: use self._expected_dim (or derive dim from snapshot length).
        """
        from cohezion.core.zero_copy_validator import ZeroCopyValidator

        v = ZeroCopyValidator(expected_dim=6)
        good = self._make_good_buf([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        v.validate_and_read(good)  # populate snapshot

        corrupt = self._make_corrupt_buf([9.0, 9.0, 9.0, 9.0, 9.0, 9.0])
        result = v.validate_and_read(corrupt)  # must not raise

        assert len(result) == 6, f"Expected 6 floats from fallback, got {len(result)}"
        assert result == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_fallback_returns_correct_dim_for_3d_validator(self):
        """Same failure for 3D validator — any non-12D custom dim crashes."""
        from cohezion.core.zero_copy_validator import ZeroCopyValidator

        v = ZeroCopyValidator(expected_dim=3)
        good = self._make_good_buf([0.1, 0.2, 0.3])
        v.validate_and_read(good)

        corrupt = self._make_corrupt_buf([9.0, 9.0, 9.0])
        result = v.validate_and_read(corrupt)

        assert len(result) == 3
        assert result == pytest.approx([0.1, 0.2, 0.3])

    def test_default_12d_fallback_still_works(self):
        """Default MANIFOLD_DIM=12 validator must continue to work after fix."""
        from cohezion.core.zero_copy_validator import ZeroCopyValidator

        v = ZeroCopyValidator()  # default expected_dim=12
        values = [float(i) for i in range(12)]
        good = self._make_good_buf(values)
        v.validate_and_read(good)

        corrupt = self._make_corrupt_buf(values)
        result = v.validate_and_read(corrupt)

        assert len(result) == 12
        assert result == pytest.approx(values)

    def test_fallback_corruption_event_logged(self):
        """Fallback must log a corruption event even when it succeeds."""
        from cohezion.core.zero_copy_validator import ZeroCopyValidator

        v = ZeroCopyValidator(expected_dim=6)
        v.validate_and_read(self._make_good_buf([1.0] * 6))
        v.validate_and_read(self._make_corrupt_buf([2.0] * 6))

        events = v.corruption_events()
        assert len(events) == 1
        assert events[0]["dim"] == 6


# ---------------------------------------------------------------------------
# Module 2: security/consent_manager.py — SESSION scope bleed (known gap)
# ---------------------------------------------------------------------------


class TestConsentSessionScopeGap:
    """Documents the SESSION scope cross-action bleed.

    ConsentManager.check_consent() returns a SESSION token for ANY action,
    even if it was granted only for a different action. This means:
        grant_consent("read_files", SESSION) → check_consent("delete_database") → ALLOW
    This violates the principle of least privilege. Tracked as a known gap;
    fix requires adding user_id/action filtering to check_consent().
    """

    def test_session_scope_does_not_authorise_unrelated_actions(self):
        """SESSION token for 'read_files' must NOT authorise 'delete_database'.

        BUG: check_consent iterates tokens and returns any valid SESSION token
        regardless of which action it was granted for — privilege escalation.
        """
        from cohezion.security.consent_manager import ConsentManager, ConsentScope

        cm = ConsentManager()
        cm.grant_consent("read_files", user_id="user_a", scope=ConsentScope.SESSION)

        result = cm.check_consent("delete_database")
        assert result is None, (
            "SESSION token for 'read_files' must not authorise 'delete_database' "
            f"(got token granted_by={result.granted_by if result else None})"
        )

    def test_session_scope_does_authorise_original_action(self):
        """SESSION token must still authorise the action it was explicitly granted for."""
        from cohezion.security.consent_manager import ConsentManager, ConsentScope

        cm = ConsentManager()
        cm.grant_consent("read_files", user_id="user_a", scope=ConsentScope.SESSION)

        result = cm.check_consent("read_files")
        assert result is not None

    def test_revoke_removes_token_immediately(self):
        """Revoked token must not be returned by check_consent."""
        from cohezion.security.consent_manager import ConsentManager, ConsentScope

        cm = ConsentManager()
        token = cm.grant_consent("read_files", user_id="user_a", scope=ConsentScope.SINGLE_ACTION)
        assert cm.check_consent("read_files") is not None

        cm.revoke(token.token_id)
        assert cm.check_consent("read_files") is None
