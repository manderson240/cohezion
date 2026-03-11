"""Tests for session management module."""

import json
import os
import subprocess
import sys
from pathlib import Path

WKDIR = Path(__file__).parent.parent


def run_cz(*args: str, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(WKDIR / "src")}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "cohezion_engine.cli", *args],
        capture_output=True,
        text=True,
        cwd=WKDIR,
        env=env,
    )


class TestSessionModule:
    def test_get_session_id_from_env(self, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-session-123")
        from cohezion_engine import session as sess_mod

        assert sess_mod.get_session_id() == "test-session-123"

    def test_get_session_id_fallback_to_pid(self, monkeypatch):
        monkeypatch.delenv("COHEZION_SESSION_ID", raising=False)
        from cohezion_engine import session as sess_mod

        sid = sess_mod.get_session_id()
        assert sid  # non-empty
        assert isinstance(sid, str)

    def test_get_session_dir_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-abc")
        from cohezion_engine import session as sess_mod

        sess_dir = sess_mod.get_session_dir(base_dir=tmp_path)
        assert sess_dir.exists()
        assert sess_dir.name == "test-abc"

    def test_write_continuation_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-abc")
        from cohezion_engine import session as sess_mod

        content = "# Continuation\n\nSome state here."
        path = sess_mod.write_continuation(content, base_dir=tmp_path)
        assert path.exists()
        assert path.read_text() == content

    def test_read_continuation_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-abc")
        from cohezion_engine import session as sess_mod

        content = "# My continuation"
        sess_mod.write_continuation(content, base_dir=tmp_path)
        result = sess_mod.read_continuation(base_dir=tmp_path)
        assert result == content

    def test_read_continuation_returns_none_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "no-such-session")
        from cohezion_engine import session as sess_mod

        result = sess_mod.read_continuation(base_dir=tmp_path)
        assert result is None

    def test_delete_continuation_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COHEZION_SESSION_ID", "test-abc")
        from cohezion_engine import session as sess_mod

        sess_mod.write_continuation("content", base_dir=tmp_path)
        sess_mod.delete_continuation(base_dir=tmp_path)
        assert sess_mod.read_continuation(base_dir=tmp_path) is None

    def test_cli_session_status_json(self):
        result = run_cz("session", "status", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "session_id" in data
        assert "session_dir" in data

    def test_cli_session_status_human(self):
        result = run_cz("session", "status")
        assert result.returncode == 0
        assert "session" in result.stdout.lower()
