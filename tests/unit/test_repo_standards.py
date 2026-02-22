"""Tests for repository standards compliance.

Validates the repository follows practices used by top-tier open source projects
(FastAPI, Pydantic, Ruff, uv, LangChain). Tests focus on what matters for
security, contributor experience, and CI reliability — not invented requirements.

References:
    - OpenSSF Scorecard checks: https://github.com/ossf/scorecard/blob/main/docs/checks.md
    - GitHub Actions security: https://docs.github.com/en/actions/reference/security/secure-use
    - Post-tj-actions best practices (2025): pin actions, least-privilege permissions
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict:
    """Load YAML handling PyYAML's on: -> True quirk."""
    data = yaml.safe_load(path.read_text())
    # PyYAML parses bare `on` as boolean True
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


# ── GitHub Community Health Files ─────────────────────────────────


class TestCommunityHealthFiles:
    """Verify required GitHub community health files exist and have content.

    What top projects do: SECURITY.md at root, CONTRIBUTING.md at root (not .github/),
    CODEOWNERS in .github/, issue templates as YAML forms, PR template.
    """

    def test_security_md_exists(self):
        path = REPO_ROOT / "SECURITY.md"
        assert path.exists(), "SECURITY.md must exist at repo root"
        content = path.read_text()
        assert "Reporting a Vulnerability" in content

    def test_contributing_md_at_root(self):
        """Every 10k+ star project puts CONTRIBUTING.md at root, not .github/."""
        root = REPO_ROOT / "CONTRIBUTING.md"
        assert root.exists(), "CONTRIBUTING.md must exist at repo root"
        content = root.read_text()
        assert "uv" in content, "CONTRIBUTING.md must reference uv package manager"
        # Should not have a duplicate in .github/ (causes confusion)
        dotgithub = REPO_ROOT / ".github" / "CONTRIBUTING.md"
        assert not dotgithub.exists(), (
            "CONTRIBUTING.md should be at root only, not duplicated in .github/"
        )

    def test_codeowners_exists(self):
        path = REPO_ROOT / ".github" / "CODEOWNERS"
        assert path.exists(), "CODEOWNERS must exist in .github/"
        content = path.read_text()
        assert "@manderson240" in content

    def test_pr_template_exists(self):
        path = REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
        assert path.exists()
        content = path.read_text()
        assert "## Summary" in content
        assert "## Test Plan" in content

    def test_issue_templates_are_yaml_forms(self):
        """Modern GitHub repos use YAML issue forms, not single markdown."""
        template_dir = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
        assert template_dir.is_dir(), "ISSUE_TEMPLATE must be a directory with YAML forms"

        old_template = REPO_ROOT / ".github" / "ISSUE_TEMPLATE.md"
        assert not old_template.exists(), (
            "Old single-file ISSUE_TEMPLATE.md should be removed in favor of YAML forms"
        )

    def test_bug_report_template(self):
        path = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert data["name"] == "Bug Report"
        field_ids = [f.get("id") for f in data["body"] if f.get("type") != "markdown"]
        assert "description" in field_ids
        assert "reproduction" in field_ids

    def test_feature_request_template(self):
        path = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml"
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert data["name"] == "Feature Request"

    def test_issue_template_config(self):
        path = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert data.get("blank_issues_enabled") is False


# ── GitHub Actions Workflows ──────────────────────────────────────


