"""Comprehensive tests for IsolationPrimitives (PRIME Skill #2).

Tests cover:
1. Filesystem snapshot creation/destruction
2. Namespace setup verification
3. Mount point validation
4. Change tracking accuracy
5. Network isolation
6. Cleanup verification
7. Symlink handling
8. Large directory support (>1GB simulation)
9. Edge cases (hard links, sparse files)
10. Complete lifecycle
"""

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


_IN_CI = os.environ.get("CI") == "true"


def _cleanup_dir(path: str) -> None:
    """Unmount any overlay filesystems under path, then remove it.

    Necessary because OverlayFS mounts leave the 'merged' directory busy
    and shutil.rmtree raises OSError: [Errno 16] Device or resource busy.
    """
    if not os.path.exists(path):
        return
    # Unmount any submounts (reverse order so children unmount before parents)
    findmnt_cmd = shutil.which("findmnt") or "findmnt"
    umount_cmd = shutil.which("umount") or "umount"
    result = subprocess.run(
        [findmnt_cmd, "--raw", "--noheadings", "-o", "TARGET", "--submounts", path],
        capture_output=True,
        text=True,
        shell=False,
    )
    for mount_point in reversed(result.stdout.strip().split("\n")):
        if mount_point.strip():
            subprocess.run([umount_cmd, mount_point.strip()], capture_output=True, shell=False)
    shutil.rmtree(path, ignore_errors=True)


_CI_SKIP_REASON = "OverlayFS requires CAP_SYS_ADMIN — unavailable in CI containers"

from cohezion.sandbox.isolation import (
    ChangeType,
    CleanupRegistry,
    CleanupResult,
    FilesystemIsolation,
    IsolationConfig,
    IsolationContext,
    IsolationManager,
    IsolationStatus,
    NetworkIsolation,
    ProcessIsolation,
    get_isolation_manager,
)


