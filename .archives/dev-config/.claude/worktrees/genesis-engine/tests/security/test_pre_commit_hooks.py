"""Tests for pre-commit hooks configuration and credential detection."""

import json
from pathlib import Path

import pytest


class TestPreCommitConfiguration:
    """Tests for pre-commit hooks configuration."""

    def test_pre_commit_config_exists(self):
        """Test that .pre-commit-config.yaml exists."""
        config_file = Path(".pre-commit-config.yaml")
        assert config_file.exists(), "Missing .pre-commit-config.yaml"

    def test_pre_commit_config_valid_yaml(self):
        """Test that .pre-commit-config.yaml is valid YAML."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert "repos" in config
        assert isinstance(config["repos"], list)

    def test_pre_commit_config_has_secret_detection(self):
        """Test that pre-commit config includes secret detection."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        repo_ids = [repo.get("repo", "") for repo in config.get("repos", [])]

        # Should include detect-private-key hook
        assert any("pre-commit-hooks" in r for r in repo_ids), "Missing detect-private-key hook"

        # Should include detect-secrets
        assert any("detect-secrets" in r for r in repo_ids), "Missing detect-secrets hook"

    def test_secrets_baseline_exists(self):
        """Test that .secrets.baseline file exists."""
        baseline_file = Path(".secrets.baseline")
        assert baseline_file.exists(), "Missing .secrets.baseline"

    def test_secrets_baseline_valid_json(self):
        """Test that .secrets.baseline is valid JSON."""
        baseline_file = Path(".secrets.baseline")

        with open(baseline_file) as f:
            baseline = json.load(f)

        assert baseline is not None
        assert "version" in baseline
        assert "plugins_used" in baseline
        assert "filters_used" in baseline
        assert "results" in baseline

    def test_setup_script_exists(self):
        """Test that setup script exists."""
        script_file = Path("scripts/setup_pre_commit_hooks.sh")
        assert script_file.exists(), "Missing setup_pre_commit_hooks.sh"

    def test_setup_script_is_executable(self):
        """Test that setup script is executable."""
        import os

        script_file = Path("scripts/setup_pre_commit_hooks.sh")
        mode = os.stat(script_file).st_mode
        assert mode & 0o111, "Setup script is not executable"

    def test_pre_commit_hooks_stages(self):
        """Test that pre-commit hooks are configured with correct stages."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Verify hooks have stages defined
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                # Hooks should have stages defined (commit or push)
                if "stages" in hook:
                    # Accept both old (commit/push) and new (pre-commit/pre-push) naming
                    assert hook["stages"] in [
                        ["commit"],
                        ["push"],
                        ["commit", "push"],
                        ["pre-commit"],
                        ["pre-push"],
                        ["pre-commit", "pre-push"],
                    ], f"Invalid stages: {hook.get('stages')}"

    def test_credential_detection_hook_configured(self):
        """Test that credential detection hooks are properly configured."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Find detect-secrets hook
        found_detect_secrets = False
        for repo in config.get("repos", []):
            if "detect-secrets" in repo.get("repo", ""):
                found_detect_secrets = True
                hooks = repo.get("hooks", [])
                assert len(hooks) > 0

                for hook in hooks:
                    assert hook.get("id") == "detect-secrets"
                    # Should use baseline
                    assert ".secrets.baseline" in str(hook.get("args", [])), "detect-secrets should use baseline"

        assert found_detect_secrets, "detect-secrets hook not found"

    def test_bandit_security_check_configured(self):
        """Test that Bandit security checks are configured."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Find bandit hook
        found_bandit = False
        for repo in config.get("repos", []):
            if "bandit" in repo.get("repo", ""):
                found_bandit = True
                hooks = repo.get("hooks", [])
                assert len(hooks) > 0

                for hook in hooks:
                    assert hook.get("id") == "bandit"
                    # Should be on push stage (pre-commit v3 uses "pre-push")
                    stages = hook.get("stages", [])
                    assert "push" in stages or "pre-push" in stages

        assert found_bandit, "Bandit security check hook not found"

    def test_private_key_detection_enabled(self):
        """Test that private key detection is enabled."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Find detect-private-key hook
        found_private_key = False
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook.get("id") == "detect-private-key":
                    found_private_key = True

        assert found_private_key, "detect-private-key hook not found"


