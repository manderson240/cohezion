"""Tests for TEE Key Manager (Story 1-0-5)."""

from __future__ import annotations

import pytest

from cohezion.security.tee_key_manager import TEEKeyManager


class TestTEEKeyManager:
    def setup_method(self):
        self.mgr = TEEKeyManager()
        self.mgr.clear_events()

    def test_generate_returns_key_id_not_raw_bytes(self):
        key_id = self.mgr.generate_key("signing-key-1")
        assert key_id == "signing-key-1"
        assert isinstance(key_id, str)

    def test_key_stored_in_tee_namespace(self):
        self.mgr.generate_key("k1")
        assert self.mgr.has_key("k1")

    def test_sign_produces_hex_digest(self):
        self.mgr.generate_key("k2")
        sig = self.mgr.sign("k2", b"payload")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex

    def test_verify_valid_signature(self):
        self.mgr.generate_key("k3")
        sig = self.mgr.sign("k3", b"hello")
        assert self.mgr.verify("k3", b"hello", sig)

    def test_verify_invalid_signature(self):
        self.mgr.generate_key("k4")
        assert not self.mgr.verify("k4", b"hello", "bad" * 21 + "x")

    def test_memory_read_blocked_and_logged(self):
        self.mgr.generate_key("k5")
        with pytest.raises(PermissionError, match="TEE boundary violation"):
            self.mgr.attempt_memory_read("k5")
        events = self.mgr.security_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "UNAUTHORIZED_MEMORY_READ"
        assert events[0]["blocked"] is True

    def test_sign_unknown_key_raises(self):
        with pytest.raises(KeyError):
            self.mgr.sign("nonexistent", b"data")

    def test_multiple_keys_independent(self):
        self.mgr.generate_key("a")
        self.mgr.generate_key("b")
        sig_a = self.mgr.sign("a", b"payload")
        sig_b = self.mgr.sign("b", b"payload")
        # Different keys → different signatures
        assert sig_a != sig_b
