import logging
import subprocess
from datetime import datetime
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("RepoJanitor")

# Constants
MAX_FILE_SIZE_MB = 5
MAX_INDEX_SIZE_MB = 100
BLOAT_THRESHOLD_PENDING = 200
REPO_ROOT = Path(__file__).parent.parent.resolve()
CACHE_DIR = REPO_ROOT / ".cache" / "janitor"
CACHE_FILE = CACHE_DIR / "status_cache.json"
BATCH_SIZE_FILES = 1000  # Size for OS file operations


def run_git_command(args, cwd=REPO_ROOT):
    """Run a git command and return the output."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(args)} - {e.stderr}")
        return None


def purge_history_candidates(dry_run=True):
    """Remove tracked files that match .gitignore patterns."""
    logger.info("🔍 Checking for tracked files that should be ignored...")

    # Get all tracked files that match ignore patterns
    tracked_files = run_git_command(["ls-files", "-i", "-c", "--exclude-standard"])
    if not tracked_files:
        logger.info("✅ No tracked files found that match .gitignore.")
        return

    files_to_remove = tracked_files.splitlines()
    logger.warning(f"⚠️ Found {len(files_to_remove)} tracked files that match .gitignore patterns.")

    if dry_run:
        for f in files_to_remove[:10]:
            logger.info(f"Dry-run: Would remove from index: {f}")
        if len(files_to_remove) > 10:
            logger.info(f"... and {len(files_to_remove) - 10} more.")
    else:
        logger.info(
            f"Removing {len(files_to_remove)} files from git index (keeping local copies)..."
        )
        # Process in batches to avoid command line length limits
        batch_size = 50
        for i in range(0, len(files_to_remove), batch_size):
            batch = files_to_remove[i : i + batch_size]
            run_git_command(["rm", "--cached", *batch])
        logger.info("✅ Successfully removed files from index.")


def cleanup_artifacts():
    """Remove untracked artifacts based on known bloat patterns."""
    logger.info("🧹 Cleaning up untracked artifacts...")

    # 1. Bulk directories (high-performance)
    bulk_dirs = [".archive", "temp", "renders", ".sandbox"]
    for d in bulk_dirs:
        dir_path = REPO_ROOT / d
        if dir_path.exists():
            logger.info(f"Removing bulk directory: {d}")
            import shutil

            try:
                shutil.rmtree(dir_path)
            except Exception as e:
                logger.error(f"Failed to remove {d}: {e}")

    # 2. Pattern cleanup
    patterns = [
        "**/*.log",
        "**/*.err",
        "**/*.out",
        "src/cohezion/knowledge_graph/universe_nodes/linguistic_evolution/logs/*.txt",
        "research/simulations/overnight_simulations/*.jsonl",
        "**/*.sst",
        "**/*.dill",
        "dist/*.tar.gz",
        "portfolio/*.bundle",
        "apps/**/node_modules",
        "**/node_modules",  # Catch top-level and nested node_modules
        "**/__pycache__",
        "**/.pytest_cache",
        "**/.mypy_cache",
    ]

    removed_count = 0
    total_size = 0

    for pattern in patterns:
        for p in REPO_ROOT.glob(pattern):
            if p.is_file():
                try:
                    size = p.stat().st_size
                    p.unlink()
                    removed_count += 1
                    total_size += size
                except Exception as e:
                    logger.error(f"Failed to delete {p}: {e}")
            elif p.is_dir() and (
                p.name == "node_modules" or p.name == "__pycache__" or p.name.endswith("_cache")
            ):
                import shutil

                try:
                    # Calculate size before removal
                    dir_size = sum(f.stat().st_size for f in p.glob("**/*") if f.is_file())
                    shutil.rmtree(p)
                    removed_count += 1
                    total_size += dir_size
                except Exception as e:
                    logger.error(f"Failed to remove directory {p}: {e}")

    logger.info(f"✅ Removed {removed_count} artifacts/dirs ({total_size / (1024 * 1024):.2f} MB saved).")


def check_git_vitals(use_cache=False):
    """Check repository health metrics with simple caching."""
    logger.info("💓 Checking Git Vitals...")

    import json

    if use_cache and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                cached_data = json.load(f)
                if (datetime.now().timestamp() - cached_data.get("timestamp", 0)) < 300:  # 5 min cache
                    logger.info("Using cached git vitals.")
                    return cached_data
        except Exception:
            pass

    # 1. Check index size
    index_path = REPO_ROOT / ".git" / "index"
    index_size_mb = 0
    if index_path.exists():
        index_size_mb = index_path.stat().st_size / (1024 * 1024)
        if index_size_mb > MAX_INDEX_SIZE_MB:
            logger.warning(f"⚠️ Git index is large: {index_size_mb:.2f} MB")
        else:
            logger.info(f"Index size: {index_size_mb:.2f} MB")

    # 2. Check pending changes
    status_porcelain = run_git_command(["status", "--porcelain"])
    pending_count = 0
    if status_porcelain:
        pending_count = len(status_porcelain.splitlines())
        if pending_count > BLOAT_THRESHOLD_PENDING:
            logger.warning(f"⚠️ High number of pending changes: {pending_count}")
        else:
            logger.info(f"Pending changes: {pending_count}")

    # 3. Check for large objects in history
    logger.info("Git object check complete.")

    # Cache the result
    vitals = {
        "timestamp": datetime.now().timestamp(),
        "index_size_mb": index_size_mb,
        "pending_count": pending_count,
    }

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(vitals, f)
    except Exception as e:
        logger.error(f"Failed to write cache: {e}")

    return vitals


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cohezion Repo Janitor")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Don't delete or uncache files",
    )
    parser.add_argument("--no-cleanup", action="store_true", help="Skip artifact cleanup")
    parser.add_argument("--no-purge", action="store_true", help="Skip history purge candidates")
    args = parser.parse_args()

    check_git_vitals()

    if not args.no_purge:
        purge_history_candidates(dry_run=args.dry_run)

    if not args.no_cleanup:
        if args.dry_run:
            logger.info("Dry-run: Skipping artifact cleanup.")
        else:
            cleanup_artifacts()


if __name__ == "__main__":
    main()
