"""Checkpoint persistence for incremental sync."""

import json

from .config import CHECKPOINT


def load_checkpoint() -> dict:
    if CHECKPOINT.exists():
        try:
            return json.loads(CHECKPOINT.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_checkpoint(ckpt: dict):
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(ckpt))
