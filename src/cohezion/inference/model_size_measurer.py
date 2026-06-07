"""GGUF size measurer (backlog item 136, 2026-06-07).

The NON-FABRICATED source of `ModelEntry.size_gb` (item 135) for models not yet populated:
the actual on-disk GGUF file size. Item 135 populated only the 2 locally-cached models because
only their GGUF was found; this helper measures any model whose GGUF is present, so the registry
(or a human) can fill more `size_gb` as models get pulled — without ever guessing from param count.

Report-only / read-only: walks the given search dirs, matches each model_id to its `.gguf` by a
normalized-substring rule (excluding `mmproj` projector files), and returns the on-disk size in
binary GB (bytes / 2**30, the `du -h` convention). A model with no local GGUF is ABSENT from the
result — never assigned a fabricated size.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path


_GIB = 1024**3


def _norm(s: str) -> str:
    """Lowercase, keep only alphanumerics — so `Gemma-4-E4B-it` ≈ `gemma4e4bit`."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _model_core(model_id: str) -> str:
    """Normalized matching key for a model_id (drop the `-GGUF` / `:cloud` suffixes)."""
    s = re.sub(r"[-_]?gguf$", "", model_id, flags=re.IGNORECASE)
    s = re.sub(r":cloud$", "", s, flags=re.IGNORECASE)
    return _norm(s)


def measure_gguf_sizes(
    model_ids: Iterable[str],
    *,
    search_dirs: Iterable[str | Path],
) -> dict[str, float]:
    """Measure on-disk GGUF size (GB) for each model_id whose `.gguf` is found. Item 136.

    Match rule: the model's normalized core (e.g. ``gemma4e4bit``) is a substring of the GGUF
    file's normalized stem. ``mmproj`` projector files are excluded (they are not the weights).
    When several files match, the LARGEST is taken (the main weights, not a shard/projector).
    A model with no matching GGUF is omitted — non-fabricated. Pure read-only filesystem walk.
    """
    files: list[tuple[str, int]] = []  # (normalized_stem, size_bytes)
    for d in search_dirs:
        root = Path(d).expanduser()
        if not root.exists():
            continue
        for f in root.rglob("*.gguf"):
            if "mmproj" in f.name.lower():
                continue
            try:
                files.append((_norm(f.stem), f.stat().st_size))
            except OSError:
                continue

    out: dict[str, float] = {}
    for model_id in model_ids:
        core = _model_core(model_id)
        if not core:
            continue
        matches = [sz for (stem, sz) in files if core in stem]
        if matches:
            out[model_id] = round(max(matches) / _GIB, 1)
    return out