@unittest.skipIf(_IN_CI, _CI_SKIP_REASON)
class TestFilesystemIsolation(unittest.TestCase):
    """Test filesystem isolation functionality."""

    def setUp(self):
        """Setup test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.fs_isolation = FilesystemIsolation(self.test_dir)

    def tearDown(self):
        """Cleanup test artifacts."""
        _cleanup_dir(self.test_dir)

    def test_setup_overlay_filesystem(self):
        """Test overlay filesystem setup creation."""
        # Create a source directory with test files
        source_dir = os.path.join(self.test_dir, "source")
        os.makedirs(source_dir)
        test_file = os.path.join(source_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Setup overlay
        isolation_id = "test-iso-001"
        merged_path, _mounts = self.fs_isolation.setup_cow_filesystem(
            isolation_id, source_dir, backend="overlay"
        )

        # Verify merged path exists
        self.assertTrue(os.path.exists(merged_path))

        # Verify structure
        isolation_dir = Path(self.test_dir) / f"isolation-{isolation_id}"
        self.assertTrue((isolation_dir / "lower").exists())
        self.assertTrue((isolation_dir / "upper").exists())
        self.assertTrue((isolation_dir / "work").exists())
        self.assertTrue((isolation_dir / "merged").exists())

    def test_setup_rsync_fallback(self):
        """Test rsync fallback filesystem setup."""
        source_dir = os.path.join(self.test_dir, "source_rsync")
        os.makedirs(source_dir)
        test_file = os.path.join(source_dir, "file.txt")
        with open(test_file, "w") as f:
            f.write("rsync test")

        # Setup rsync
        isolation_id = "test-iso-rsync"
        merged_path, _mounts = self.fs_isolation.setup_cow_filesystem(
            isolation_id, source_dir, backend="rsync"
        )

        # Verify copy exists
        self.assertTrue(os.path.exists(merged_path))
        copied_file = os.path.join(merged_path, "file.txt")
        self.assertTrue(os.path.exists(copied_file))

    def test_copy_tree_efficient(self):
        """Test efficient directory tree copying."""
        src_dir = os.path.join(self.test_dir, "src_tree")
        dst_dir = os.path.join(self.test_dir, "dst_tree")
        os.makedirs(src_dir)

        # Create test structure
        os.makedirs(os.path.join(src_dir, "subdir"))
        with open(os.path.join(src_dir, "file1.txt"), "w") as f:
            f.write("content1")
        with open(os.path.join(src_dir, "subdir", "file2.txt"), "w") as f:
            f.write("content2")

        # Copy
        self.fs_isolation._copy_tree_efficient(src_dir, dst_dir)

        # Verify copy
        self.assertTrue(os.path.exists(os.path.join(dst_dir, "file1.txt")))
        self.assertTrue(os.path.exists(os.path.join(dst_dir, "subdir", "file2.txt")))

    def test_track_changes_created(self):
        """Test tracking of newly created files."""
        source_dir = os.path.join(self.test_dir, "source_change")
        os.makedirs(source_dir)

        # Setup isolation
        isolation_id = "test-iso-changes"
        merged_path, mounts = self.fs_isolation.setup_cow_filesystem(
            isolation_id, source_dir, backend="rsync"
        )

        # Create new file in merged path
        new_file = os.path.join(merged_path, "new.txt")
        with open(new_file, "w") as f:
            f.write("new file")

        # Create isolation context
        context = IsolationContext(
            isolation_id=isolation_id,
            root_path=merged_path,
            base_path=source_dir,
            config=IsolationConfig(),
            mounts=mounts,
        )

        # Track changes
        changes = self.fs_isolation.track_changes(context)

        # Verify change detected
        self.assertGreater(len(changes), 0)
        change_types = [c.change_type for c in changes]
        self.assertIn(ChangeType.CREATED, change_types)

    def test_track_changes_deletion(self):
        """Test tracking of deleted files."""
        source_dir = os.path.join(self.test_dir, "source_delete")
        os.makedirs(source_dir)

        # Create initial file
        original_file = os.path.join(source_dir, "original.txt")
        with open(original_file, "w") as f:
            f.write("original")

        # Setup isolation
        isolation_id = "test-iso-delete"
        merged_path, mounts = self.fs_isolation.setup_cow_filesystem(
            isolation_id, source_dir, backend="rsync"
        )

        # Delete file in merged
        merged_file = os.path.join(merged_path, "original.txt")
        if os.path.exists(merged_file):
            os.remove(merged_file)

        # Create isolation context
        context = IsolationContext(
            isolation_id=isolation_id,
            root_path=merged_path,
            base_path=source_dir,
            config=IsolationConfig(),
            mounts=mounts,
        )

        # Track changes
        changes = self.fs_isolation.track_changes(context)

        # Verify deletion detected
        change_types = [c.change_type for c in changes]
        self.assertIn(ChangeType.DELETED, change_types)

    def test_large_directory_support(self):
        """Test handling of large directories (simulated)."""
        source_dir = os.path.join(self.test_dir, "source_large")
        os.makedirs(source_dir)

        # Create "large" directory structure (not truly 1GB, but enough files)
        for i in range(100):
            file_path = os.path.join(source_dir, f"file_{i:04d}.txt")
            with open(file_path, "w") as f:
                f.write(f"content {i}" * 100)  # ~1KB per file

        # Setup isolation
        isolation_id = "test-iso-large"
        start_time = time.time()
        merged_path, _mounts = self.fs_isolation.setup_cow_filesystem(
            isolation_id, source_dir, backend="overlay"
        )
        duration = time.time() - start_time

        # Verify successful setup
        self.assertTrue(os.path.exists(merged_path))
        # Should be relatively fast (overlay is CoW, not copy)
        self.assertLess(duration, 5.0)

    def test_symlink_handling(self):
        """Test proper handling of symbolic links."""
        source_dir = os.path.join(self.test_dir, "source_symlink")
        os.makedirs(source_dir)

        # Create target and symlink
        target_file = os.path.join(source_dir, "target.txt")
        with open(target_file, "w") as f:
            f.write("target content")

        link_file = os.path.join(source_dir, "link.txt")
        os.symlink(target_file, link_file)

        # Setup isolation
        isolation_id = "test-iso-symlink"
        merged_path, _mounts = self.fs_isolation.setup_cow_filesystem(
            isolation_id, source_dir, backend="rsync"
        )

        # Verify symlink preserved or resolved
        merged_link = os.path.join(merged_path, "link.txt")
        self.assertTrue(os.path.exists(merged_link))


@unittest.skipIf(_IN_CI, _CI_SKIP_REASON)
class TestProcessIsolation(unittest.TestCase):
    """Test process namespace isolation."""

    def test_setup_process_namespace(self):
        """Test process namespace setup."""
        config = IsolationConfig()
        context = IsolationContext(
            isolation_id="test-ns-001",
            root_path="/tmp/test",
            base_path="/tmp",
            config=config,
        )

        # Setup namespace
        namespace_id = ProcessIsolation.setup_process_namespace(context)

        # Verify namespace ID
        self.assertIsNotNone(namespace_id)
        self.assertIn("ns-", namespace_id)
        self.assertEqual(context.process_namespace_id, namespace_id)

    def test_verify_process_isolation(self):
        """Test process isolation verification."""
        namespace_id = "ns-test-verify"

        # Verify isolation check works
        result = ProcessIsolation.verify_process_isolation(namespace_id)

        # Should return bool
        self.assertIsInstance(result, bool)


@unittest.skipIf(_IN_CI, _CI_SKIP_REASON)
class TestNetworkIsolation(unittest.TestCase):
    """Test network isolation functionality."""

    def test_setup_network_isolation_no_external(self):
        """Test network isolation with external access blocked."""
        config = IsolationConfig(allow_network=True)
        context = IsolationContext(
            isolation_id="test-net-001",
            root_path="/tmp/test",
            base_path="/tmp",
            config=config,
        )

        # Setup network (mocked)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            network_ns = NetworkIsolation.setup_network_isolation(context, allow_external=False)

            # Verify network namespace created
            self.assertIsNotNone(network_ns)
            self.assertFalse(network_ns.allow_external)
            self.assertIn("veth", network_ns.veth_host)
            self.assertIn("br_", network_ns.bridge_name)

    def test_setup_network_isolation_allow_external(self):
        """Test network isolation with external access allowed."""
        config = IsolationConfig(allow_network=True)
        context = IsolationContext(
            isolation_id="test-net-002",
            root_path="/tmp/test",
            base_path="/tmp",
            config=config,
        )

        # Setup network (mocked)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            network_ns = NetworkIsolation.setup_network_isolation(context, allow_external=True)

            # Verify external access allowed
            self.assertIsNotNone(network_ns)
            self.assertTrue(network_ns.allow_external)


@unittest.skipIf(_IN_CI, _CI_SKIP_REASON)
class TestCleanupRegistry(unittest.TestCase):
    """Test cleanup registry functionality."""

    def test_register_and_cleanup(self):
        """Test registering and executing cleanup handlers."""
        registry = CleanupRegistry()
        isolation_id = "test-cleanup-001"

        # Create mock handler
        handler = Mock()

        # Register handler
        registry.register(isolation_id, handler)

        # Execute cleanup
        results = registry.cleanup_all(isolation_id)

        # Verify handler called
        handler.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][1])  # Success flag

    def test_multiple_handlers(self):
        """Test multiple cleanup handlers."""
        registry = CleanupRegistry()
        isolation_id = "test-cleanup-multi"

        # Create multiple handlers
        handler1 = Mock()
        handler2 = Mock()

        # Register handlers
        registry.register(isolation_id, handler1)
        registry.register(isolation_id, handler2)

        # Execute cleanup
        results = registry.cleanup_all(isolation_id)

        # Verify both handlers called
        handler1.assert_called_once()
        handler2.assert_called_once()
        self.assertEqual(len(results), 2)

    def test_handler_exception(self):
        """Test cleanup with handler exceptions."""
        registry = CleanupRegistry()
        isolation_id = "test-cleanup-exc"

        # Create handler that raises
        handler = Mock(side_effect=Exception("Test error"))

        # Register handler
        registry.register(isolation_id, handler)

        # Execute cleanup (should not raise)
        results = registry.cleanup_all(isolation_id)

        # Verify failure recorded
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0][1])  # Success flag is False

    def test_verify_cleanup(self):
        """Test cleanup verification."""
        registry = CleanupRegistry()
        config = IsolationConfig()
        context = IsolationContext(
            isolation_id="test-verify-clean",
            root_path="/tmp/test",
            base_path="/tmp",
            config=config,
            temp_dirs=[],
        )

        # Verify cleanup succeeds when no artifacts
        is_clean, remaining = registry.verify_cleanup(context)
        self.assertTrue(is_clean)
        self.assertEqual(len(remaining), 0)


@unittest.skipIf(_IN_CI, _CI_SKIP_REASON)
class TestIsolationManager(unittest.TestCase):
    """Test IsolationManager orchestration."""

    def setUp(self):
        """Setup test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.manager = IsolationManager(self.test_dir)

    def tearDown(self):
        """Cleanup test artifacts."""
        _cleanup_dir(self.test_dir)

    def test_setup_filesystem(self):
        """Test filesystem isolation setup."""
        source_dir = os.path.join(self.test_dir, "source")
        os.makedirs(source_dir)

        # Setup isolation
        context = self.manager.setup_filesystem(source_dir, snapshot_backend="overlay")

        # Verify context
        self.assertIsNotNone(context)
        self.assertEqual(context.status, IsolationStatus.ACTIVE)
        self.assertTrue(os.path.exists(context.root_path))
        # Overlay may fallback without root privileges, but isolation should still work
        self.assertIsNotNone(context.root_path)

    def test_setup_process_namespace(self):
        """Test process namespace setup."""
        source_dir = os.path.join(self.test_dir, "source_ns")
        os.makedirs(source_dir)

        # Setup filesystem first
        context = self.manager.setup_filesystem(source_dir)

        # Setup process namespace
        namespace_id = self.manager.setup_process_namespace(context)

        # Verify namespace
        self.assertIsNotNone(namespace_id)
        self.assertEqual(context.process_namespace_id, namespace_id)

    def test_setup_network(self):
        """Test network isolation setup."""
        source_dir = os.path.join(self.test_dir, "source_net")
        os.makedirs(source_dir)

        # Setup filesystem first
        context = self.manager.setup_filesystem(source_dir)

        # Setup network (mocked)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            network_ns = self.manager.setup_network(context, allow_external=False)

            # Verify network
            self.assertIsNotNone(network_ns)
            self.assertIsNotNone(context.network_namespace)

    def test_get_changes(self):
        """Test getting changes from isolation."""
        source_dir = os.path.join(self.test_dir, "source_changes")
        os.makedirs(source_dir)

        # Create initial file
        with open(os.path.join(source_dir, "initial.txt"), "w") as f:
            f.write("initial")

        # Setup isolation
        context = self.manager.setup_filesystem(source_dir, snapshot_backend="rsync")

        # Create change in isolation
        new_file = os.path.join(context.root_path, "new.txt")
        with open(new_file, "w") as f:
            f.write("new")

        # Get changes
        changes = self.manager.get_changes(context)

        # Verify changes recorded
        self.assertGreater(len(changes), 0)

    def test_cleanup_success(self):
        """Test successful cleanup."""
        source_dir = os.path.join(self.test_dir, "source_cleanup")
        os.makedirs(source_dir)

        # Setup isolation
        context = self.manager.setup_filesystem(source_dir, snapshot_backend="overlay")

        # Cleanup with mocking for subprocess calls.
        # umount → returncode=0 (success), findmnt → returncode=1 (mount gone).
        def _side_effect(cmd, **kwargs):
            if isinstance(cmd, list) and "findmnt" in cmd:
                return MagicMock(returncode=1)  # mount not found = cleaned up
            return MagicMock(returncode=0)  # umount and others succeed

        with patch("subprocess.run", side_effect=_side_effect):
            result = self.manager.cleanup(context)

            # Verify cleanup
            self.assertIsInstance(result, CleanupResult)
            self.assertEqual(context.status, IsolationStatus.CLEANED)

    def test_isolation_context_created(self):
        """Test isolation context is properly tracked."""
        source_dir = os.path.join(self.test_dir, "source_track")
        os.makedirs(source_dir)

        # Setup isolation
        context = self.manager.setup_filesystem(source_dir)

        # Verify context in manager
        self.assertIn(context.isolation_id, self.manager.contexts)

        # Cleanup
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            self.manager.cleanup(context)

        # Verify context removed
        self.assertNotIn(context.isolation_id, self.manager.contexts)


