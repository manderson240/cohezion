import logging
import subprocess
from datetime import datetime
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("WorkManager")

REPO_ROOT = Path(__file__).parent.parent.resolve()
JANITOR_CACHE_FILE = REPO_ROOT / ".cache" / "janitor" / "status_cache.json"


def run_git_command(args, cwd=REPO_ROOT):
    """Run a git command and return the output."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(args)} - {e.stderr}")
        return None


def start_task(task_name):
    """Create a new lean branch for a task."""
    logger.info(f"🚀 Starting task: {task_name}")

    # Sanitize task name
    branch_name = task_name.replace(" ", "-").lower()

    # Check if we have uncommitted changes
    status = run_git_command(["status", "--porcelain"])
    if status:
        logger.warning("⚠️ You have uncommitted changes. Stashing them before switching...")
        run_git_command(["stash", "save", f"Auto-stash before task: {task_name}"])

    # Create and switch to branch
    logger.info(f"Creating branch: {branch_name}")
    result = run_git_command(["checkout", "-b", branch_name])
    if result is not None:
        logger.info(f"✅ Switched to new branch: {branch_name}")
    else:
        # Try switching if it already exists
        run_git_command(["checkout", branch_name])


def checkpoint(message=None):
    """Save current work in a checkpoint commit or stash."""
    if not message:
        message = f"Checkpoint: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    logger.info("💾 Creating checkpoint...")

    # Stage current changes (respecting .gitignore)
    run_git_command(["add", "."])

    # Check if anything is staged
    staged = run_git_command(["diff", "--cached", "--name-only"])
    if not staged:
        logger.info("✅ No changes to checkpoint.")
        return

    # Commit
    run_git_command(["commit", "-m", message])
    logger.info(f"✅ Checkpoint created: {message}")


def show_status():
    """Show task-oriented status with cache awareness."""
    branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    logger.info(f"📍 Active Task: {branch}")

    import json

    if JANITOR_CACHE_FILE.exists():
        try:
            with open(JANITOR_CACHE_FILE) as f:
                cache = json.load(f)
                if (datetime.now().timestamp() - cache.get("timestamp", 0)) < 300:
                    logger.info(f"Pending changes (cached): {cache.get('pending_count')}")
                    if cache.get("pending_count", 0) > 1000:
                        logger.warning("⚠️ High bloat detected. Run 'scripts/repo_janitor.py' for detailed status.")
                        return
        except Exception:
            pass

    status = run_git_command(["status", "--short"])
    if status:
        lines = status.splitlines()
        logger.info(f"Pending changes ({len(lines)}):")
        for line in lines[:20]:
            logger.info(f"  {line}")
        if len(lines) > 20:
            logger.info(f"  ... and {len(lines) - 20} more.")
    else:
        logger.info("✅ Working directory clean.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cohezion Work Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # start-task
    start_parser = subparsers.add_parser("start-task", help="Start a new task branch")
    start_parser.add_argument("name", help="Name of the task")

    # checkpoint
    checkpoint_parser = subparsers.add_parser("checkpoint", help="Create a savepoint commit")
    checkpoint_parser.add_argument("-m", "--message", help="Checkpoint message")

    # status
    subparsers.add_parser("status", help="Show task status")

    args = parser.parse_args()

    if args.command == "start-task":
        start_task(args.name)
    elif args.command == "checkpoint":
        checkpoint(args.message)
    elif args.command == "status":
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
