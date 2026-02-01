#!/usr/bin/env python3
import sys
import subprocess
import os

MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

def get_staged_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.splitlines()
    except subprocess.CalledProcessError:
        return []

def check_file_size(file_path):
    if not os.path.exists(file_path):
        return True
    
    size = os.path.getsize(file_path)
    if size > MAX_SIZE_BYTES:
        print(f"❌ Error: File '{file_path}' is too large ({size / (1024*1024):.2f} MB).")
        print(f"   Max allowed size is {MAX_SIZE_BYTES / (1024*1024):.2f} MB.")
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
    ignored_staged = subprocess.run(
        ["git", "ls-files", "-i", "-c", "--exclude-standard"],
        capture_output=True,
        text=True
    ).stdout.splitlines()

    if ignored_staged:
        print("\n🚫 Commit blocked: Some staged files match .gitignore patterns.")
        for f in ignored_staged:
            print(f"   - {f}")
        print("Please unstage them with 'git rm --cached <file>'.")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
