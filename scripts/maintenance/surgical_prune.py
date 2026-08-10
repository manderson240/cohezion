import os
import subprocess
import sys


def batch_prune(batch_size=50000):
    """
    Efficiently remove deleted files from the git index using update-index.
    Uses batching to avoid command line length limits and provide progress.
    """
    print("Listing deleted files...")
    # Get list of deleted files
    try:
        proc = subprocess.Popen(["git", "ls-files", "--deleted"], stdout=subprocess.PIPE, text=True)
    except Exception as e:
        print(f"Failed to list files: {e}")
        return

    batch = []
    count = 0
    total_removed = 0

    print(f"Starting batch pruning (Batch size: {batch_size})...")

    # Process stream
    for line in proc.stdout:
        filepath = line.strip()
        batch.append(filepath)
        count += 1

        if count >= batch_size:
            _execute_batch(batch)
            total_removed += count
            print(f"Pruned {total_removed} files...")
            batch = []
            count = 0

    # Final batch
    if batch:
        _execute_batch(batch)
        total_removed += count

    print(f"Complete. Removed {total_removed} files from index.")


def _execute_batch(files):
    # git update-index --remove --stdin is efficient
    # We pass the files via stdin
    proc = subprocess.Popen(
        ["git", "update-index", "--remove", "--stdin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
    )
    proc.communicate(input="\n".join(files).encode())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Allow passing "unlock" to try removing lockfile
        if sys.argv[1] == "unlock" and os.path.exists(".git/index.lock"):
            print("Removing .git/index.lock...")
            os.remove(".git/index.lock")

    batch_prune()
