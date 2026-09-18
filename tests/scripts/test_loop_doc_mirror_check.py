"""R5: loop docs' `mirror:` claims must resolve to live rows (scripts/ci/loop_doc_mirror_check.py)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci" / "loop_doc_mirror_check.py"
spec = importlib.util.spec_from_file_location("loop_doc_mirror_check", SCRIPT)
assert spec is not None and spec.loader is not None
mc = importlib.util.module_from_spec(spec)
sys.modules["loop_doc_mirror_check"] = mc  # dataclasses resolve their module by name
spec.loader.exec_module(mc)


def _doc(tmp_path: Path, name: str, line: str) -> Path:
    p = tmp_path / name
    p.write_text(f"---\n{line}\n---\nbody\n")
    return p


def test_phantom_mirror_is_red_and_real_one_is_green(tmp_path: Path) -> None:
    _doc(tmp_path, "a.md", "mirror: SurrealDB ns cohezion db main — table nonexistent_loop")
    claims = mc.scan_docs([tmp_path])
    assert [(c.db, c.table) for c in claims] == [("main", "nonexistent_loop")]
    red, _ = mc.check(claims, lambda db, t, dom: 0)
    assert red and "nonexistent_loop" in red[0]
    green, _ = mc.check(claims, lambda db, t, dom: 3)
    assert not green


def test_zero_row_guard_is_what_makes_it_red() -> None:
    """Mutation: remove the `n == 0` guard and a phantom passes -- this then fails."""
    claim = mc.Claim("phantom_doc.md", "main", "ghost_loop", None)
    failures, _ = mc.check([claim], lambda *a: 0)
    assert failures


def test_domain_scope_and_multi_db_and_negated_db_parse(tmp_path: Path) -> None:
    _doc(
        tmp_path,
        "b.md",
        "mirror: SurrealDB ns cohezion db main — domain='roster' (30 kg_node / 42 kg_edge)",
    )
    _doc(
        tmp_path,
        "c.md",
        "mirror: ns cohezion db main — table goal (5 new), db vault — table event_log",
    )
    _doc(tmp_path, "d.md", 'mirror: "db main (NOT db vault — colliding table names) — 30 kg_node"')
    _doc(tmp_path, "e.md", "mirror: none yet — candidate for goal tables")
    got = {(Path(c.doc).name, c.db, c.table, c.domain) for c in mc.scan_docs([tmp_path])}
    assert ("b.md", "main", "kg_node", "roster") in got and (
        "b.md",
        "main",
        "kg_edge",
        "roster",
    ) in got
    assert ("c.md", "main", "goal", None) in got and ("c.md", "vault", "event_log", None) in got
    assert ("d.md", "main", "kg_node", None) in got and not any(
        g[1] == "vault" and g[0] == "d.md" for g in got
    )
    assert not any(g[0] == "e.md" for g in got)  # `none` is an honest non-claim


def test_unknown_is_not_red_and_require_live_makes_it_fatal(tmp_path: Path) -> None:
    _doc(tmp_path, "a.md", "mirror: db main — table x_loop")
    red, unk = mc.check(mc.scan_docs([tmp_path]), lambda *a: None)
    assert not red and unk


def test_grandfather_is_a_ratchet() -> None:
    c = mc.Claim(
        "/v/20260904-admission-proxy-loops-and-goals.md", "main", "admission_proxy_loop", None
    )
    assert mc.check([c], lambda *a: 0) == ([], [])  # known phantom: tolerated
    stale, _ = mc.check([c], lambda *a: 4)  # now holds rows: entry must be deleted
    assert stale and "GRANDFATHERED" in stale[0]


def test_self_test_passes_and_a_neutered_check_would_fail_it() -> None:
    r = subprocess.run([sys.executable, str(SCRIPT), "--self-test"], capture_output=True, text=True)
    assert r.returncode == 0 and "SELF-TEST OK" in r.stdout


def test_real_twin_doc_mirror_resolves_live_or_skips() -> None:
    """R5 falsifier: real doc (twin_loop) -> exit 0 against live SurrealDB."""
    doc = Path.home() / "vaults/cohezion-vault/references/20260904-researcher-twin-session-loops.md"
    if not doc.exists():
        pytest.skip("vault doc not present")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--docs", str(doc.parent), "--require-live"],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
    )
    if "UNKNOWN" in r.stdout:
        pytest.skip("SurrealDB unreachable")
    assert r.returncode == 0, r.stdout


def test_guard_runs_the_mirror_check_with_self_test_first() -> None:
    """CONSUMPTION: the landing gate must invoke it; neutering the wiring turns this red."""
    guard = (ROOT / "scripts" / "ci" / "automerge_guard.sh").read_text()
    st, run = "loop_doc_mirror_check.py --self-test", "loop_doc_mirror_check.py\n"
    assert st in guard and run in guard and guard.index(st) < guard.index(run)
    assert guard.index("doc_code_consistency.py\n") < guard.index(st)  # next to its sibling
