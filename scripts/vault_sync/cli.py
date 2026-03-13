"""CLI entry point for vault sync."""

import sys

from .batch import full_import, incremental_sync
from .checkpoint import load_checkpoint
from .client import SurrealClient
from .config import VAULT_ROOT, SURREAL_PORT
from .reactor import GraphReactor, ALERTS_FILE
from .sync import sync_file, delete_file, move_file
from .watcher import watch_vault
from .writeback import NeuralWriteBack


def main():
    db = SurrealClient(port=SURREAL_PORT)

    r = db.query("INFO FOR DB;")
    if not r or r[0].get("status") != "OK":
        print("ERROR: SurrealDB not reachable on port", SURREAL_PORT, file=sys.stderr)
        sys.exit(1)

    if "--watch" in sys.argv:
        print(f"Vault Sync daemon — watching {VAULT_ROOT}", file=sys.stderr)
        watch_vault(db, quiet="--quiet" in sys.argv)

    elif "--react" in sys.argv:
        print("Running graph reactor...", file=sys.stderr)
        reactor = GraphReactor(db)
        reactor._last_run = 0
        if reactor.maybe_react():
            print(f"Alerts written to {ALERTS_FILE}", file=sys.stderr)
        else:
            print("No changes detected", file=sys.stderr)

    elif "--writeback" in sys.argv:
        print("Running neural write-back...", file=sys.stderr)
        wb = NeuralWriteBack(db)
        wb.maybe_run(force=True)
        print("Write-back complete", file=sys.stderr)

    elif "--full-import" in sys.argv:
        print(f"Full import from {VAULT_ROOT}", file=sys.stderr)
        count = full_import(db, quiet="--quiet" in sys.argv)
        print(f"Synced {count} files", file=sys.stderr)

    elif len(sys.argv) >= 3 and sys.argv[1] == "sync":
        ok = sync_file(db, sys.argv[2])
        sys.exit(0 if ok else 1)

    elif len(sys.argv) >= 3 and sys.argv[1] == "delete":
        ok = delete_file(db, sys.argv[2])
        sys.exit(0 if ok else 1)

    elif len(sys.argv) >= 4 and sys.argv[1] == "move":
        ok = move_file(db, sys.argv[2], sys.argv[3])
        sys.exit(0 if ok else 1)

    else:
        checkpoint = load_checkpoint()
        print(f"Vault Sync — {len(checkpoint)} in checkpoint", file=sys.stderr)
        count = incremental_sync(db, quiet="--quiet" in sys.argv)
        print(f"Synced {count} changed files", file=sys.stderr)