@unittest.skipIf(_IN_CI, _CI_SKIP_REASON)
class TestIsolationLifecycle(unittest.TestCase):
    """Test complete isolation lifecycle."""

    def setUp(self):
        """Setup test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.manager = IsolationManager(self.test_dir)

    def tearDown(self):
        """Cleanup test artifacts."""
        _cleanup_dir(self.test_dir)

    def test_complete_lifecycle(self):
        """Test complete isolation lifecycle."""
        source_dir = os.path.join(self.test_dir, "source_full")
        os.makedirs(source_dir)

        # Create initial state
        with open(os.path.join(source_dir, "original.txt"), "w") as f:
            f.write("original content")

        # 1. Setup filesystem
        context = self.manager.setup_filesystem(source_dir, snapshot_backend="rsync")
        self.assertEqual(context.status, IsolationStatus.ACTIVE)

        # 2. Setup process namespace
        ns_id = self.manager.setup_process_namespace(context)
        self.assertIsNotNone(ns_id)

        # 3. Make changes
        with open(os.path.join(context.root_path, "new.txt"), "w") as f:
            f.write("new content")

        # 4. Track changes
        changes = self.manager.get_changes(context)
        self.assertGreater(len(changes), 0)

        # 5. Cleanup
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = self.manager.cleanup(context)

        # Verify final state
        self.assertTrue(result.success)
        self.assertEqual(context.status, IsolationStatus.CLEANED)

    def test_isolation_idempotency(self):
        """Test isolation is idempotent."""
        source_dir = os.path.join(self.test_dir, "source_idem")
        os.makedirs(source_dir)

        # Setup twice
        context1 = self.manager.setup_filesystem(source_dir)
        context2 = self.manager.setup_filesystem(source_dir)

        # Verify different isolations
        self.assertNotEqual(context1.isolation_id, context2.isolation_id)

        # Cleanup both — findmnt must return 1 (not found) or cleanup reports failure
        def _side_effect(cmd, **kwargs):
            if isinstance(cmd, list) and "findmnt" in cmd:
                return MagicMock(returncode=1)  # mount gone = clean
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=_side_effect):
            result1 = self.manager.cleanup(context1)
            result2 = self.manager.cleanup(context2)

        self.assertTrue(result1.success)
        self.assertTrue(result2.success)


@unittest.skipIf(_IN_CI, _CI_SKIP_REASON)
class TestGetIsolationManager(unittest.TestCase):
    """Test factory function."""

    def test_singleton_instance(self):
        """Test singleton pattern."""
        manager1 = get_isolation_manager()
        manager2 = get_isolation_manager()

        # Should be same instance
        self.assertIs(manager1, manager2)

    def test_factory_custom_path(self):
        """Test factory with custom path."""
        test_dir = tempfile.mkdtemp()

        try:
            # Create new manager with custom path
            manager = IsolationManager(test_dir)

            # Verify base path
            self.assertEqual(str(manager.filesystem.base_path), test_dir)

        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)


# Pytest markers
pytestmark = [pytest.mark.unit, pytest.mark.sandbox]


if __name__ == "__main__":
    unittest.main()
