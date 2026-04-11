"""Tests for VaultFileWatcher with debounce and fan-out."""

import asyncio
import time

import pytest

from mcp_server.vault_watcher import VaultEvent, VaultFileWatcher


@pytest.fixture
def vault_dir(tmp_path):
    """Create a temporary vault directory."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "decisions").mkdir()
    return tmp_path


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def watcher(vault_dir, event_loop):
    w = VaultFileWatcher(str(vault_dir), event_loop, debounce_seconds=0.1)
    w.start()
    yield w
    w.stop()


def _run(loop, coro):
    """Run a coroutine on the given loop from a sync context."""
    return loop.run_until_complete(coro)


class TestVaultEvent:
    def test_to_dict(self):
        event = VaultEvent(event_type="created", path="inbox/test.md")
        d = event.to_dict()
        assert d["event_type"] == "created"
        assert d["path"] == "inbox/test.md"
        assert "timestamp" in d
        assert d["old_path"] is None

    def test_to_dict_with_old_path(self):
        event = VaultEvent(
            event_type="moved", path="decisions/moved.md", old_path="inbox/test.md"
        )
        d = event.to_dict()
        assert d["event_type"] == "moved"
        assert d["old_path"] == "inbox/test.md"
        assert d["path"] == "decisions/moved.md"


class TestVaultFileWatcher:
    def test_create_event(self, watcher, vault_dir, event_loop):
        queue = watcher.subscribe()
        (vault_dir / "test.md").write_text("hello")
        event = _run(event_loop, asyncio.wait_for(queue.get(), timeout=3.0))
        assert event.event_type == "created"
        assert event.path == "test.md"

    def test_modify_event(self, watcher, vault_dir, event_loop):
        # Create first, then modify
        test_file = vault_dir / "modify-me.md"
        test_file.write_text("initial")
        # Wait for create event to pass debounce
        time.sleep(0.3)

        queue = watcher.subscribe()
        test_file.write_text("updated content")
        event = _run(event_loop, asyncio.wait_for(queue.get(), timeout=3.0))
        assert event.event_type == "modified"
        assert event.path == "modify-me.md"

    def test_delete_event(self, watcher, vault_dir, event_loop):
        test_file = vault_dir / "delete-me.md"
        test_file.write_text("to be deleted")
        time.sleep(0.3)

        queue = watcher.subscribe()
        test_file.unlink()
        event = _run(event_loop, asyncio.wait_for(queue.get(), timeout=3.0))
        assert event.event_type == "deleted"
        assert event.path == "delete-me.md"

    def test_debounce_rapid_modifications(self, watcher, vault_dir, event_loop):
        """Rapid modifications to the same file should produce only one event."""
        test_file = vault_dir / "rapid.md"
        test_file.write_text("v0")
        time.sleep(0.3)

        queue = watcher.subscribe()
        # Write rapidly many times
        for i in range(5):
            test_file.write_text(f"version {i}")
            time.sleep(0.02)

        # Wait for debounce to settle
        time.sleep(0.3)

        # Should get exactly one event (not five)
        event = _run(event_loop, asyncio.wait_for(queue.get(), timeout=3.0))
        assert event.event_type == "modified"
        assert event.path == "rapid.md"

        # Queue should be empty (no more events)
        assert queue.empty()

    def test_filter_obsidian_dir(self, watcher, vault_dir, event_loop):
        """Files in .obsidian/ should be ignored."""
        obsidian = vault_dir / ".obsidian"
        obsidian.mkdir(exist_ok=True)

        queue = watcher.subscribe()
        (obsidian / "workspace.md").write_text("obsidian config")
        time.sleep(0.3)

        assert queue.empty()

    def test_filter_git_dir(self, watcher, vault_dir, event_loop):
        """Files in .git/ should be ignored."""
        git_dir = vault_dir / ".git"
        git_dir.mkdir(exist_ok=True)

        queue = watcher.subscribe()
        (git_dir / "HEAD.md").write_text("ref: refs/heads/main")
        time.sleep(0.3)

        assert queue.empty()

    def test_filter_non_md_files(self, watcher, vault_dir, event_loop):
        """Non-.md files should be ignored."""
        queue = watcher.subscribe()
        (vault_dir / "image.png").write_bytes(b"\x89PNG")
        (vault_dir / "data.json").write_text("{}")
        time.sleep(0.3)

        assert queue.empty()

    def test_filter_template_files(self, watcher, vault_dir, event_loop):
        """_template.md files should be ignored."""
        queue = watcher.subscribe()
        (vault_dir / "_template.md").write_text("# Template")
        time.sleep(0.3)

        assert queue.empty()

    def test_fan_out_two_subscribers(self, watcher, vault_dir, event_loop):
        """Two subscribers should both receive the same event."""
        q1 = watcher.subscribe()
        q2 = watcher.subscribe()

        (vault_dir / "fanout.md").write_text("broadcast")

        e1 = _run(event_loop, asyncio.wait_for(q1.get(), timeout=3.0))
        e2 = _run(event_loop, asyncio.wait_for(q2.get(), timeout=3.0))

        assert e1.event_type == "created"
        assert e2.event_type == "created"
        assert e1.path == e2.path == "fanout.md"

    def test_unsubscribe(self, watcher, vault_dir, event_loop):
        """After unsubscribe, the queue should not receive events."""
        queue = watcher.subscribe()
        watcher.unsubscribe(queue)

        (vault_dir / "after-unsub.md").write_text("should not appear")
        time.sleep(0.3)

        assert queue.empty()

    def test_stop_no_more_events(self, vault_dir, event_loop):
        """After stop(), no more events should be delivered."""
        w = VaultFileWatcher(str(vault_dir), event_loop, debounce_seconds=0.1)
        w.start()
        queue = w.subscribe()
        w.stop()

        (vault_dir / "after-stop.md").write_text("should not appear")
        time.sleep(0.3)

        assert queue.empty()

    def test_subdirectory_event(self, watcher, vault_dir, event_loop):
        """Events in subdirectories should have correct vault-relative paths."""
        queue = watcher.subscribe()
        (vault_dir / "decisions" / "new-decision.md").write_text("# Decision")

        event = _run(event_loop, asyncio.wait_for(queue.get(), timeout=3.0))
        assert event.event_type == "created"
        assert event.path == "decisions/new-decision.md"

    def test_filter_hidden_directory(self, watcher, vault_dir, event_loop):
        """Files in any hidden (dot-prefixed) directory should be ignored."""
        hidden = vault_dir / ".hidden"
        hidden.mkdir()

        queue = watcher.subscribe()
        (hidden / "secret.md").write_text("hidden content")
        time.sleep(0.3)

        assert queue.empty()
