"""Backward-compatibility module alias forwarding all imports to cohezion.data_mesh."""

from __future__ import annotations

from cohezion import data_mesh as _data_mesh

# Forward module attributes to preserve static imports
for _attr in dir(_data_mesh):
    if not _attr.startswith("__"):
        globals()[_attr] = getattr(_data_mesh, _attr)

__all__ = getattr(_data_mesh, "__all__", [])
