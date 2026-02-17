#!/usr/bin/env python3
"""
Code Simplifier Agent (Evolutionary Driver Component).

1. Scans codebase for high-complexity functions (Score > 15).
2. Uses LLM to propose a "Flattened" version.
3. Verifies syntax.
"""

import argparse
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parents[2] / "src"))

from cohezion.healing.deep_audit import DeepAuditor


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CodeSimplifier")


class CodeSimplifier:
    def __init__(self, dry_run: bool = False):
        self.auditor = DeepAuditor()
        self.dry_run = dry_run

    def scan_for_targets(self, path: Path) -> list[tuple[str, int]]:
        """Find functions with complexity > 15."""
        targets = []
        if path.is_file():
            self.auditor.audit_file(path)
        else:
            for p in path.rglob("*.py"):
                self.auditor.audit_file(p)

        # DeepAuditor finds issues, we need to extract specific complexity ones
        for issue in self.auditor.issues:
            if "High complexity function" in issue.message:
                targets.append((issue.file_path, issue.line))

        return targets

    def simplify_target(self, file_path: str, line_no: int):
        """
        Uses an LLM to simplify the specific function.
        (Placeholder for MCP integration)
        """
        logger.info(f"Targeting {file_path}:{line_no} for simplification...")

        # TODO: Integrate with cohezion.mcp.swarm_server or similar
        # For now, we just identify and report.
        if self.dry_run:
            print(f"[DRY RUN] Would simplify {file_path}:{line_no}")
            return

        print(f"Please refactor {file_path} around line {line_no} to reduce complexity.")


def main():
    parser = argparse.ArgumentParser(description="Code Simplifier Agent")
    parser.add_argument("path", nargs="?", default="src/cohezion", help="Path to scan")
    parser.add_argument("--dry-run", action="store_true", help="Don't apply changes")
    args = parser.parse_args()

    simplifier = CodeSimplifier(dry_run=args.dry_run)
    targets = simplifier.scan_for_targets(Path(args.path))

    if not targets:
        logger.info("✨ No high-complexity targets found. Codebase is elegant.")
        return

    logger.info(f"🔍 Found {len(targets)} targets for simplification.")
    for t in targets[:5]:  # Show top 5
        simplifier.simplify_target(t[0], t[1])


if __name__ == "__main__":
    main()
