#!/usr/bin/env python3
import os
import subprocess
import sys


MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


def _git_paths(*args):
    """Run a git command with -z and return its NUL-separated paths, unquoted.

    Without -z git quotes names containing non-ASCII, tab, newline, `"` or `\\`
    ("caf\\303\\251.env"), and a quoted name matches no real file or index entry.
    """
    result = subprocess.run(
        ["git", *args, "-z"], capture_output=True, text=True, errors="surrogateescape", check=True
    )
    return [p for p in result.stdout.split("\0") if p]


def get_staged_files():
    try:
        return _git_paths("diff", "--cached", "--name-only")
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

    # Check for ignored files that are somehow staged
    # (Rare but happens with git add -f)
    # Scoped to the STAGED paths: `ls-files -i -c` alone lists every TRACKED file matching an
    # ignore pattern, so a tree carrying tracked-then-ignored files blocked every commit
    # regardless of what was staged (observed 2026-09-21: ~200 unrelated paths). Intersect two
    # NUL-separated lists rather than passing paths as pathspecs: no quoting mismatch (a
    # force-added "café.env" must still block) and no argv length limit on huge commits.
    staged_set = set(staged_files)
    try:
        ignored_tracked = _git_paths("ls-files", "-i", "-c", "--exclude-standard")
    except subprocess.CalledProcessError:
        ignored_tracked = []
    ignored_staged = [p for p in ignored_tracked if p in staged_set]

    if ignored_staged:
        print("\n🚫 Commit blocked: Some staged files match .gitignore patterns.")
        for f in ignored_staged:
            print(f"   - {f}")
        print("Please unstage them with 'git rm --cached <file>'.")
        sys.exit(1)

    # 3. Secret Scanning
    import re

    SECRET_PATTERNS = [
        (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "Google Cloud API Key"),
        (re.compile(r"sk-[a-zA-Z0-9]{48}"), "OpenAI API Key"),
        (re.compile(r"xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}"), "Slack Token"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
        (re.compile(r"PRIVATE\s+KEY"), "Private Key"),
    ]

    found_secrets = False
    for f in staged_files:
        if os.path.isfile(f):
            try:
                with open(f, encoding="utf-8") as file_content:
                    content = file_content.read()
                    for pattern, name in SECRET_PATTERNS:
                        if pattern.search(content):
                            print(f"❌ Error: Potential {name} found in '{f}'.")
                            found_secrets = True
            except Exception:
                continue

    if found_secrets:
        print("\n🚫 Commit blocked: Secrets detected in staged files.")
        print("Please use BitwardenVault for all sensitive credentials.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