class TestWorkflowStandards:
    """Validate GitHub Actions workflow quality and security.

    Modeled after practices from ruff (40k+), uv (40k+), FastAPI (70k+),
    and LangChain (100k+). Tests what actually prevents security incidents
    and CI issues, not invented requirements.
    """

    @pytest.fixture
    def ci_workflow(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        assert path.exists()
        return _load_yaml(path)

    def test_no_duplicate_workflows(self):
        """Consolidated CI should replace separate lint.yml and test.yml."""
        workflows_dir = REPO_ROOT / ".github" / "workflows"
        filenames = {f.name for f in workflows_dir.glob("*.yml")}
        assert "ci.yml" in filenames, "ci.yml must exist as unified CI pipeline"
        assert "lint.yml" not in filenames, "lint.yml should be removed (consolidated into ci.yml)"
        assert "test.yml" not in filenames, "test.yml should be removed (consolidated into ci.yml)"

    def test_ci_uses_setup_uv(self, ci_workflow):
        """CI must use astral-sh/setup-uv, not pip install uv."""
        ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
        assert "astral-sh/setup-uv" in ci_text, "CI must use official setup-uv action"
        assert "pip install uv" not in ci_text, "Do not use pip to install uv"

    def test_ci_uses_modern_action_versions(self, ci_workflow):
        """CI should use reasonably modern action versions (not ancient @v1/@v2)."""
        ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
        # Check that checkout is at least v4 (not v1, v2, v3)
        checkout_refs = re.findall(r"actions/checkout@v(\d+)", ci_text)
        for version in checkout_refs:
            assert int(version) >= 4, f"actions/checkout@v{version} is too old, use v4+"
        # Check that setup-python is at least v4
        setup_python_refs = re.findall(r"actions/setup-python@v(\d+)", ci_text)
        for version in setup_python_refs:
            assert int(version) >= 4, f"actions/setup-python@v{version} is too old, use v4+"

    def test_ci_has_concurrency(self, ci_workflow):
        """CI should cancel redundant runs on the same branch."""
        assert "concurrency" in ci_workflow

    def test_ci_has_dependency_review(self, ci_workflow):
        """CI should include dependency review for PRs."""
        jobs = ci_workflow.get("jobs", {})
        assert "dependency-review" in jobs, "CI must include dependency-review job"

    def test_ci_no_bare_pip(self):
        """No workflow should use bare pip install."""
        workflows_dir = REPO_ROOT / ".github" / "workflows"
        for wf_path in workflows_dir.glob("*.yml"):
            content = wf_path.read_text()
            lines = content.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "pip install" in stripped and "uv" not in stripped:
                    pytest.fail(
                        f"{wf_path.name}:{i + 1} uses bare pip: {stripped!r}. Use uv instead."
                    )

    def test_dependabot_configured(self):
        path = REPO_ROOT / ".github" / "dependabot.yml"
        assert path.exists(), "Dependabot config must exist"
        data = yaml.safe_load(path.read_text())
        ecosystems = {u["package-ecosystem"] for u in data.get("updates", [])}
        assert "pip" in ecosystems, "Dependabot must monitor Python deps"
        assert "github-actions" in ecosystems, "Dependabot must monitor GH Actions"


# ── Workflow Security (OpenSSF / post-tj-actions) ─────────────────


class TestWorkflowSecurity:
    """Security best practices that actually prevent supply chain attacks.

    After the tj-actions incident (March 2025), the OpenSSF and GitHub
    recommend: least-privilege permissions, persist-credentials: false,
    job timeouts, and action version pinning.

    Reference: https://openssf.org/blog/2025/06/11/maintainers-guide-securing-ci-cd-pipelines/
    """

    def _all_workflows(self):
        """Yield (path, data) for every workflow file."""
        workflows_dir = REPO_ROOT / ".github" / "workflows"
        for wf_path in sorted(workflows_dir.glob("*.yml")):
            yield wf_path, _load_yaml(wf_path)

    def test_workflows_have_top_level_permissions(self):
        """Every workflow must declare top-level permissions (OpenSSF Scorecard).

        This sets a least-privilege default. Jobs that need more access
        declare their own permissions block, which overrides the default.
        Top OSS pattern: `permissions: contents: read` or `permissions: {}`.
        """
        for wf_path, data in self._all_workflows():
            assert "permissions" in data, (
                f"{wf_path.name} missing top-level `permissions:` block. "
                "Add `permissions: contents: read` or `permissions: {{}}` for least privilege."
            )

    def test_ci_jobs_have_timeout(self):
        """CI jobs must have timeout-minutes to prevent runaway builds.

        Ruff uses 10 min, LangChain uses 15-30 min. Without a timeout,
        a hung job wastes Actions minutes indefinitely.
        """
        ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        data = _load_yaml(ci_path)
        jobs = data.get("jobs", {})
        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict):
                assert "timeout-minutes" in job_config, (
                    f"CI job '{job_name}' missing timeout-minutes"
                )

    def test_checkout_uses_persist_credentials_false(self):
        """Checkout steps should use persist-credentials: false.

        This prevents the GITHUB_TOKEN from persisting in the git config,
        reducing blast radius if a later step is compromised. Used by
        ruff, uv, and recommended by OpenSSF.
        """
        ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text()
        # Count checkout actions and persist-credentials: false
        checkout_count = content.count("actions/checkout@")
        persist_false_count = content.count("persist-credentials: false")
        assert persist_false_count >= checkout_count, (
            f"CI has {checkout_count} checkout steps but only {persist_false_count} "
            "use persist-credentials: false"
        )

    def test_claude_workflow_has_write_permissions(self):
        """Claude coding agent needs write permissions to create PRs."""
        path = REPO_ROOT / ".github" / "workflows" / "claude.yml"
        data = _load_yaml(path)
        jobs = data.get("jobs", {})
        claude_job = jobs.get("claude", {})
        perms = claude_job.get("permissions", {})
        assert perms.get("contents") == "write"
        assert perms.get("pull-requests") == "write"

    def test_review_workflow_has_pr_write(self):
        """Review workflow needs write to post comments."""
        path = REPO_ROOT / ".github" / "workflows" / "claude-code-review.yml"
        data = _load_yaml(path)
        jobs = data.get("jobs", {})
        review_job = jobs.get("claude-review", {})
        perms = review_job.get("permissions", {})
        assert perms.get("pull-requests") == "write"

    def test_ci_jobs_no_unnecessary_write(self):
        """CI jobs (lint, test, etc.) should not have contents: write."""
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        data = _load_yaml(path)
        jobs = data.get("jobs", {})
        read_only_jobs = {"lint", "test", "typecheck", "validate", "compound"}
        for job_name in read_only_jobs:
            job = jobs.get(job_name, {})
            if isinstance(job, dict):
                perms = job.get("permissions", {})
                assert perms.get("contents") != "write", (
                    f"CI job {job_name} should not have contents: write"
                )


