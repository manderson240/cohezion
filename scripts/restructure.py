#!/usr/bin/env python3
"""Directory Restructure Migration Script.

Consolidates Cohezion codebase to a cleaner structure:

Before:
    src/cohezion/
        caching/
        cache_manager.py
        db/
        repositories.py
        swarm/agents/ (50+ agent files)

After:
    src/cohezion/
        core/
            cache/  (consolidated from caching/ + cache_manager.py)
            persistence/  (consolidated from db/ + repositories.py)
        agents/  (flat structure, moved from swarm/agents/)

Usage:
    uv run python scripts/restructure.py --dry-run  # Preview changes
    uv run python scripts/restructure.py --apply    # Apply changes

WARNING: This script modifies your file structure. Always run with --dry-run first!
"""

import argparse
import logging
import shutil
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("restructure")


class DirectoryRestructure:
    """Handles directory restructuring for Cohezion codebase."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.root = Path(__file__).parent.parent
        self.src = self.root / "src" / "cohezion"

        self.changes: list[dict[str, Any]] = []
        self.errors: list[str] = []

    def analyze_current_structure(self) -> dict[str, Any]:
        """Analyze current directory structure."""
        logger.info("=" * 60)
        logger.info("📊 ANALYZING CURRENT STRUCTURE")
        logger.info("=" * 60)

        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "caching_files": 0,
            "db_files": 0,
            "agent_files": 0,
        }

        # Count files in key directories
        caching_dir = self.src / "caching"
        if caching_dir.exists():
            stats["caching_files"] = len(list(caching_dir.glob("*.py")))

        db_dir = self.src / "db"
        if db_dir.exists():
            stats["db_files"] = len(list(db_dir.glob("*.py")))

        agents_dir = self.src / "swarm" / "agents"
        if agents_dir.exists():
            stats["agent_files"] = len(list(agents_dir.glob("*.py")))

        for _py_file in self.src.rglob("*.py"):
            stats["total_files"] += 1

        stats["total_dirs"] = len(list(self.src.rglob("*/")))

        logger.info(f"   Total Python files: {stats['total_files']}")
        logger.info(f"   Caching files: {stats['caching_files']}")
        logger.info(f"   DB files: {stats['db_files']}")
        logger.info(f"   Agent files: {stats['agent_files']}")

        return stats

    def plan_migration(self) -> dict[str, Any]:
        """Plan the directory migration."""
        logger.info("\n" + "=" * 60)
        logger.info("📋 PLANNING MIGRATION")
        logger.info("=" * 60)

        plan = {
            "steps": [],
            "files_to_move": [],
            "imports_to_update": [],
        }

        # Step 1: Create core/ directory structure
        plan["steps"].append(
            {
                "action": "create_directory",
                "path": str(self.src / "core"),
                "description": "Create core/ directory",
            }
        )

        plan["steps"].append(
            {
                "action": "create_directory",
                "path": str(self.src / "core" / "cache"),
                "description": "Create core/cache/ subdirectory",
            }
        )

        plan["steps"].append(
            {
                "action": "create_directory",
                "path": str(self.src / "core" / "persistence"),
                "description": "Create core/persistence/ subdirectory",
            }
        )

        plan["steps"].append(
            {
                "action": "create_directory",
                "path": str(self.src / "agents"),
                "description": "Create agents/ directory (flat structure)",
            }
        )

        # Step 2: Plan file moves
        # Move caching/ files to core/cache/
        caching_dir = self.src / "caching"
        if caching_dir.exists():
            for f in caching_dir.glob("*.py"):
                plan["files_to_move"].append(
                    {
                        "from": str(f),
                        "to": str(self.src / "core" / "cache" / f.name),
                    }
                )

        # Move cache_manager.py to core/cache/
        cache_manager = self.src / "cache_manager.py"
        if cache_manager.exists():
            plan["files_to_move"].append(
                {
                    "from": str(cache_manager),
                    "to": str(self.src / "core" / "cache" / "cache_manager.py"),
                }
            )

        # Move db/ files to core/persistence/ (except admin.py)
        db_dir = self.src / "db"
        if db_dir.exists():
            for f in db_dir.glob("*.py"):
                if f.name not in ["admin.py", "__init__.py"]:
                    plan["files_to_move"].append(
                        {
                            "from": str(f),
                            "to": str(self.src / "core" / "persistence" / f.name),
                        }
                    )

        # Move repositories.py to core/persistence/
        repos = self.src / "repositories.py"
        if repos.exists():
            plan["files_to_move"].append(
                {
                    "from": str(repos),
                    "to": str(self.src / "core" / "persistence" / "repositories.py"),
                }
            )

        # Move swarm/agents/*.py to agents/
        agents_dir = self.src / "swarm" / "agents"
        if agents_dir.exists():
            for f in agents_dir.glob("*.py"):
                if f.is_file() and not f.name.startswith("_"):
                    plan["files_to_move"].append(
                        {
                            "from": str(f),
                            "to": str(self.src / "agents" / f.name),
                        }
                    )

        # Step 3: Plan import updates
        plan["imports_to_update"] = [
            {
                "old_pattern": r"from cohezion\.caching import",
                "new_pattern": "from cohezion.core.cache import",
            },
            {
                "old_pattern": r"from cohezion\.cache_manager import",
                "new_pattern": "from cohezion.core.cache.cache_manager import",
            },
            {
                "old_pattern": r"from cohezion\.db\.",
                "new_pattern": "from cohezion.core.persistence.",
            },
            {
                "old_pattern": r"from cohezion\.repositories import",
                "new_pattern": "from cohezion.core.persistence.repositories import",
            },
            {
                "old_pattern": r"from cohezion\.swarm\.agents\.",
                "new_pattern": "from cohezion.agents.",
            },
        ]

        # Log plan
        logger.info(f"   Directories to create: {len([s for s in plan['steps'] if s['action'] == 'create_directory'])}")
        logger.info(f"   Files to move: {len(plan['files_to_move'])}")
        logger.info(f"   Import patterns to update: {len(plan['imports_to_update'])}")

        return plan

    def execute_migration(self) -> dict[str, Any]:
        """Execute the directory migration."""
        plan = self.plan_migration()

        logger.info("\n" + "=" * 60)
        logger.info("🚀 EXECUTING MIGRATION")
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("⚠️  DRY RUN - No changes will be made")

        report = {
            "dry_run": self.dry_run,
            "directories_created": 0,
            "files_moved": 0,
            "files_copied": 0,
            "imports_updated": 0,
            "errors": [],
        }

        # Create directories
        for step in plan["steps"]:
            if step["action"] == "create_directory":
                path = Path(step["path"])
                if self.dry_run:
                    logger.info(f"   [DRY RUN] Would create: {path}")
                else:
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"   ✅ Created: {path}")
                report["directories_created"] += 1

        # Move files
        for move in plan["files_to_move"]:
            from_path = Path(move["from"])
            to_path = Path(move["to"])

            if self.dry_run:
                logger.info(f"   [DRY RUN] Would move: {from_path.name} -> {to_path.parent.name}/")
            else:
                try:
                    to_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(from_path), str(to_path))
                    logger.info(f"   ✅ Moved: {from_path.name} -> {to_path.parent.name}/")
                    report["files_moved"] += 1
                except Exception as e:
                    logger.error(f"   ❌ Failed to move {from_path}: {e}")
                    report["errors"].append(str(e))

        # Update imports (simplified - would need more sophisticated implementation)
        logger.info("\n   📝 Note: Import updates would require running update_imports.py")
        logger.info("   Run: uv run python scripts/update_imports.py after migration")

        # Final report
        logger.info("\n" + "=" * 60)
        logger.info("📋 MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"   Directories created: {report['directories_created']}")
        logger.info(f"   Files moved: {report['files_moved']}")
        logger.info(f"   Errors: {len(report['errors'])}")

        if report["errors"]:
            for error in report["errors"]:
                logger.error(f"   {error}")

        return report

    def generate_import_updater(self) -> str:
        """Generate a script to update imports after migration."""
        script = '''#!/usr/bin/env python3
"""Update imports after directory restructure.

