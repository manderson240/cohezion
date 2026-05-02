#!/usr/bin/env python3
"""
Vault brain-region backup.

Copies cortex/ and cerebellum/ from the cohezion-vault to a dated backup
directory. Keeps the last KEEP_DAYS daily snapshots and prunes the rest.

Run manually:  python3 tools/vault-backup.py
Automated:     vault-backup.timer (systemd user unit)
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path


VAULT_PATH = Path("~/vaults/cohezion-vault").expanduser()
BACKUP_ROOT = Path("~/.cohezion-backups/vault").expanduser()
BRAIN_DIRS = ["cortex", "cerebellum"]
KEEP_DAYS = 14


def main() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    backup_dir = BACKUP_ROOT / today
    backup_dir.mkdir(parents=True, exist_ok=True)

    errors = 0
    for dir_name in BRAIN_DIRS:
        src = VAULT_PATH / dir_name
        dst = backup_dir / dir_name
        if not src.exists():
            print(f"WARNING: {src} not found — skipping {dir_name}")
            errors += 1
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        count = len(list(dst.glob("*.md")))
        print(f"Backed up {dir_name}/: {count} files -> {dst}")

    # Prune snapshots beyond KEEP_DAYS
    snapshots = sorted(BACKUP_ROOT.glob("20??-??-??"))
    to_prune = snapshots[:-KEEP_DAYS] if len(snapshots) > KEEP_DAYS else []
    for old in to_prune:
        shutil.rmtree(old)
        print(f"Pruned old snapshot: {old.name}")

    print(f"Done. Backup root: {BACKUP_ROOT} ({len(snapshots)} snapshots kept)")
    return errors


if __name__ == "__main__":
    sys.exit(main())