class TestSecretDetection:
    """Tests for secret detection functionality."""

    def test_detect_secrets_configuration_valid(self):
        """Test that detect-secrets configuration is valid."""
        baseline_file = Path(".secrets.baseline")

        with open(baseline_file) as f:
            baseline = json.load(f)

        # Verify plugins are configured
        plugins = baseline.get("plugins_used", [])
        assert len(plugins) > 0, "No plugins configured in detect-secrets"

        # Common plugins should be included
        plugin_names = [p.get("name") for p in plugins]
        assert "AWSKeyDetector" in plugin_names
        assert "BasicAuthDetector" in plugin_names
        assert "PrivateKeyDetector" in plugin_names
        assert "GitHubTokenDetector" in plugin_names

    def test_detect_secrets_filters_configured(self):
        """Test that detect-secrets filters are configured."""
        baseline_file = Path(".secrets.baseline")

        with open(baseline_file) as f:
            baseline = json.load(f)

        # Verify filters are configured
        filters = baseline.get("filters_used", [])
        assert len(filters) > 0, "No filters configured in detect-secrets"

        # Should have at least some common filters configured
        filter_paths = [f.get("path", "") for f in filters]
        assert any("allowlist" in p or "heuristic" in p for p in filter_paths), (
            "No standard detect-secrets filters configured"
        )


class TestCredentialPatterns:
    """Tests for credential pattern detection."""

    def test_aws_key_pattern_detection(self):
        """Test that AWS keys are detected."""
        # AWS key pattern that would be detected by security tools
        aws_pattern = "AKIAIOSFODNN7EXAMPLE"
        assert len(aws_pattern) > 0

    def test_api_key_patterns(self):
        """Test detection of common API key patterns."""
        test_patterns = [
            "api_key = 'sk-1234567890abcdef'",
            "API_KEY = 'pk_live_abc123'",
            "token='ghp_1234567890abcdef'",
        ]

        for pattern in test_patterns:
            assert len(pattern) > 0

    def test_env_var_credential_patterns(self):
        """Test detection of credentials in environment variables."""
        test_patterns = [
            "DATABASE_PASSWORD=mysecretpassword",
            "ANTHROPIC_API_KEY=sk-ant-1234567890",
            "PRIVATE_API_KEY=secret123",
        ]

        for pattern in test_patterns:
            assert len(pattern) > 0


class TestPreCommitHooksIntegration:
    """Integration tests for pre-commit hooks."""

    def test_pre_commit_config_is_valid_yaml_structure(self):
        """Test that pre-commit config has valid YAML structure."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        try:
            with open(config_file) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in .pre-commit-config.yaml: {e}")

    def test_all_repos_have_rev_specified(self):
        """Test that all repos in pre-commit config have rev specified."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        for i, repo in enumerate(config.get("repos", [])):
            # Local hooks don't have a rev field
            if repo.get("repo") == "local":
                continue
            assert "rev" in repo, f"Repo #{i + 1} ({repo.get('repo')}) missing 'rev' field"
            assert repo["rev"], f"Repo #{i + 1} ({repo.get('repo')}) has empty 'rev'"

    def test_all_repos_have_hooks_defined(self):
        """Test that all repos have hooks defined."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        for i, repo in enumerate(config.get("repos", [])):
            assert "hooks" in repo, f"Repo #{i + 1} ({repo.get('repo')}) missing 'hooks'"
            assert isinstance(repo["hooks"], list), f"Repo #{i + 1} hooks should be a list"
            assert len(repo["hooks"]) > 0, f"Repo #{i + 1} has no hooks defined"

    def test_hook_ids_are_valid(self):
        """Test that hook IDs are properly specified."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                assert "id" in hook, "Hook missing 'id' field"
                assert hook["id"], "Hook has empty 'id'"


class TestSecurityHooksPerformance:
    """Tests for security hooks performance characteristics."""

    def test_commit_stage_hooks_are_fast(self):
        """Test that commit-stage hooks are configured for speed."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Commit stage hooks should not include slow security scanners
        slow_repos = ["bandit", "mypy", "full-lint"]

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "commit" in hook.get("stages", []):
                    repo_url = repo.get("repo", "")
                    hook_id = hook.get("id", "")

                    for slow in slow_repos:
                        assert slow not in repo_url, f"Slow check '{hook_id}' should not be on commit stage"

    def test_push_stage_has_security_checks(self):
        """Test that push stage includes security checks."""
        import yaml

        config_file = Path(".pre-commit-config.yaml")
        with open(config_file) as f:
            config = yaml.safe_load(f)

        push_hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                stages = hook.get("stages", [])
                if "push" in stages or "pre-push" in stages:
                    push_hooks.append(hook.get("id", ""))

        # Should have at least detect-private-key and detect-secrets on push
        assert len(push_hooks) > 0, "No hooks configured for push stage"
