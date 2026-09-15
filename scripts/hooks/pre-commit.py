#!/usr/bin/env python3
import os
import subprocess
import sys

_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


def get_staged_files():
    try:
        # Check added, copied, modified files only (exclude deleted files)
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=d"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.splitlines()
    except subprocess.CalledProcessError:
        return []



def check_file_size(file_path):
    if not os.path.exists(file_path):
        return True

    size = os.path.getsize(file_path)
    if size > MAX_SIZE_BYTES:
        print(f"❌ Error: File '{file_path}' is too large ({size / (1024 * 1024):.2f} MB).")
        print(f"   Max allowed size is {MAX_SIZE_BYTES / (1024 * 1024):.2f} MB.")
        return False
    return True


def main():
    staged_files = get_staged_files()
    forbidden_files = []

    for f in staged_files:
        if not check_file_size(f):
            forbidden_files.append(f)

    if forbidden_files:
        print("\n🚫 Commit blocked due to large files.")
        print("Please remove these files or add them to .gitignore if they are artifacts.")
        sys.exit(1)

    # Check for ignored files that are staged for addition/modification
    # (Excludes deleted files so tracked files can be cleanly purged)
    if staged_files:
        non_deleted_proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=d"],
            capture_output=True,
            text=True,
        )
        non_deleted = [f.strip() for f in non_deleted_proc.stdout.splitlines() if f.strip()]
        if non_deleted:
            check_proc = subprocess.run(
                ["git", "check-ignore", "--stdin"],
                input="\n".join(non_deleted),
                capture_output=True,
                text=True,
            )
            ignored_staged = [line.strip() for line in check_proc.stdout.splitlines() if line.strip()]
            if ignored_staged:
                print("\n🚫 Commit blocked: Some staged files match .gitignore patterns.")
                for f in ignored_staged:
                    print(f"   - {f}")
                print("Please unstage them with 'git rm --cached <file>'.")
                sys.exit(1)


    # 3. Forbidden Credential Files & Secret Scanning
    try:
        from cohezion.security.secret_scrubber import (
            FORBIDDEN_CREDENTIAL_FILES,
            contains_unredacted_credentials,
        )
    except ImportError:
        FORBIDDEN_CREDENTIAL_FILES = []
        contains_unredacted_credentials = None

    for f in staged_files:
        for forbidden in FORBIDDEN_CREDENTIAL_FILES:
            if forbidden.search(f):
                print(f"\n🚫 Commit blocked: Staged file '{f}' matches forbidden credential pattern '{forbidden.pattern}'.")
                print("Never stage credential files. Use environment variables or secret vaults.")
                sys.exit(1)

    import re

    SECRET_PATTERNS = [
        (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "Google Cloud API Key"),
        (re.compile(r"\bsk-[a-zA-Z0-9_\-]{20,60}\b"), "API Key"),
        (re.compile(r"\bsk-ant-api[0-9]{2}-[a-zA-Z0-9_\-]{30,120}\b"), "Anthropic Key"),
        (re.compile(r'("key"\s*:\s*")[a-f0-9]{32}(")'), "Kaggle API Key"),
        (re.compile(r"\bBQUBIT_[a-zA-Z0-9_\-]{20,80}\b"), "BlueQubit Token"),
        (re.compile(r"xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}"), "Slack Token"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
        (re.compile(r"PRIVATE\s+KEY"), "Private Key"),
    ]

    EXEMPT_SECRET_SCAN_PATHS = {
        "src/cohezion/security/secret_scrubber.py",
        "tests/security/test_secret_scrubber.py",
        "scripts/ops/verify_credential_defense_gates.py",
        "docs/reconcile/vss-head-versions/src_cohezion_core_persistence_surreal_client.py",
        "docs/research/daemon_fleet_upgrade_audit.md",
        "docs/research/twenty_cycles_adversarial_review.md",
        "scripts/kaggle/arc3_autoharness_kernel/arc-agi-3-autoharness-agent.ipynb",
    }

    found_secrets = False
    for f in staged_files:
        if f in EXEMPT_SECRET_SCAN_PATHS or f.startswith("docs/") or f.startswith("tests/security/"):
            continue
        if os.path.isfile(f):
            try:
                with open(f, encoding="utf-8", errors="replace") as file_content:
                    content = file_content.read()
                    if "# pragma: allowlist secret" in content:
                        continue
                    is_test_or_doc = (
                        f.startswith("tests/")
                        or f.endswith(".md")
                        or f.startswith("docs/")
                        or "/test_" in f
                        or f.startswith("test_")
                    )
                    if not is_test_or_doc and contains_unredacted_credentials and contains_unredacted_credentials(content):
                        print(f"❌ Error: Unredacted credential pattern found in '{f}'.")
                        found_secrets = True
                    else:
                        for pattern, name in SECRET_PATTERNS:
                            if pattern.search(content):
                                print(f"❌ Error: Potential {name} found in '{f}'.")
                                found_secrets = True
            except Exception:
                continue

    if found_secrets:
        print("\n🚫 Commit blocked: Secrets detected in staged files.")
        print("Please scrub credentials before committing.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
