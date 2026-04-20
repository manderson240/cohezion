#!/usr/bin/env python3
"""Update imports after directory restructure.

Run this after executing: python scripts/restructure.py --apply

Usage:
    python scripts/update_imports.py --dry-run  # Preview changes
    python scripts/update_imports.py --apply    # Apply changes

This script updates import statements in Python files to reflect the new
directory structure:

Before:
    from cohezion.caching import ...
    from cohezion.swarm.agents.foo import ...

After:
    from cohezion.core.cache import ...
    from cohezion.agents.foo import ...
"""

import argparse
import re
from pathlib import Path


def update_imports(dry_run: bool = True) -> dict[str, int]:
    """Update imports in all Python files."""
    root = Path("src/cohezion")

    import_mappings = [
        # caching/ -> core/cache/
        (r"from cohezion\.caching\b", "from cohezion.core.cache"),
        (r"from cohezion\.cache_manager\b", "from cohezion.core.cache.cache_manager"),
        # db/ -> core/persistence/
        (r"from cohezion\.db\.", "from cohezion.core.persistence."),
        (
            r"from cohezion\.repositories\b",
            "from cohezion.core.persistence.repositories",
        ),
        # swarm/agents/ -> agents/
        (r"from cohezion\.swarm\.agents\b", "from cohezion.agents"),
        (r"from cohezion\.swarm\.agents\.", "from cohezion.agents."),
    ]

    files_updated = 0
    files_scanned = 0

    for py_file in sorted(root.rglob("*.py")):
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
                    print(f"   [DRY RUN] Would update: {py_file.relative_to(root)}")
                else:
                    py_file.write_text(content)
                    print(f"   ✅ Updated: {py_file.relative_to(root)}")

            files_scanned += 1

        except Exception as e:
            print(f"   ❌ Error processing {py_file}: {e}")

    return {"scanned": files_scanned, "updated": files_updated}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update imports after directory restructure")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes")

    args = parser.parse_args()

    if not args.apply:
        args.dry_run = True

    print("=" * 60)
    print("📝 IMPORT UPDATER")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
        print()
    else:
        print("🚀 Applying import updates...")
        print()

    result = update_imports(dry_run=args.dry_run)

    print()
    print("=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print(f"   Files scanned: {result['scanned']}")
    print(f"   Files updated: {result['updated']}")

    if args.dry_run:
        print()
        print("To apply changes, run:")
        print("   python scripts/update_imports.py --apply")


if __name__ == "__main__":
    main()
