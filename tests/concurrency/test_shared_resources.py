"""Integration tests for thread-safe shared resource management."""

import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from cohezion.concurrency.shared_resources import (
    CapabilityUsageTracker,
    GitLabRunnerConfig,
    SkillRegistry,
)


@pytest.fixture
def temp_skill_registry():
    """Create temporary skill registry file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump({"skills": {}}, f)
        filepath = f.name
    yield filepath
    Path(filepath).unlink(missing_ok=True)


@pytest.fixture
def temp_usage_tracker():
    """Create temporary usage tracking file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump({"operations": {}}, f)
        filepath = f.name
    yield filepath
    Path(filepath).unlink(missing_ok=True)


class TestSkillRegistry:
    """Tests for SkillRegistry with file locking."""

    def test_register_skill(self, temp_skill_registry):
        """Test registering a skill."""
        registry = SkillRegistry(temp_skill_registry)

        skill_data = {
            "version": "1.0",
            "description": "Test skill",
            "domain": "test",
        }
        result = registry.register_skill("test_skill", skill_data)

        assert "skills" in result
        assert "test_skill" in result["skills"]
        assert result["skills"]["test_skill"]["version"] == "1.0"

    def test_get_skill(self, temp_skill_registry):
        """Test getting a skill."""
        registry = SkillRegistry(temp_skill_registry)

        skill_data = {"version": "1.0", "description": "Test skill"}
        registry.register_skill("my_skill", skill_data)

        retrieved = registry.get_skill("my_skill")
        assert retrieved is not None
        assert retrieved["version"] == "1.0"

    def test_get_all_skills(self, temp_skill_registry):
        """Test getting all skills."""
        registry = SkillRegistry(temp_skill_registry)

        registry.register_skill("skill1", {"version": "1.0"})
        registry.register_skill("skill2", {"version": "2.0"})

        all_skills = registry.get_all_skills()
        assert len(all_skills) == 2
        assert "skill1" in all_skills
        assert "skill2" in all_skills

    def test_update_skill_version(self, temp_skill_registry):
        """Test updating skill version."""
        registry = SkillRegistry(temp_skill_registry)

        registry.register_skill("my_skill", {"version": "1.0"})
        result = registry.update_skill_version("my_skill", "2.0")

        assert result["skills"]["my_skill"]["version"] == "2.0"

    def test_remove_skill(self, temp_skill_registry):
        """Test removing a skill."""
        registry = SkillRegistry(temp_skill_registry)

        registry.register_skill("skill1", {"version": "1.0"})
        registry.register_skill("skill2", {"version": "2.0"})

        result = registry.remove_skill("skill1")

        assert "skill1" not in result["skills"]
        assert "skill2" in result["skills"]

    def test_increment_skill_usage(self, temp_skill_registry):
        """Test incrementing usage counter."""
        registry = SkillRegistry(temp_skill_registry)

        registry.register_skill("my_skill", {"version": "1.0"})
        result = registry.increment_skill_usage("my_skill")

        assert result["skills"]["my_skill"]["usage_count"] == 1

        result = registry.increment_skill_usage("my_skill")
        assert result["skills"]["my_skill"]["usage_count"] == 2

    def test_concurrent_skill_registration(self, temp_skill_registry):
        """Test concurrent skill registration without data loss."""
        registry = SkillRegistry(temp_skill_registry)
        results = []

        def register_skill(skill_id):
            skill_data = {
                "version": "1.0",
                "description": f"Skill {skill_id}",
                "domain": "test",
            }
            result = registry.register_skill(f"skill_{skill_id}", skill_data)
            results.append(len(result["skills"]))

        # Register 5 skills concurrently
        threads = [
            threading.Thread(target=register_skill, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All skills should be registered
        all_skills = registry.get_all_skills()
        assert len(all_skills) == 5

        # All registrations should have succeeded (no lost updates)
        for i in range(5):
            assert f"skill_{i}" in all_skills

    def test_concurrent_usage_increment(self, temp_skill_registry):
        """Test concurrent usage counter increments."""
        registry = SkillRegistry(temp_skill_registry)
        registry.register_skill("my_skill", {"version": "1.0"})

        def increment_usage():
            for _ in range(10):
                registry.increment_skill_usage("my_skill")

        threads = [
            threading.Thread(target=increment_usage)
            for _ in range(3)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        final = registry.get_skill("my_skill")
        # Should be 3 threads * 10 increments = 30
        assert final["usage_count"] == 30


class TestCapabilityUsageTracker:
    """Tests for CapabilityUsageTracker with file locking."""

    def test_record_operation(self, temp_usage_tracker):
        """Test recording operation."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        result = tracker.record_operation(
            "generate",
            tokens_used=250,
            success=True,
        )

        assert "operations" in result
        assert "generate" in result["operations"]
        assert result["operations"]["generate"]["count"] == 1
        assert result["operations"]["generate"]["success_count"] == 1
        assert result["operations"]["generate"]["total_tokens"] == 250

    def test_record_failed_operation(self, temp_usage_tracker):
        """Test recording failed operation."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        result = tracker.record_operation(
            "analyze",
            tokens_used=100,
            success=False,
        )

        assert result["operations"]["analyze"]["count"] == 1
        assert result["operations"]["analyze"]["success_count"] == 0

    def test_get_operation_stats(self, temp_usage_tracker):
        """Test getting operation stats."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        tracker.record_operation("generate", tokens_used=250, success=True)
        tracker.record_operation("generate", tokens_used=300, success=True)

        stats = tracker.get_operation_stats("generate")
        assert stats["count"] == 2
        assert stats["total_tokens"] == 550
        assert stats["avg_tokens"] == 275.0

    def test_get_success_rate(self, temp_usage_tracker):
        """Test calculating success rate."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        tracker.record_operation("generate", tokens_used=100, success=True)
        tracker.record_operation("generate", tokens_used=100, success=True)
        tracker.record_operation("generate", tokens_used=100, success=False)

        success_rate = tracker.get_success_rate("generate")
        assert success_rate == pytest.approx(2.0 / 3.0)

    def test_get_average_tokens(self, temp_usage_tracker):
        """Test getting average tokens."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        tracker.record_operation("analyze", tokens_used=100, success=True)
        tracker.record_operation("analyze", tokens_used=200, success=True)
        tracker.record_operation("analyze", tokens_used=150, success=True)

        avg = tracker.get_average_tokens("analyze")
        assert avg == pytest.approx(150.0)

    def test_reset_operation_stats(self, temp_usage_tracker):
        """Test resetting operation stats."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        tracker.record_operation("search", tokens_used=100, success=True)
        tracker.record_operation("search", tokens_used=100, success=True)

        result = tracker.reset_operation_stats("search")
        assert "search" not in result["operations"]

    def test_concurrent_operation_recording(self, temp_usage_tracker):
        """Test concurrent operation recording without data loss."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        def record_operations(operation_type, count):
            for i in range(count):
                tracker.record_operation(
                    operation_type,
                    tokens_used=100 + i,
                    success=(i % 2 == 0),
                )

        # Record operations from 3 threads concurrently
        threads = [
            threading.Thread(target=record_operations, args=("generate", 10)),
            threading.Thread(target=record_operations, args=("analyze", 10)),
            threading.Thread(target=record_operations, args=("search", 10)),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All operations should be recorded
        all_stats = tracker.get_all_stats()
        assert len(all_stats) == 3

        for op_type in ["generate", "analyze", "search"]:
            assert all_stats[op_type]["count"] == 10

    def test_concurrent_increments_preserve_precision(self, temp_usage_tracker):
        """Test that concurrent increments maintain correct totals."""
        tracker = CapabilityUsageTracker(temp_usage_tracker)

        def record_operations():
            for i in range(20):
                tracker.record_operation(
                    "generate",
                    tokens_used=10,
                    success=True,
                )
                time.sleep(0.001)  # Small delay to increase contention

        threads = [
            threading.Thread(target=record_operations)
            for _ in range(5)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        stats = tracker.get_operation_stats("generate")
        # 5 threads * 20 operations * 10 tokens = 1000
        assert stats["total_tokens"] == 1000
        assert stats["count"] == 100


@pytest.mark.skip(
    reason="GitLab CI deprecated and replaced with GitHub Actions (Session 57). "
    "Tests preserved for historical reference. Will be removed 2026-08-13."
)
class TestGitLabRunnerConfig:
    """Tests for GitLab Runner configuration management.

    .. deprecated:: 2026-02-13
        These tests are skipped but preserved for historical reference.
        GitLab CI was replaced with GitHub Actions in Session 57.
        Tests will be removed in v2.0.0 (2026-08-13).
    """

    def test_add_runner(self):
        """Test adding a runner."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            filepath = f.name

        try:
            config = GitLabRunnerConfig(filepath)

            runner_data = {
                "name": "test-runner",
                "url": "http://localhost:8929",
                "token": "test-token",
            }
            result = config.add_runner(runner_data)

            assert "runners" in result
            assert len(result["runners"]) == 1
            assert result["runners"][0]["name"] == "test-runner"
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_update_runner(self):
        """Test updating runner configuration."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            filepath = f.name

        try:
            config = GitLabRunnerConfig(filepath)

            config.add_runner({
                "name": "my-runner",
                "url": "http://localhost:8929",
            })

            result = config.update_runner("my-runner", {"token": "new-token"})

            runner = result["runners"][0]
            assert runner["token"] == "new-token"
            assert runner["url"] == "http://localhost:8929"
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_remove_runner(self):
        """Test removing a runner."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            filepath = f.name

        try:
            config = GitLabRunnerConfig(filepath)

            config.add_runner({"name": "runner1", "url": "http://localhost:8929"})
            config.add_runner({"name": "runner2", "url": "http://localhost:8930"})

            result = config.remove_runner("runner1")

            assert len(result["runners"]) == 1
            assert result["runners"][0]["name"] == "runner2"
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_concurrent_runner_config_updates(self):
        """Test concurrent runner config updates."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            filepath = f.name

        try:
            config = GitLabRunnerConfig(filepath)

            def add_runners(thread_id):
                for i in range(3):
                    config.add_runner({
                        "name": f"runner-{thread_id}-{i}",
                        "url": f"http://localhost:{9000 + thread_id * 10 + i}",
                    })

            threads = [
                threading.Thread(target=add_runners, args=(i,))
                for i in range(3)
            ]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            result = config.read_config()
            # 3 threads * 3 runners = 9
            assert len(result.get("runners", [])) == 9
        finally:
            Path(filepath).unlink(missing_ok=True)