# ── Claude Code Configuration ─────────────────────────────────────


class TestClaudeCodeConfig:
    """Validate Claude Code hooks and settings."""

    @pytest.fixture
    def settings(self):
        path = REPO_ROOT / ".claude" / "settings.json"
        assert path.exists()
        return json.loads(path.read_text())

    def test_settings_has_hooks(self, settings):
        assert "hooks" in settings

    def test_pre_tool_use_hooks_exist(self, settings):
        """PreToolUse hooks must protect files and validate commands."""
        pre_hooks = settings["hooks"].get("PreToolUse", [])
        matchers = [h.get("matcher", "") for h in pre_hooks]
        assert any("Edit" in m or "Write" in m for m in matchers), (
            "PreToolUse must have Edit/Write protection hook"
        )
        assert any("Bash" in m for m in matchers), "PreToolUse must have Bash safety hook"

    def test_post_tool_use_lint_hook(self, settings):
        """PostToolUse should auto-lint after file edits."""
        post_hooks = settings["hooks"].get("PostToolUse", [])
        matchers = [h.get("matcher", "") for h in post_hooks]
        assert any("Edit" in m or "Write" in m for m in matchers), (
            "PostToolUse must have lint hook for Edit/Write"
        )

    def test_hook_scripts_are_executable(self):
        hooks_dir = REPO_ROOT / ".claude" / "hooks"
        if not hooks_dir.exists():
            pytest.skip("No hooks directory")
        for script in hooks_dir.glob("*.sh"):
            assert os.access(script, os.X_OK), f"{script.name} must be executable"

    def test_permissions_deny_force_push(self, settings):
        deny = settings.get("permissions", {}).get("deny", [])
        deny_str = " ".join(deny)
        assert "force" in deny_str or "-f" in deny_str, "Permissions must deny force push"

    def test_permissions_deny_hard_reset(self, settings):
        deny = settings.get("permissions", {}).get("deny", [])
        deny_str = " ".join(deny)
        assert "reset --hard" in deny_str

    def test_permissions_allow_git_push(self, settings):
        """git push (non-force) must be allowed for agentic workflows."""
        allow = settings.get("permissions", {}).get("allow", [])
        assert any("git push" in a for a in allow)


