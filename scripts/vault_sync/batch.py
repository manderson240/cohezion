"""Batch sync operations: full_import and incremental_sync."""

from .checkpoint import load_checkpoint, save_checkpoint
from .client import SurrealClient
from .config import VAULT_ROOT, CONTENT_DIRS
from .sync import sync_file


def full_import(db: SurrealClient, quiet: bool = False) -> int:
    """Sync all vault files. Returns count of files synced."""
    checkpoint: dict = {}
    count = 0
    for d in CONTENT_DIRS:
        dp = VAULT_ROOT / d
        if not dp.is_dir():
            continue
        for fpath in dp.rglob("*.md"):
            if fpath.name.startswith("_"):
                continue
            if sync_file(db, str(fpath), checkpoint=checkpoint, quiet=quiet):
                count += 1
    save_checkpoint(checkpoint)
    return count


def incremental_sync(db: SurrealClient, quiet: bool = False) -> int:
    """Sync only changed files (by mtime vs checkpoint). Returns count."""
    checkpoint = load_checkpoint()
    count = 0
    for d in CONTENT_DIRS:
        dp = VAULT_ROOT / d
        if not dp.is_dir():
            continue
        for fpath in dp.rglob("*.md"):
            if fpath.name.startswith("_"):
                continue
            rel_path = str(fpath.relative_to(VAULT_ROOT))
            mtime = fpath.stat().st_mtime
            ckpt_entry = checkpoint.get(rel_path, {})
            if isinstance(ckpt_entry, dict):
                old_mtime = ckpt_entry.get("mtime", 0)
            else:
                old_mtime = ckpt_entry  # backward compat: old format was just mtime
            if mtime > old_mtime:
                if sync_file(db, str(fpath), checkpoint=checkpoint, quiet=quiet):
                    count += 1
    if count > 0:
        save_checkpoint(checkpoint)
    return count
