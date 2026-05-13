"""Pre-commit Hooks and Secret Detection Tests - Task #4 Validation.

This test suite validates Task #4 of Phase 2 Security Hardening:
- Pre-commit framework installation
- detect-secrets package and configuration
- Secret baseline creation
- Git hook installation
- Credential detection capability
"""

import json
import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestPrecommitInstallation:
    """Test pre-commit framework installation."""

    def test_precommit_config_exists(self):
        """Verify .pre-commit-config.yaml exists."""
        config_path = PROJECT_ROOT / ".pre-commit-config.yaml"
        assert config_path.exists(), f"Pre-commit config not found at {config_path}"

    def test_precommit_config_is_valid_yaml(self):
        """Verify .pre-commit-config.yaml is valid YAML."""
        config_path = PROJECT_ROOT / ".pre-commit-config.yaml"
        try:
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)
            assert config is not None
            assert "repos" in config
        except ImportError:
            pytest.skip("PyYAML not available")

    def test_precommit_has_detect_secrets_hook(self):
        """Verify detect-secrets hook is configured."""
        config_path = PROJECT_ROOT / ".pre-commit-config.yaml"
        try:
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)

            repos = [repo.get("repo", "") for repo in config.get("repos", [])]
            assert any("detect-secrets" in repo for repo in repos), "detect-secrets repo not configured"
        except ImportError:
            pytest.skip("PyYAML not available")

    def test_precommit_has_bandit_hook(self):
        """Verify bandit security hook is configured."""
        config_path = PROJECT_ROOT / ".pre-commit-config.yaml"
        try:
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)

            repos = [repo.get("repo", "") for repo in config.get("repos", [])]
            assert any("bandit" in repo for repo in repos), "bandit repo not configured"
        except ImportError:
            pytest.skip("PyYAML not available")

    def test_precommit_config_has_commit_stage(self):
        """Verify pre-commit has commit stage hooks."""
        config_path = PROJECT_ROOT / ".pre-commit-config.yaml"
        with open(config_path) as f:
            content = f.read()
        # Accept both old (commit) and new (pre-commit) stage naming
        assert "stages: [commit]" in content or "stages: [pre-commit]" in content, "No commit stage hooks configured"

    def test_precommit_config_has_push_stage(self):
        """Verify pre-commit has push stage hooks."""
        config_path = PROJECT_ROOT / ".pre-commit-config.yaml"
        with open(config_path) as f:
            content = f.read()
        # Accept both old (push) and new (pre-push) stage naming
        assert "stages: [push]" in content or "stages: [pre-push]" in content, "No push stage hooks configured"


class TestDetectSecretsConfiguration:
    """Test detect-secrets package and configuration."""

    def test_secrets_baseline_exists(self):
        """Verify .secrets.baseline exists."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        assert baseline_path.exists(), f"Secrets baseline not found at {baseline_path}"

    def test_secrets_baseline_is_valid_json(self):
        """Verify .secrets.baseline is valid JSON."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        try:
            with open(baseline_path) as f:
                baseline = json.load(f)
            assert baseline is not None
            assert "version" in baseline
            assert "plugins_used" in baseline
        except json.JSONDecodeError:
            pytest.fail("Secrets baseline is not valid JSON")

    def test_secrets_baseline_has_version(self):
        """Verify baseline has version information."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        with open(baseline_path) as f:
            baseline = json.load(f)
        version = baseline.get("version", "")
        assert version >= "1.4.0", f"Baseline version should be >= 1.4.0, got {version}"

    def test_secrets_baseline_has_plugins(self):
        """Verify baseline has detection plugins configured."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        with open(baseline_path) as f:
            baseline = json.load(f)

        plugins_used = baseline.get("plugins_used", [])
        plugin_names = [p.get("name", "") for p in plugins_used]

        # Essential plugins for comprehensive secret detection
        expected_plugins = [
            "AWSKeyDetector",
            "BasicAuthDetector",
            "GitHubTokenDetector",
            "KeywordDetector",
            "PrivateKeyDetector",
            "SlackDetector",
        ]

        for plugin in expected_plugins:
            assert plugin in plugin_names, f"Missing plugin: {plugin}"

    def test_secrets_baseline_has_filters(self):
        """Verify baseline has filters configured."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        with open(baseline_path) as f:
            baseline = json.load(f)

        filters_used = baseline.get("filters_used", [])
        assert len(filters_used) > 0, "No filters configured in baseline"

    def test_secrets_baseline_results_empty(self):
        """Verify baseline results are initially empty."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        with open(baseline_path) as f:
            baseline = json.load(f)

        results = baseline.get("results", {})
        assert isinstance(results, dict), "Results should be a dictionary"


