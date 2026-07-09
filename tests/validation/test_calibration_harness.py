"""Unit tests for the dynamically adaptive calibration harness and config reloader."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cohezion.cache.semantic_cache import SemanticCache
from cohezion.validation.calibration_harness import (
    redact_pii,
    save_calibration_profile,
)


def test_pii_redaction():
    """Verify that credentials and IP addresses are redacted, while simple prompts remain intact."""
    raw_prompt = (
        "Verify config on server with password: 'my-super-secret-pass-123' and host: 192.168.1.50"
    )
    sanitized = redact_pii(raw_prompt)
    assert (
        "password=REDACTED" in sanitized or "password: 'my-super-secret-pass-123'" not in sanitized
    )
    assert "192.168.1.50" not in sanitized
    assert "IP.REDACTED" in sanitized
    assert "Verify config" in sanitized


def test_save_and_load_calibration_profiles(monkeypatch):
    """Test atomic calibration profile save and dynamic reload behavior."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Mock the project root to target our temp directory
        monkeypatch.setattr(
            "cohezion.validation.calibration_harness.get_project_root", lambda: tmp_path
        )
        monkeypatch.setattr("cohezion.cache.semantic_cache.get_project_root", lambda: tmp_path)

        # 1. Save profile parameters
        params = {"similarity_threshold": 0.68}
        save_calibration_profile("semantic_cache", params)

        profile_file = config_dir / "calibration_profiles.json"
        assert profile_file.exists()

        # Check content
        with open(profile_file) as f:
            data = json.load(f)
            assert data["semantic_cache"]["parameters"]["similarity_threshold"] == 0.68

        # Mock the config loader in semantic_cache to use our temp path
        class MockConfig:
            root_dir = tmp_path

        monkeypatch.setattr("cohezion.cache.semantic_cache.get_config", lambda: MockConfig)

        # 2. Test lookup with environment override active (pytest defaults)
        # Should return None (bypass loading)
        cache = SemanticCache()
        assert cache._load_profile_threshold() is None

        # 3. Test lookup with environment override disabled
        # Temporarily clear env vars to simulate normal run
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("COHEZION_IGNORE_CALIBRATION_PROFILE", raising=False)

        # Create cache instance; it should load 0.68
        cache_calibrated = SemanticCache()
        val = cache_calibrated._load_profile_threshold()
        assert val == 0.68
