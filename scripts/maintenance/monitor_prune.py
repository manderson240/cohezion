import subprocess
import time
from pathlib import Path


LOG_FILE = Path("scripts/maintenance/prune_status.log")
STATUS_FILE = Path("PRUNE_STATUS.md")


def check_progress():
    """Checks the progress of the surgical prune."""
    try:
        # Check process existence
        result = subprocess.run(
            ["pgrep", "-f", "surgical_prune.py"], capture_output=True, text=True
        )
        if not result.stdout.strip():
            update_status("DONE", "Process not found (Finished or Failed).")
            return False

        # Read the log file if it exists (assuming surgical_prune writes to stdout/file)
        # Since we ran it interactively, we look at the last update time or git index size

        # Check git index size directly
        index_size = Path(".git/index").stat().st_size / (1024 * 1024)

        update_status("RUNNING", f"Git Index Size: {index_size:.2f} MB")
        return True

    except Exception as e:
        update_status("ERROR", str(e))
        return False


def update_status(state, details):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    content = f"""# Prune Status
**Updated**: {timestamp}
**State**: {state}
**Details**: {details}
"""
    STATUS_FILE.write_text(content)
    print(f"[{timestamp}] {state}: {details}")


if __name__ == "__main__":
    print("Starting Prune Monitor...")
    while check_progress():
        time.sleep(60)
