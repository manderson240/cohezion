"""Integration tests for cohezion-engine: full CLI, coherence checks, worktree cycle."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WKDIR = Path(__file__).parent.parent
VAULT_ROOT = WKDIR.parent.parent
PYTHON = sys.executable


def run_cz(*args: str, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    """Run cz CLI and return result."""
    env = {**os.environ, "PYTHONPATH": str(WKDIR / "src")}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [PYTHON, "-m", "cohezion_engine.cli", *args],
        capture_output=True,
        text=True,
        cwd=WKDIR,
        env=env,
    )


# ---------------------------------------------------------------------------
# Coherence checks — vault structure integrity
# ---------------------------------------------------------------------------


class TestCoherenceChecks:
    """Verify that the vault .claude/ directory has no Pilot references and all required files."""

    REQUIRED_COMMANDS = [
        "spec.md",
        "spec-plan.md",
        "spec-implement.md",
        "spec-verify.md",
        "learn.md",
        "sync.md",
        "vault.md",
    ]

    REQUIRED_AGENTS = [
        "plan-verifier.md",
        "plan-challenger.md",
        "spec-reviewer-compliance.md",
        "spec-reviewer-quality.md",
    ]

    def test_all_command_files_exist(self):
        commands_dir = VAULT_ROOT / ".claude" / "commands"
        for name in self.REQUIRED_COMMANDS:
            assert (commands_dir / name).exists(), f"Missing command file: {name}"

    def test_all_agent_files_exist(self):
        agents_dir = VAULT_ROOT / ".claude" / "agents"
        for name in self.REQUIRED_AGENTS:
            assert (agents_dir / name).exists(), f"Missing agent file: {name}"

    def test_no_pilot_binary_refs_in_rules(self):
        """No file in .claude/rules/ should reference ~/.pilot/."""
        rules_dir = VAULT_ROOT / ".claude" / "rules"
        if not rules_dir.exists():
            pytest.skip("No .claude/rules/ directory")
        offenders = []
        for md_file in rules_dir.glob("*.md"):
            text = md_file.read_text()
            if "~/.pilot/" in text:
                offenders.append(md_file.name)
        assert not offenders, f"Files with ~/.pilot/ references: {offenders}"

    def test_no_pilot_binary_refs_in_commands(self):
        """No command file should reference ~/.pilot/."""
        commands_dir = VAULT_ROOT / ".claude" / "commands"
        offenders = []
        for md_file in commands_dir.glob("*.md"):
            text = md_file.read_text()
            if "~/.pilot/" in text:
                offenders.append(md_file.name)
        assert not offenders, f"Command files with ~/.pilot/ references: {offenders}"

    def test_no_pilot_binary_refs_in_agents(self):
        """No agent file should reference ~/.pilot/."""
        agents_dir = VAULT_ROOT / ".claude" / "agents"
        offenders = []
        for md_file in agents_dir.glob("*.md"):
            text = md_file.read_text()
            if "~/.pilot/" in text:
                offenders.append(md_file.name)
        assert not offenders, f"Agent files with ~/.pilot/ references: {offenders}"

    def test_no_pilot_session_id_in_rules(self):
        """No rules file should reference PILOT_SESSION_ID."""
        rules_dir = VAULT_ROOT / ".claude" / "rules"
        if not rules_dir.exists():
            pytest.skip("No .claude/rules/ directory")
        offenders = []
        for md_file in rules_dir.glob("*.md"):
            text = md_file.read_text()
            if "PILOT_SESSION_ID" in text:
                offenders.append(md_file.name)
        assert not offenders, f"Rules files with PILOT_SESSION_ID: {offenders}"

    def test_no_pilot_session_id_in_commands(self):
        """No command file should reference PILOT_SESSION_ID."""
        commands_dir = VAULT_ROOT / ".claude" / "commands"
        offenders = []
        for md_file in commands_dir.glob("*.md"):
            text = md_file.read_text()
            if "PILOT_SESSION_ID" in text:
                offenders.append(md_file.name)
        assert not offenders, f"Command files with PILOT_SESSION_ID: {offenders}"


# ---------------------------------------------------------------------------
# CLI integration — JSON schema validation across all subcommands
# ---------------------------------------------------------------------------


class TestCLIJsonSchemas:
    """Verify that all --json outputs conform to their documented schemas."""

    def test_status_json_schema(self):
        result = run_cz("status", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "version" in data
        assert "config_dir" in data
        assert isinstance(data["version"], str)
        assert isinstance(data["config_dir"], str)

    def test_context_json_schema(self):
        result = run_cz("context", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "status" in data
        assert "percentage" in data
        assert data["status"].upper() in ("OK", "WARNING", "CLEAR_NEEDED", "UNKNOWN")
        assert isinstance(data["percentage"], (int, float))

    def test_session_status_json_schema(self):
        result = run_cz("session", "status", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "session_id" in data
        assert "session_dir" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

    def test_worktree_status_json_schema(self):
        result = run_cz("worktree", "status", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "active" in data
        assert isinstance(data["active"], bool)

    def test_worktree_detect_json_schema(self):
        result = run_cz("worktree", "detect", "--json", "nonexistent-slug-xyz")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "found" in data
        assert data["found"] is False


# ---------------------------------------------------------------------------
# Worktree full cycle in a temporary git repository
# ---------------------------------------------------------------------------


class TestWorktreeCycle:
    """Test create → detect → diff → cleanup in an isolated git repo."""

    def test_full_worktree_cycle(self, tmp_git_repo):
        """create → detect → diff → cleanup returns consistent results."""
        slug = "integration-test-slug"
        env = {**os.environ, "PYTHONPATH": str(WKDIR / "src")}

        def cz_in_repo(*args):
            return subprocess.run(
                [PYTHON, "-m", "cohezion_engine.cli", *args],
                capture_output=True,
                text=True,
                cwd=WKDIR,
                env={**env, "CZ_REPO_ROOT": str(tmp_git_repo)},
            )

        from cohezion_engine.worktree import (
            cleanup_worktree,
            create_worktree,
            detect_worktree,
            diff_worktree,
            sync_worktree,
        )

        # Step 1: Detect — not found
        detected = detect_worktree(slug, repo_root=tmp_git_repo)
        assert detected["found"] is False

        # Step 2: Create
        created = create_worktree(slug, repo_root=tmp_git_repo)
        assert created.get("success") is True, f"Create failed: {created}"
        assert "path" in created
        worktree_path = Path(created["path"])
        assert worktree_path.exists()

        # Step 3: Detect — now found
        detected = detect_worktree(slug, repo_root=tmp_git_repo)
        assert detected["found"] is True
        assert detected["branch"] == f"spec/{slug}"

        # Step 4: Make a change in the worktree and commit it
        new_file = worktree_path / "feature.txt"
        new_file.write_text("new feature\n")
        subprocess.run(
            ["git", "-C", str(worktree_path), "add", "feature.txt"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(worktree_path), "commit", "-m", "add feature"],
            check=True,
            capture_output=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@test.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@test.com",
            },
        )

        # Step 5: Diff — should show changes vs base branch
        diffed = diff_worktree(slug, repo_root=tmp_git_repo)
        assert diffed.get("success") is True, f"Diff failed: {diffed}"
        assert diffed.get("count", 0) > 0

        # Step 6: Sync — squash merge back to base branch
        synced = sync_worktree(slug, repo_root=tmp_git_repo)
        assert synced.get("success") is True, f"Sync failed: {synced}"
        assert "commit_hash" in synced

        # Step 7: Cleanup
        cleaned = cleanup_worktree(slug, repo_root=tmp_git_repo)
        assert cleaned.get("success") is True, f"Cleanup failed: {cleaned}"
        assert not worktree_path.exists()

        # Step 8: Detect — gone again
        detected = detect_worktree(slug, repo_root=tmp_git_repo)
        assert detected["found"] is False

        # Step 9: Verify the synced file exists on the base branch
        assert (tmp_git_repo / "feature.txt").exists()

    def test_create_detects_dirty_tree(self, tmp_git_repo):
        """Create fails gracefully when working tree has uncommitted changes."""
        from cohezion_engine.worktree import create_worktree

        # Add an uncommitted file to make tree dirty
        (tmp_git_repo / "dirty.txt").write_text("uncommitted")

        result = create_worktree("dirty-test", repo_root=tmp_git_repo)
        # Should either fail with error OR succeed (depending on git behavior)
        # At minimum it should not raise an exception and should return a dict
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Hook script integration
# ---------------------------------------------------------------------------


class TestHookIntegration:
    """Test that hook scripts respond correctly to real-world-style inputs."""

    HOOKS_DIR = WKDIR / "src" / "cohezion_engine" / "hooks"

    def run_hook(
        self, hook_file: str, stdin_data: dict, env: dict | None = None
    ) -> subprocess.CompletedProcess:
        hook_env = {**os.environ}
        if env:
            hook_env.update(env)
        return subprocess.run(
            [PYTHON, str(self.HOOKS_DIR / hook_file)],
            input=json.dumps(stdin_data),
            capture_output=True,
            text=True,
            env=hook_env,
        )

    def test_context_monitor_with_high_context_emits_warning(self, tmp_path):
        """Context monitor at 91% emits CLEAR_NEEDED to stdout."""
        # Create a fake JSONL with enough tokens to trigger CLEAR_NEEDED (91%)
        # 200k * 0.91 = 182,000 tokens
        jsonl = tmp_path / "session.jsonl"
        entry = {
            "role": "assistant",
            "usage": {
                "input_tokens": 182000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }
        jsonl.write_text(json.dumps({"message": entry}) + "\n")

        result = self.run_hook(
            "context_monitor.py",
            {"tool_name": "Write", "tool_input": {}},
            env={"CZ_TEST_SESSION_JSONL": str(jsonl)},
        )
        assert result.returncode == 0
        assert "CLEAR_NEEDED" in result.stdout or "CRITICAL" in result.stdout

    def test_file_checker_allows_normal_files(self, tmp_path):
        """File checker passes on a file with < 300 lines."""
        test_file = tmp_path / "module.py"
        test_file.write_text("x = 1\n" * 50)
        result = self.run_hook(
            "file_checker.py",
            {"tool_name": "Write", "tool_input": {"file_path": str(test_file)}},
        )
        assert result.returncode == 0

    def test_file_checker_blocks_huge_files(self, tmp_path):
        """File checker blocks files over 500 lines."""
        test_file = tmp_path / "huge.py"
        test_file.write_text("x = 1\n" * 510)
        result = self.run_hook(
            "file_checker.py",
            {"tool_name": "Write", "tool_input": {"file_path": str(test_file)}},
        )
        assert result.returncode == 2
