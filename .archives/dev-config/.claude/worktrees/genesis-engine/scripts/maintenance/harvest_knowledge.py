#!/usr/bin/env python3
"""
Cohezion Historical Knowledge Harvester.
Iterates through all branches, extracts unique agent journeys and journal entries,
and consolidates them into the Vault before archival.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

VAULT_HISTORICAL_PATH = Path("vault/historical_harvest")
JOURNAL_PATH = "src/cohezion/knowledge_graph/MISSION_JOURNAL.md"
JOURNEY_DIR = "data/universe"


@dataclass
class HarvestResult:
    branch: str
    journeys_found: int
    new_journeys: int
    journal_entries_found: int


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_file_content_from_branch(branch: str, file_path: str) -> str | None:
    try:
        return run_git(["show", f"{branch}:{file_path}"])
    except subprocess.CalledProcessError:
        return None


def get_file_list_from_branch(branch: str, dir_path: str) -> list[str]:
    try:
        output = run_git(["ls-tree", "-r", "--name-only", branch, dir_path])
        return [line.strip() for line in output.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        return []


def get_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def harvest_branch(branch: str, master_hashes: set[str]) -> HarvestResult:
    logger.info(f"Harvesting knowledge from branch: {branch}")

    # 1. Harvest Journeys
    branch_journeys = get_file_list_from_branch(branch, JOURNEY_DIR)
    new_journeys_count = 0

    for journey_path in branch_journeys:
        content = get_file_content_from_branch(branch, journey_path)
        if content:
            h = get_hash(content)
            if h not in master_hashes:
                # Store in historical vault
                branch_clean = branch.replace("/", "_")
                dest = VAULT_HISTORICAL_PATH / "journeys" / branch_clean
                dest.mkdir(parents=True, exist_ok=True)
                (dest / Path(journey_path).name).write_text(content)
                master_hashes.add(h)
                new_journeys_count += 1

    # 2. Harvest Journal Entries
    journal_content = get_file_content_from_branch(branch, JOURNAL_PATH)
    entries_found = 0
    if journal_content:
        # Simple heuristic: split by '### [' which usually starts a session entry
        entries = journal_content.split("### [")
        for entry in entries[1:]:  # skip preamble
            full_entry = "### [" + entry
            h = get_hash(full_entry)
            if h not in master_hashes:
                branch_clean = branch.replace("/", "_")
                dest = VAULT_HISTORICAL_PATH / "journals" / branch_clean
                dest.mkdir(parents=True, exist_ok=True)
                # Use first line as filename
                entry_title = entry.split("]")[0].replace(" ", "_").replace("/", "_")
                (dest / f"{entry_title}_{h[:8]}.md").write_text(full_entry)
                master_hashes.add(h)
                entries_found += 1

    return HarvestResult(branch, len(branch_journeys), new_journeys_count, entries_found)


def main() -> None:
    VAULT_HISTORICAL_PATH.mkdir(parents=True, exist_ok=True)

    # Load current master hashes to avoid duplicates
    master_hashes = set()
    logger.info("Indexing current main branch knowledge...")

    # Index current journeys
    if Path(JOURNEY_DIR).exists():
        for f in Path(JOURNEY_DIR).glob("*.json"):
            master_hashes.add(get_hash(f.read_text()))

    # Index current journal
    if Path(JOURNAL_PATH).exists():
        journal_content = Path(JOURNAL_PATH).read_text()
        entries = journal_content.split("### [")
        for entry in entries[1:]:
            master_hashes.add(get_hash("### [" + entry))

    # Get all local branches
    branches = [b.strip() for b in run_git(["branch", "--format=%(refname:short)"]).splitlines() if b.strip()]

    results = []
    for branch in branches:
        if branch in ["main", "master", "HEAD", "feat/epic-5-shadowscripter-v1.3.0"]:
            continue
        try:
            results.append(harvest_branch(branch, master_hashes))
        except Exception as e:
            logger.error(f"Failed to harvest {branch}: {e}")

    # Summary
    logger.info("\n--- Harvest Summary ---")
    total_new_journeys = sum(r.new_journeys for r in results)
    total_new_entries = sum(r.journal_entries_found for r in results)

    for r in results:
        if r.new_journeys > 0 or r.journal_entries_found > 0:
            logger.info(
                f"Branch '{r.branch}': {r.new_journeys} new journeys, {r.journal_entries_found} new journal entries"
            )

    logger.info(f"\nTotal Harvested: {total_new_journeys} journeys, {total_new_entries} journal entries.")
    logger.info(f"All artifacts saved to: {VAULT_HISTORICAL_PATH}")


if __name__ == "__main__":
    main()
