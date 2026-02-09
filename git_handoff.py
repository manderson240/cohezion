#!/usr/bin/env python3
"""
ASCENDED COHEZION - Safe Git Handoff Tool
Ensures clean handoffs between development sessions

Usage: python3 git_handoff.py [prepare|resume|status]
"""

import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path


def run_cmd(cmd, capture=True):
    """Run shell command safely"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True,
            cwd="/home/mike-anderson/dev/cohezion",
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_branch_status():
    """Get current git branch status"""
    success, stdout, stderr = run_cmd("git status --porcelain")
    if not success:
        return None

    # Parse status
    staged = []
    unstaged = []
    untracked = []

    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        filename = line[3:]

        if status.startswith("M") or status.startswith("A") or status.startswith("D"):
            if status[0] != " ":
                staged.append(filename)
            if status[1] != " ":
                unstaged.append(filename)
        elif status == "??":
            untracked.append(filename)

    return {
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "clean": not (staged or unstaged),
    }


def prepare_handoff():
    """Prepare for handoff - commit or stash work"""
    print("🔄 Preparing git handoff...")
    print()

    status = get_branch_status()
    if not status:
        print("❌ Error: Not in a git repository")
        return 1

    if status["clean"] and not status["untracked"]:
        print("✅ Working tree clean - ready for handoff")

        # Show last commit
        _, stdout, _ = run_cmd("git log -1 --oneline")
        print(f"   Last commit: {stdout.strip()}")

        # Create handoff marker
        handoff_file = Path("/home/mike-anderson/dev/cohezion/.handoff.json")
        handoff_data = {
            "timestamp": datetime.now().isoformat(),
            "branch": run_cmd("git branch --show-current")[1].strip(),
            "last_commit": stdout.strip(),
            "status": "clean",
        }
        handoff_file.write_text(json.dumps(handoff_data, indent=2))
        print(f"   Handoff marker saved: {handoff_file}")

        return 0

    # Show current state
    print("📋 Current changes:")
    if status["staged"]:
        print(
            f"   Staged ({len(status['staged'])}): {', '.join(status['staged'][:3])}{'...' if len(status['staged']) > 3 else ''}"
        )
    if status["unstaged"]:
        print(
            f"   Unstaged ({len(status['unstaged'])}): {', '.join(status['unstaged'][:3])}{'...' if len(status['unstaged']) > 3 else ''}"
        )
    if status["untracked"]:
        print(
            f"   Untracked ({len(status['untracked'])}): {', '.join(status['untracked'][:3])}{'...' if len(status['untracked']) > 3 else ''}"
        )

    print()
    print("💡 Options:")
    print("   1. Commit changes: git add -A && git commit -m 'WIP: handoff'")
    print("   2. Stash changes: git stash push -m 'handoff'")
    print("   3. Continue without committing (not recommended)")
    print()

    response = input("Commit changes? (y/n/c): ").lower()

    if response == "y":
        # Stage and commit
        print("📝 Committing changes...")
        run_cmd("git add -A")
        success, stdout, stderr = run_cmd("git commit -m 'WIP: session handoff'")
        if success:
            print("✅ Changes committed successfully")

            # Create handoff marker
            handoff_file = Path("/home/mike-anderson/dev/cohezion/.handoff.json")
            handoff_data = {
                "timestamp": datetime.now().isoformat(),
                "branch": run_cmd("git branch --show-current")[1].strip(),
                "last_commit": stdout.strip().split("\n")[0],
                "status": "committed",
            }
            handoff_file.write_text(json.dumps(handoff_data, indent=2))
            print(f"   Handoff marker saved: {handoff_file}")
            return 0
        else:
            print(f"❌ Commit failed: {stderr}")
            return 1

    elif response == "n":
        # Stash
        print("📦 Stashing changes...")
        success, stdout, stderr = run_cmd("git stash push -m 'handoff'")
        if success:
            print("✅ Changes stashed successfully")

            # Create handoff marker
            handoff_file = Path("/home/mike-anderson/dev/cohezion/.handoff.json")
            handoff_data = {
                "timestamp": datetime.now().isoformat(),
                "branch": run_cmd("git branch --show-current")[1].strip(),
                "stash": True,
                "status": "stashed",
            }
            handoff_file.write_text(json.dumps(handoff_data, indent=2))
            print(f"   Handoff marker saved: {handoff_file}")
            return 0
        else:
            print(f"❌ Stash failed: {stderr}")
            return 1

    else:
        print("⚠️  Continuing without committing (not recommended for handoff)")
        return 0


def resume_session():
    """Resume from handoff - check status and guide user"""
    print("▶️  Resuming session...")
    print()

    # Check for handoff marker
    handoff_file = Path("/home/mike-anderson/dev/cohezion/.handoff.json")
    if handoff_file.exists():
        try:
            handoff_data = json.loads(handoff_file.read_text())
            print(f"📋 Found handoff from: {handoff_data.get('timestamp', 'unknown')}")
            print(f"   Branch: {handoff_data.get('branch', 'unknown')}")
            print(f"   Status: {handoff_data.get('status', 'unknown')}")

            if handoff_data.get("status") == "stashed":
                print()
                print("💡 Changes were stashed. To restore:")
                print("   git stash pop")

                response = input("\nRestore stashed changes? (y/n): ").lower()
                if response == "y":
                    success, stdout, stderr = run_cmd("git stash pop")
                    if success:
                        print("✅ Stashed changes restored")
                        handoff_file.unlink()
                    else:
                        print(f"❌ Restore failed: {stderr}")
                        return 1

            elif handoff_data.get("status") == "committed":
                print("✅ Changes were committed - working tree is clean")
                handoff_file.unlink()

            elif handoff_data.get("status") == "clean":
                print("✅ Working tree was clean on handoff")
                handoff_file.unlink()

        except Exception as e:
            print(f"⚠️  Error reading handoff file: {e}")

    # Check current status
    print()
    print("📊 Current repository status:")

    status = get_branch_status()
    if status:
        if status["clean"]:
            print("   ✅ Working tree clean")
        else:
            print(
                f"   ⚠️  {len(status['staged'])} staged, {len(status['unstaged'])} unstaged changes"
            )

        if status["untracked"]:
            print(f"   📝 {len(status['untracked'])} untracked files")

    # Show recent commits
    print()
    print("📝 Recent commits:")
    success, stdout, _ = run_cmd("git log --oneline -5")
    if success:
        for line in stdout.strip().split("\n"):
            print(f"   {line}")

    return 0


def show_status():
    """Show current repository status"""
    print("📊 Repository Status")
    print("=" * 50)
    print()

    # Branch
    success, stdout, _ = run_cmd("git branch --show-current")
    if success:
        print(f"🌿 Branch: {stdout.strip()}")

    # Status
    status = get_branch_status()
    if status:
        print(f"📋 Working tree: {'clean' if status['clean'] else 'dirty'}")
        if status["staged"]:
            print(f"   Staged: {len(status['staged'])} files")
        if status["unstaged"]:
            print(f"   Unstaged: {len(status['unstaged'])} files")
        if status["untracked"]:
            print(f"   Untracked: {len(status['untracked'])} files")

    # Last commit
    success, stdout, _ = run_cmd("git log -1 --oneline")
    if success:
        print(f"📝 Last commit: {stdout.strip()}")

    # Check for handoff marker
    handoff_file = Path("/home/mike-anderson/dev/cohezion/.handoff.json")
    if handoff_file.exists():
        print()
        print("🔄 Handoff marker found (session was prepared for handoff)")

    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 git_handoff.py [prepare|resume|status]")
        return 1

    command = sys.argv[1].lower()

    if command == "prepare":
        return prepare_handoff()
    elif command == "resume":
        return resume_session()
    elif command == "status":
        return show_status()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python3 git_handoff.py [prepare|resume|status]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
