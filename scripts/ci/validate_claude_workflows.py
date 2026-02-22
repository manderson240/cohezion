#!/usr/bin/env python3
"""Validate that Claude GitHub Actions workflows have correct write permissions.

@claude PR mentions fail silently when permissions are set to 'read' — Claude
receives the trigger event but cannot post a reply or push code changes.

Required permissions for @claude to function:
  - contents: write      (push code changes)
  - pull-requests: write (post PR/review comments)
  - issues: write        (post issue comments)

This script is called by .github/workflows/validate-claude-config.yml on every
PR that touches .github/workflows/claude*.yml and on a weekly schedule.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

CLAUDE_WORKFLOWS = [
    ".github/workflows/claude.yml",
    ".github/workflows/claude-code-review.yml",
]

# Permissions that must be 'write' for @claude to work
REQUIRED_WRITE_PERMISSIONS = {"contents", "pull-requests", "issues"}

# Action must NOT be pinned to the deprecated beta tag
DEPRECATED_ACTION_TAGS = {"@beta"}

errors: list[str] = []
checked: list[str] = []


def check_workflow(workflow_path: str) -> None:
    path = Path(workflow_path)
    if not path.exists():
        errors.append(f"  [{workflow_path}] File not found")
        return

    with open(path) as f:
        config = yaml.safe_load(f)

    jobs: dict = config.get("jobs", {})

    for job_name, job in jobs.items():
        perms: dict = job.get("permissions", {})

        for perm in REQUIRED_WRITE_PERMISSIONS:
            value = perms.get(perm)
            if value != "write":
                errors.append(
                    f"  [{workflow_path}] job '{job_name}': "
                    f"permissions.{perm} must be 'write', got '{value or 'not set'}'"
                )

        for step in job.get("steps", []):
            uses: str = step.get("uses", "")
            if "claude-code-action" in uses:
                for deprecated_tag in DEPRECATED_ACTION_TAGS:
                    if deprecated_tag in uses:
                        errors.append(
                            f"  [{workflow_path}] job '{job_name}': "
                            f"step uses deprecated tag '{deprecated_tag}' ({uses}). "
                            f"Update to @v1"
                        )

    checked.append(workflow_path)


def main() -> None:
    print("Validating Claude workflow configurations...")
    print()

    for workflow_path in CLAUDE_WORKFLOWS:
        check_workflow(workflow_path)

    if errors:
        print("❌ Claude workflow configuration errors found:\n")
        for error in errors:
            print(error)
        print()
        print("Required fix — each Claude workflow job must have:")
        print("  permissions:")
        print("    contents: write")
        print("    pull-requests: write")
        print("    issues: write")
        print()
        print(
            "Without these, @claude receives the trigger event but cannot "
            "post replies or push code, making it appear broken."
        )
        sys.exit(1)

    print(f"✅ All Claude workflow configurations are valid")
    for path in checked:
        print(f"   {path}")


if __name__ == "__main__":
    main()
