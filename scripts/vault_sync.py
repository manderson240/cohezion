#!/usr/bin/env python3
"""
Vault Sync — Event-driven SurrealDB sync for the Cohezion vault.

Thin entry point that delegates to the vault_sync package.

Usage:
    python3 scripts/vault_sync.py --watch          # Event-driven daemon (inotify)
    python3 scripts/vault_sync.py --full-import    # Full resync (like triune-import)
    python3 scripts/vault_sync.py --react          # Run graph reactor once
    python3 scripts/vault_sync.py --writeback      # Run neural write-back once
    python3 scripts/vault_sync.py sync <file>      # Sync a single file
    python3 scripts/vault_sync.py delete <file>    # Remove a deleted file's neuron
    python3 scripts/vault_sync.py move <old> <new> # Handle a rename/move
"""

from vault_sync.cli import main

if __name__ == "__main__":
    main()