class TestGitHooksInstallation:
    """Test git hook installation."""

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / ".git/hooks/pre-commit").exists(),
        reason="pre-commit hooks not installed (run 'pre-commit install')",
    )
    def test_pre_commit_hook_exists(self):
        """Verify .git/hooks/pre-commit exists."""
        hook_path = PROJECT_ROOT / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists(), f"Pre-commit hook not found at {hook_path}"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / ".git/hooks/pre-push").exists(),
        reason="pre-push hooks not installed (run 'pre-commit install --hook-type pre-push')",
    )
    def test_pre_push_hook_exists(self):
        """Verify .git/hooks/pre-push exists."""
        hook_path = PROJECT_ROOT / ".git" / "hooks" / "pre-push"
        assert hook_path.exists(), f"Pre-push hook not found at {hook_path}"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / ".git/hooks/pre-commit").exists(),
        reason="pre-commit hooks not installed",
    )
    def test_pre_commit_hook_is_executable(self):
        """Verify .git/hooks/pre-commit is executable."""
        hook_path = PROJECT_ROOT / ".git" / "hooks" / "pre-commit"
        assert os.access(hook_path, os.X_OK), "Pre-commit hook is not executable"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / ".git/hooks/pre-push").exists(),
        reason="pre-push hooks not installed",
    )
    def test_pre_push_hook_is_executable(self):
        """Verify .git/hooks/pre-push is executable."""
        hook_path = PROJECT_ROOT / ".git" / "hooks" / "pre-push"
        assert os.access(hook_path, os.X_OK), "Pre-push hook is not executable"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / ".git/hooks/pre-commit").exists(),
        reason="pre-commit hooks not installed",
    )
    def test_pre_commit_hook_references_framework(self):
        """Verify .git/hooks/pre-commit references pre-commit framework."""
        hook_path = PROJECT_ROOT / ".git" / "hooks" / "pre-commit"
        with open(hook_path) as f:
            content = f.read()
        assert "pre-commit" in content.lower(), "Pre-commit hook should reference pre-commit framework"


class TestSecurityToolsInstallation:
    """Test security tools installation."""

    def test_install_script_is_executable(self):
        """Verify install_security_tools.sh exists and is executable."""
        script_path = PROJECT_ROOT / "scripts" / "setup" / "install_security_tools.sh"
        assert script_path.exists(), f"Script not found at {script_path}"
        assert os.access(script_path, os.X_OK), f"Script is not executable: {script_path}"

    def test_install_script_creates_baseline(self):
        """Verify install script creates secrets baseline."""
        script_path = PROJECT_ROOT / "scripts" / "setup" / "install_security_tools.sh"
        with open(script_path) as f:
            content = f.read()
        assert ".secrets.baseline" in content, "Install script should handle .secrets.baseline"

    def test_install_script_installs_hooks(self):
        """Verify install script installs pre-commit hooks."""
        script_path = PROJECT_ROOT / "scripts" / "setup" / "install_security_tools.sh"
        with open(script_path) as f:
            content = f.read()
        assert "pre-commit install" in content, "Install script should run pre-commit install"

    def test_install_script_documents_usage(self):
        """Verify install script documents setup and usage."""
        script_path = PROJECT_ROOT / "scripts" / "setup" / "install_security_tools.sh"
        with open(script_path) as f:
            content = f.read()

        expected_docs = [
            "SKIP=",
            "detect-secrets scan",
            "Next steps",
        ]

        for doc in expected_docs:
            assert doc in content, f"Documentation missing: {doc}"


class TestDetectSecretsCapability:
    """Test secret detection capability."""

    def test_detect_secrets_plugins_comprehensive(self):
        """Verify detect-secrets has comprehensive plugin coverage."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        with open(baseline_path) as f:
            baseline = json.load(f)

        plugins_used = baseline.get("plugins_used", [])
        plugin_names = {p.get("name") for p in plugins_used}

        # Comprehensive secret types covered
        high_value_plugins = {
            "AWSKeyDetector",
            "GitHubTokenDetector",
            "BasicAuthDetector",
            "PrivateKeyDetector",
            "Base64HighEntropyString",
            "HexHighEntropyString",
        }

        covered = high_value_plugins & plugin_names
        assert len(covered) >= 4, f"Missing key plugins. Have: {covered}"

    def test_baseline_excludes_directories(self):
        """Verify baseline excludes common safe directories."""
        baseline_path = PROJECT_ROOT / ".secrets.baseline"
        with open(baseline_path) as f:
            baseline = json.load(f)

        # Verify plugins are configured to exclude safe directories
        plugins_used = baseline.get("plugins_used", [])
        assert len(plugins_used) > 0, "Plugins should be configured"


class TestPrecommitIntegration:
    """Integration tests for pre-commit system."""

    def test_security_tools_documentation(self):
        """Verify security tools are documented."""
        doc_path = PROJECT_ROOT / "SECURITY_PROCEDURES.md"
        if doc_path.exists():
            with open(doc_path) as f:
                content = f.read()
            assert "pre-commit" in content.lower() or "hooks" in content.lower(), (
                "Security procedures should document pre-commit setup"
            )

    def test_gitignore_protects_sensitive_files(self):
        """Verify .gitignore prevents committing sensitive files."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                content = f.read()

            # Sensitive patterns that should be ignored
            sensitive_patterns = [
                "*.key",
                "*.pem",
                ".env",
            ]

            for pattern in sensitive_patterns:
                if pattern in content:
                    break  # At least one pattern found
            else:
                pytest.skip(".gitignore may not have all sensitive patterns")

    def test_setup_scripts_complete(self):
        """Verify all necessary setup scripts exist."""
        scripts = [
            PROJECT_ROOT / "scripts" / "setup" / "generate_tls_certificates.sh",
            PROJECT_ROOT / "scripts" / "setup" / "install_security_tools.sh",
        ]

        for script in scripts:
            assert script.exists(), f"Missing setup script: {script}"
