"""Vault Sync — Event-driven SurrealDB sync for the Cohezion vault."""

from .config import VAULT_ROOT, CHECKPOINT, SURREAL_PORT, CONTENT_DIRS, SKIP_DIRS
from .client import SurrealClient
from .sync import sync_file, delete_file, move_file
from .checkpoint import load_checkpoint, save_checkpoint
from .batch import full_import, incremental_sync
from .reactor import GraphReactor, ALERTS_FILE
from .writeback import NeuralWriteBack
from .watcher import InotifyWatcher, watch_vault
from .cli import main

__all__ = [
    "SurrealClient", "sync_file", "delete_file", "move_file",
    "load_checkpoint", "save_checkpoint", "full_import", "incremental_sync",
    "GraphReactor", "NeuralWriteBack", "InotifyWatcher", "watch_vault", "main",
]
