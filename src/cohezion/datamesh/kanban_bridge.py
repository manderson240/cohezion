"""Bridge redirect: delegates to canonical cohezion.data_mesh.kanban_bridge."""

from __future__ import annotations

from typing import Any

from cohezion.data_mesh import kanban_bridge as _km


def persist_item(item: dict[str, Any]) -> dict[str, bool]:
    """Delegate to canonical data_mesh.kanban_bridge.persist_item."""
    return _km.persist_item(item)


def backfill_items(items: list[dict[str, Any]]) -> dict[str, int]:
    """Delegate to canonical data_mesh.kanban_bridge.backfill_items."""
    return _km.backfill_items(items)


__all__ = ["backfill_items", "persist_item"]
