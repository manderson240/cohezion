"""Keep ConfigSyncLogger's default audit log out of the repository during tests.

ConfigSyncLogger() defaults to <cwd>/data/config-sync-logs, and the orchestrator and sync
engine construct it without arguments, so every test run appended to the tracked
data/config-sync-logs/config_sync.jsonl. Only the DEFAULT is redirected; a test that passes
log_dir explicitly keeps it.
"""

from __future__ import annotations

import pytest

from cohezion.config.config_sync_logger import ConfigSyncLogger


@pytest.fixture(autouse=True)
def _sync_log_in_tmp(tmp_path, monkeypatch):
    original = ConfigSyncLogger.__init__

    def init(self, log_dir=None):
        original(self, log_dir if log_dir is not None else tmp_path / "config-sync-logs")

    monkeypatch.setattr(ConfigSyncLogger, "__init__", init)
