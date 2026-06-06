"""Discriminating guard for the latent NameError in CompoundExecutor (2026-06-06).

`executor.py` uses `pathlib.Path(...)` at four sites (vault-default resolution and
on-disk file analysis) but, at commit f4ec56944 (HEAD before this fix), the module
imported no `Path` — a latent `NameError` that only fires on the rarely-exercised
branches, so the green test suite never caught it.

Falsifiable check: the WRONG implementation (the missing import) leaves the module
namespace without `Path`, so `executor.Path` raises AttributeError. This is a
structural-before-behavioral guard (Learning 366): the failure surface is an
import/name drift, so a name-presence assertion fires at collection time with an
explicit invariant rather than deep in a vault-default code path at runtime.
"""

from __future__ import annotations

from pathlib import Path


def test_executor_module_has_pathlib_path_imported() -> None:
    import cohezion.compound.executor as executor

    # Wrong impl (no `from pathlib import Path`) → `executor.Path` is absent → fails.
    assert getattr(executor, "Path", None) is Path