# ── pyproject.toml Consistency ────────────────────────────────────


class TestPyprojectConsistency:
    """Validate pyproject.toml has no version mismatches."""

    @pytest.fixture
    def pyproject_text(self):
        return (REPO_ROOT / "pyproject.toml").read_text()

    def test_requires_python_is_313(self, pyproject_text):
        assert 'requires-python = ">=3.13"' in pyproject_text

    def test_ruff_target_matches_project(self, pyproject_text):
        assert 'target-version = "py313"' in pyproject_text, (
            "Ruff target-version must match requires-python (py313)"
        )

    def test_mypy_version_matches_project(self, pyproject_text):
        assert 'python_version = "3.13"' in pyproject_text, (
            "mypy python_version must match requires-python (3.13)"
        )

    def test_no_black_in_deps(self, pyproject_text):
        """Ruff replaces Black — black should not be in dev deps."""
        dev_match = re.search(r"dev = \[(.*?)\]", pyproject_text, re.DOTALL)
        if dev_match:
            dev_section = dev_match.group(1)
            assert "black" not in dev_section.lower(), (
                "black should be removed from dev deps (ruff replaces it)"
            )

    def test_no_flake8_in_deps(self, pyproject_text):
        """Ruff replaces flake8 — flake8 should not be in dev deps."""
        dev_match = re.search(r"dev = \[(.*?)\]", pyproject_text, re.DOTALL)
        if dev_match:
            dev_section = dev_match.group(1)
            assert "flake8" not in dev_section.lower(), (
                "flake8 should be removed from dev deps (ruff replaces it)"
            )


# ── Pre-commit Configuration ─────────────────────────────────────


class TestPreCommitConfig:
    """Validate pre-commit hook configuration."""

    @pytest.fixture
    def precommit_config(self):
        path = REPO_ROOT / ".pre-commit-config.yaml"
        assert path.exists()
        return yaml.safe_load(path.read_text())

    def test_has_ruff_hooks(self, precommit_config):
        repos = [r.get("repo", "") for r in precommit_config.get("repos", [])]
        assert any("ruff" in r for r in repos), "Pre-commit must include ruff"

    def test_has_large_file_check(self, precommit_config):
        all_hook_ids = []
        for repo in precommit_config.get("repos", []):
            for hook in repo.get("hooks", []):
                all_hook_ids.append(hook.get("id", ""))
        assert "check-added-large-files" in all_hook_ids

    def test_has_private_key_detection(self, precommit_config):
        all_hook_ids = []
        for repo in precommit_config.get("repos", []):
            for hook in repo.get("hooks", []):
                all_hook_ids.append(hook.get("id", ""))
        assert "detect-private-key" in all_hook_ids


# ── .gitignore Coverage ──────────────────────────────────────────


class TestGitignore:
    """Validate .gitignore covers necessary patterns."""

    @pytest.fixture
    def gitignore(self):
        return (REPO_ROOT / ".gitignore").read_text()

    def test_ignores_env_files(self, gitignore):
        assert ".env" in gitignore

    def test_ignores_venv(self, gitignore):
        assert ".venv" in gitignore

    def test_ignores_pycache(self, gitignore):
        assert "__pycache__" in gitignore

    def test_ignores_checkpoints(self, gitignore):
        assert ".pt" in gitignore or "checkpoint" in gitignore.lower()

    def test_ignores_log_files(self, gitignore):
        assert "*.log" in gitignore

    def test_ignores_coverage(self, gitignore):
        assert ".coverage" in gitignore
