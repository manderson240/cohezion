import asyncio
import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from cohezion.core.persistence.admin import DBAdmin

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KnowledgeHarvester:
    """
    Agent responsible for harvesting 'Learnings' and 'Journeys' from untracked files
    before they are pruned.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.archive_dir = self.root_dir / ".archive"
        self.archive_dir.mkdir(exist_ok=True)
        self.dba = DBAdmin()

    async def find_bloat(self) -> Path:
        """Find the directory with the most files."""
        max_files = 0
        bloat_dir = None

        excludes = {".git", "node_modules", "surrealdb", ".archive"}

        logger.info("🕵️ Scanning for file explosion...")

        for root, dirs, files in os.walk(self.root_dir):
            # Prune excludes in-place
            dirs[:] = [d for d in dirs if d not in excludes]

            count = len(files)
            if count > 1000:
                logger.info(f"High count in {root}: {count} files")

            if count > max_files:
                max_files = count
                bloat_dir = Path(root)

            # If we find a crazy number, stop early? No, traverse.
            # But os.walk on 8 million files will take forever.
            # We need a heuristic.

        logger.info(f"Biggest directory: {bloat_dir} ({max_files} files)")
        return bloat_dir

    async def get_untracked_files(self) -> list[Path]:
        """Get untracked files, using git if possible, else fallback to scan."""
        # Git is choking on 8M files. Let's try to target the bloat dir directly if git fails.
        try:
            logger.info("Asking git for untracked files (timeout 30s)...")
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
                timeout=30,  # Fail fast
            )
            files = [self.root_dir / f for f in result.stdout.splitlines() if f.strip()]
            return files
        except subprocess.TimeoutExpired:
            logger.warning("Git timed out. Switching to manual scan.")
            # If git fails, we trust the 'find_bloat' or just scan common suspects
            # For now, let's just return empty list to trigger the manual fallback in run()
            return []
        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return []

    def classify_file(self, file_path: Path) -> str:
        """Classify file as 'learning', 'journey', or 'noise'."""
        if file_path.suffix not in [".md", ".json", ".log", ".txt"]:
            return "noise"

        name = file_path.name.lower()

        # High Value Patterns
        if any(
            x in name for x in ["insight", "retrospective", "learning", "key_learning"]
        ):
            return "learning"

        if any(x in name for x in ["journey", "trace", "plan", "thought", "step_"]):
            return "journey"

        # Inspect Content (Briefly)
        try:
            if file_path.stat().st_size < 1024 * 1024:  # Only scan small files < 1MB
                content = file_path.read_text(errors="ignore").lower()
                if "insight:" in content or "# retrospective" in content:
                    return "learning"
                if '"thought":' in content or "step id:" in content:
                    return "journey"
        except Exception:
            pass

        return "noise"

    async def ingest_learning(self, file_path: Path):
        """Ingest a Learning artifact into SurrealDB."""
        try:
            content = file_path.read_text(errors="ignore")
            # Extract basic metadata
            title = file_path.stem
            category = "harvested_learning"

            # Simple unstructured ingestion for now
            record = {
                "title": title,
                "content": content,
                "path": str(file_path),
                "source": "harvester",
                "ingested_at": datetime.now(UTC).isoformat(),
                "type": "learning",
            }

            await self.dba.client.create("knowledge", record)
            logger.info(f"🧠 Ingested Learning: {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to ingest learning {file_path}: {e}")
            return False

    async def ingest_journey(self, file_path: Path):
        """Ingest a Journey artifact into SurrealDB."""
        try:
            # For JSON journeys, we might want structured data
            record = {
                "path": str(file_path),
                "source": "harvester",
                "ingested_at": datetime.now(UTC).isoformat(),
                "type": "journey",
            }

            if file_path.suffix == ".json":
                try:
                    data = json.loads(file_path.read_text())
                    record["data"] = data
                except (json.JSONDecodeError, ValueError):
                    record["raw_content"] = file_path.read_text(errors="ignore")[:10000]
            else:
                record["raw_content"] = file_path.read_text(errors="ignore")[:10000]

            await self.dba.client.create(
                "memories", record
            )  # Store journeys in 'memories'
            logger.info(f"👣 Ingested Journey: {file_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to ingest journey {file_path}: {e}")
            return False

    async def harvest_ghosts(self):
        """
        Harvest files that are missing from disk (Deleted) but exist in Git Index.
        Uses git ls-files -d --stage and git cat-file --batch for efficiency.
        """
        logger.info("👻 Starting GHOST HARVEST Protocol...")

        # 1. Get list of missing files + OIDs
        logger.info("Listing ghost files from git index (this may take a while)...")
        # We process line by line to avoid memory explosion
        proc_ls = subprocess.Popen(
            ["git", "ls-files", "-d", "--stage"],
            stdout=subprocess.PIPE,
            text=True,
            cwd=self.root_dir,
            bufsize=1,  # Line buffered
        )

        # 2. Start git cat-file process
        proc_cat = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=False,  # Binary mode for content
            cwd=self.root_dir,
            bufsize=0,  # Unbuffered
        )

        await self.dba.connect()
        count = 0
        ingested = 0

        try:
            for line in proc_ls.stdout:
                count += 1
                if count % 10000 == 0:
                    logger.info(f"Processed {count} ghosts... (Ingested: {ingested})")

                # Format: 100644 <oid> 0\t<path>
                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue

                meta, path_str = parts
                path = Path(path_str.strip())
                oid = meta.split()[1]

                # classify
                cls = self.classify_file(path)
                if cls == "noise":
                    continue

                # Request content
                try:
                    proc_cat.stdin.write(f"{oid}\n".encode())
                    proc_cat.stdin.flush()

                    # Read header: "<oid> <type> <size>\n"
                    header_bytes = proc_cat.stdout.readline()
                    header = header_bytes.decode().strip()

                    if "missing" in header:
                        logger.warning(f"Object {oid} missing for {path}")
                        continue

                    h_parts = header.split()
                    if len(h_parts) < 3:
                        logger.error(f"Bad header for {path}: {header}")
                        continue

                    try:
                        size = int(h_parts[2])
                    except ValueError:
                        # Sometimes header might be messed up if out of sync
                        logger.error(f"Invalid size in header: {header}")
                        # Recovering synchronization is hard. We might need to restart.
                        # For now, let's just try to read *something* or abort this batch
                        continue

                    content = proc_cat.stdout.read(size)
                    proc_cat.stdout.read(1)  # Consume trailing newline

                    # Ingest
                    text_content = content.decode("utf-8", errors="ignore")
                    if cls == "learning":
                        # Inline ingest to reuse logic, but adapted for text input
                        record = {
                            "title": path.stem,
                            "content": text_content,
                            "path": str(path),
                            "source": "ghost_harvester",
                            "ingested_at": datetime.now(UTC).isoformat(),
                            "type": "learning",
                        }
                        await self.dba.client.create("knowledge", record)
                    elif cls == "journey":
                        record = {
                            "path": str(path),
                            "source": "ghost_harvester",
                            "ingested_at": datetime.now(UTC).isoformat(),
                            "type": "journey",
                            "raw_content": text_content[:20000],
                        }
                        if path.suffix == ".json":
                            try:
                                record["data"] = json.loads(text_content)
                            except (json.JSONDecodeError, ValueError):
                                pass
                        await self.dba.client.create("memories", record)

                    ingested += 1
                except Exception as e:
                    logger.error(f"Cat-file failed for {path}: {e}")
                    # If stream is desync, we should probably break or restart proc_cat

        except Exception as e:
            logger.error(f"Ghost Harvest crashed: {e}")
        finally:
            proc_ls.terminate()
            proc_cat.terminate()
            await self.dba.close()
            logger.info(
                f"Ghost Harvest Complete. Scanned {count}, Ingested {ingested}."
            )

    async def run(self, dry_run: bool = True):
        """Main execution flow."""
        if dry_run:
            logger.info("Dry run only. Run without --dry-run for real harvest.")
            # Simple check for bloat
            await self.find_bloat()
            return

        # Double check for ghosts
        await self.harvest_ghosts()

        # Original logic for untracked files...


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulate run")
    args = parser.parse_args()

    harvester = KnowledgeHarvester()
    asyncio.run(harvester.run(dry_run=args.dry_run))