Run this after executing the directory restructure migration.

Usage:
    uv run python scripts/update_imports.py --dry-run  # Preview changes
    uv run python scripts/update_imports.py --apply    # Apply changes
"""

import argparse
import re
from pathlib import Path


def update_imports(dry_run: bool = True):
    """Update imports in all Python files."""
    root = Path("src/cohezion")

    import_mappings = [
        (r"from cohezion\\.caching import", "from cohezion.core.cache import"),
        (r"from cohezion\\.cache_manager import", "from cohezion.core.cache.cache_manager import"),
        (r"from cohezion\\.db\\.", "from cohezion.core.persistence."),
        (r"from cohezion\\.repositories import", "from cohezion.core.persistence.repositories import"),
        (r"from cohezion\\.swarm\\.agents\\.", "from cohezion.agents."),
    ]

    files_updated = 0

    for py_file in root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()
            original = content

            for old_pattern, new_pattern in import_mappings:
                content = re.sub(old_pattern, new_pattern, content)

            if content != original:
                files_updated += 1
                if dry_run:
                    print(f"   [DRY RUN] Would update: {py_file}")
                else:
                    py_file.write_text(content)
                    print(f"   ✅ Updated: {py_file}")

        except Exception as e:
            print(f"   ❌ Error processing {py_file}: {e}")

    print(f"\\n📊 Files updated: {files_updated}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update imports after restructure")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    args = parser.parse_args()

    if args.apply:
        update_imports(dry_run=False)
    else:
        update_imports(dry_run=True)
'''
        return script

    def save_import_updater(self):
        """Save the import updater script."""
        script_path = self.root / "scripts" / "update_imports.py"
        script = self.generate_import_updater()

        if self.dry_run:
            logger.info(f"   [DRY RUN] Would create: {script_path}")
        else:
            script_path.write_text(script)
            logger.info(f"   ✅ Created: {script_path}")

        return script_path


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cohezion Directory Restructure Migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--analyze",
        "-a",
        action="store_true",
        help="Analyze current structure without making changes",
    )
    parser.add_argument(
        "--plan",
        "-p",
        action="store_true",
        help="Show migration plan without executing",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the migration (WARNING: modifies file structure)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
        default=True,
    )

    args = parser.parse_args()

    if not args.apply:
        args.dry_run = True

    migrator = DirectoryRestructure(dry_run=args.dry_run)

    if args.analyze:
        migrator.analyze_current_structure()

    elif args.plan:
        migrator.plan_migration()

    elif args.apply or args.dry_run:
        if args.dry_run:
            logger.info("⚠️  DRY RUN MODE - No changes will be made")
            logger.info("   Run with --apply to execute migration")

        migrator.analyze_current_structure()
        migrator.execute_migration()
        migrator.save_import_updater()

        logger.info("\n📝 NEXT STEPS:")
        logger.info("   1. Review the changes above")
        logger.info("   2. Run tests: uv run pytest")
        logger.info("   3. If all tests pass, run: uv run python scripts/restructure.py --apply")
        logger.info("   4. Update imports: uv run python scripts/update_imports.py --apply")

    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
