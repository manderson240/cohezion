"""Discriminating tests for single-caller pass-through detection (item 46, 2026-06-06).

`needless_passthroughs(paths)` narrows item-44's `passthrough_functions` by REACHABILITY: it keeps
only forwarders whose function has <=1 static caller across the paths — the wrapper that earns
nothing (1 caller) or is itself an orphan (0 callers). A >=2-caller forwarder is a FACADE (a real
API surface) and is dropped. Ties the simplicity dimension to the wiring/reachability dimension.

Each test fails a plausible wrong impl:
  - keeps a many-caller facade → test_facade_dropped,
  - drops the 0-caller orphan instead of flagging it → test_orphan_kept_flagged,
  - flags a non-passthrough → test_non_passthrough_ignored,
  - miscounts callers (off-by-one on the def, or counts the forwarded-to target) → test_single_caller_kept.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import NeedlessPassthrough, needless_passthroughs


_FIXTURE = """\
def target(x):
    return x


def single_fwd(x):
    return target(x)


def facade_fwd(x):
    return target(x)


def orphan_fwd(x):
    return target(x)


def real_fn(x):
    if x:
        return target(x)
    return 0


def _callers():
    single_fwd(1)        # exactly ONE caller of single_fwd
    facade_fwd(1)        # two callers of facade_fwd -> facade
    facade_fwd(2)
    real_fn(3)
    # orphan_fwd: NEVER called
"""


def _write(tmp_path: Path) -> list[Path]:
    f = tmp_path / "mod.py"
    f.write_text(_FIXTURE)
    return [tmp_path]


def _by_name(rows: list[NeedlessPassthrough]) -> dict[str, NeedlessPassthrough]:
    return {r.qualified_name.split("::")[-1]: r for r in rows}


def test_single_caller_kept(tmp_path: Path) -> None:
    rows = _by_name(needless_passthroughs(_write(tmp_path)))
    assert "single_fwd" in rows
    assert rows["single_fwd"].caller_count == 1
    assert rows["single_fwd"].orphan is False


def test_facade_dropped(tmp_path: Path) -> None:
    rows = _by_name(needless_passthroughs(_write(tmp_path)))
    assert "facade_fwd" not in rows, "a >=2-caller forwarder is a facade, not needless"


def test_orphan_kept_flagged(tmp_path: Path) -> None:
    rows = _by_name(needless_passthroughs(_write(tmp_path)))
    assert "orphan_fwd" in rows
    assert rows["orphan_fwd"].caller_count == 0
    assert rows["orphan_fwd"].orphan is True


def test_non_passthrough_ignored(tmp_path: Path) -> None:
    rows = _by_name(needless_passthroughs(_write(tmp_path)))
    assert "real_fn" not in rows  # has a branch → not a pass-through at all
    assert "target" not in rows  # returns a bare Name, not a forwarding call


def test_clean_tree_empty(tmp_path: Path) -> None:
    (tmp_path / "c.py").write_text("def f(x):\n    return x + 1\n")
    assert needless_passthroughs([tmp_path]) == []
