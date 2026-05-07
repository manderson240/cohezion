"""Pre-commit hooks configuration for credential detection and security checks."""

import logging
import shutil
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


def _which(name: str, fallback: str = "") -> str:
    """Resolve executable path; fall back to bare name (subprocess will surface errors)."""
    return shutil.which(name) or fallback or name


class PreCommitConfiguration:
    """Manage pre-commit hooks for security scanning."""

    @staticmethod
    def is_detect_secrets_installed() -> bool:
        """
        Check if detect-secrets package is installed.

        Returns:
            True if detect-secrets is available, False otherwise
        """
        try:
            result = subprocess.run(  # noqa: S603 - static probe; tool may not be installed
                [_which("detect-secrets"), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def is_pre_commit_installed() -> bool:
        """
        Check if pre-commit framework is installed.

        Returns:
            True if pre-commit is available, False otherwise
        """
        try:
            result = subprocess.run(  # noqa: S603 - static probe; tool may not be installed
                [_which("pre-commit"), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def install_detect_secrets() -> bool:
        """
        Install detect-secrets package.

        Returns:
            True if installation successful, False otherwise
        """
        try:
            result = subprocess.run(  # noqa: S603 - static install command, no user input
                [_which("pip"), "install", "detect-secrets"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("✓ detect-secrets installed successfully")
                return True
            else:
                logger.error("Failed to install detect-secrets: %s", result.stderr)
                return False
        except Exception as e:
            logger.error("Error installing detect-secrets: %s", e)
            return False

    @staticmethod
    def install_pre_commit() -> bool:
        """
        Install pre-commit framework.

        Returns:
            True if installation successful, False otherwise
        """
        try:
            result = subprocess.run(  # noqa: S603 - static install command, no user input
                [_which("pip"), "install", "pre-commit"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("✓ pre-commit installed successfully")
                return True
            else:
                logger.error("Failed to install pre-commit: %s", result.stderr)
                return False
        except Exception as e:
            logger.error("Error installing pre-commit: %s", e)
            return False

    @staticmethod
    def create_pre_commit_config(
        config_path: str = ".pre-commit-config.yaml",
    ) -> bool:
        """
        Create .pre-commit-config.yaml with security hooks.

        Args:
            config_path: Path to .pre-commit-config.yaml

        Returns:
            True if config created successfully, False otherwise
        """
        config_content = """# Pre-commit hooks configuration for security scanning
repos:
  # Credential Detection
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        name: Detect secrets
        entry: detect-secrets scan
        language: python
        types: [python]
        exclude: ^tests/
        args:
          - --baseline
          - .secrets.baseline
          - --force-use-all-plugins
          - --plugins
          - ArtifactoryDetector
          - AWSKeyDetector
          - AzureStorageKeyDetector
          - BasicAuthDetector
          - CloudantDetector
          - DiscordBotTokenDetector
          - GitHubTokenDetector
          - HexHighEntropyString
          - IbmCloudIamDetector
          - IbmCosHmacDetector
          - JwtTokenDetector
          - KeywordDetector
          - MailchimpDetector
          - NpmDetector
          - PrivateKeyDetector
          - SendGridDetector
          - SlackDetector
          - SoftlayerDetector
          - SquareOAuthDetector
          - TwilioKeyDetector

  # Security Checks (Bandit)
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        name: Bandit security check
        entry: bandit
        language: python
        types: [python]
        exclude: ^tests/
        args:
          - -ll
          - --severity-level
          - medium

  # Basic commit checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: check-ast
        name: Check Python AST
      - id: check-merge-conflict
        name: Check for merge conflicts
      - id: check-yaml
        name: Check YAML files
      - id: end-of-file-fixer
        name: Fix end of file
      - id: trailing-whitespace
        name: Trim trailing whitespace
      - id: mixed-line-ending
        name: Check line endings
        args:
          - --fix=lf
"""

        try:
            config_file = Path(config_path)
            config_file.write_text(config_content)
            logger.info("✓ Created %s", config_path)
            return True
        except Exception as e:
            logger.error("Failed to create pre-commit config: %s", e)
            return False

    @staticmethod
    def create_baseline(
        baseline_path: str = ".secrets.baseline",
    ) -> bool:
        """
        Create secrets baseline for known secrets.

        Args:
            baseline_path: Path to .secrets.baseline file

        Returns:
            True if baseline created successfully, False otherwise
        """
        try:
            # Initialize baseline with no secrets
            result = subprocess.run(  # noqa: S603 - baseline_path internal, args static
                [
                    _which("detect-secrets"),
                    "scan",
                    "--baseline",
                    baseline_path,
                    "--force-use-all-plugins",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info("✓ Created baseline at %s", baseline_path)
                return True
            else:
                logger.warning(
                    "Baseline creation completed with warnings: %s",
                    result.stderr,
                )
                # Still consider successful if file was created
                return Path(baseline_path).exists()

        except Exception as e:
            logger.error("Error creating baseline: %s", e)
            return False

    @staticmethod
    def install_git_hooks(
        repo_path: str | None = None,
    ) -> bool:
        """
        Install pre-commit git hooks.

        Args:
            repo_path: Path to git repository (default: current directory)

        Returns:
            True if hooks installed successfully, False otherwise
        """
        try:
            cmd = [_which("pre-commit"), "install"]
            kwargs = {"capture_output": True, "text": True, "timeout": 10}

            if repo_path:
                kwargs["cwd"] = repo_path

            result = subprocess.run(cmd, **kwargs)  # noqa: S603 - static command

            if result.returncode == 0:
                logger.info("✓ Pre-commit hooks installed successfully")
                return True
            else:
                logger.error("Failed to install hooks: %s", result.stderr)
                return False

        except Exception as e:
            logger.error("Error installing hooks: %s", e)
            return False

    @staticmethod
    def run_detect_secrets_check(
        baseline_path: str = ".secrets.baseline",
    ) -> bool:
        """
        Run detect-secrets scan against baseline.

        Args:
            baseline_path: Path to baseline file

        Returns:
            True if no new secrets found, False if secrets detected
        """
        try:
            result = subprocess.run(  # noqa: S603 - baseline_path internal, args static
                [
                    _which("detect-secrets"),
                    "scan",
                    "--baseline",
                    baseline_path,
                    "--force-use-all-plugins",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info("✓ No new secrets detected")
                return True
            else:
                logger.warning("Potential secrets detected")
                return False

        except Exception as e:
            logger.error("Error running detect-secrets: %s", e)
            return False

    @staticmethod
    def setup_security_hooks(
        repo_path: str | None = None,
    ) -> bool:
        """
        Complete setup of security hooks in repository.

        Args:
            repo_path: Path to git repository

        Returns:
            True if all setup successful, False otherwise
        """
        logger.info("Setting up security hooks...")

        # Check/install detect-secrets
        if not PreCommitConfiguration.is_detect_secrets_installed():
            logger.info("Installing detect-secrets...")
            if not PreCommitConfiguration.install_detect_secrets():
                logger.error("Failed to install detect-secrets")
                return False

        # Check/install pre-commit
        if not PreCommitConfiguration.is_pre_commit_installed():
            logger.info("Installing pre-commit...")
            if not PreCommitConfiguration.install_pre_commit():
                logger.error("Failed to install pre-commit")
                return False

        # Create baseline
        if not PreCommitConfiguration.create_baseline():
            logger.warning("Failed to create baseline (may not be critical)")

        # Create config
        if not PreCommitConfiguration.create_pre_commit_config():
            logger.error("Failed to create pre-commit config")
            return False

        # Install hooks
        if not PreCommitConfiguration.install_git_hooks(repo_path):
            logger.error("Failed to install git hooks")
            return False

        logger.info("✓ Security hooks setup complete")
        return True
