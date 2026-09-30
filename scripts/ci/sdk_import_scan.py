#!/usr/bin/env python3
"""Every third-party-SDK import in src/ must resolve on the INSTALLED SDK.

Origin (2026-09-30): amd-gaia removed ``gaia.agents.chat`` / ``gaia.agents.mcp`` (gone in 0.23.0).
``gaia_adapter.build_gaia_native_tier`` kept importing them lazily inside a function, under
``except ImportError -> RuntimeError("amd-gaia not installed")`` — so the break surfaced at CALL time
with a misleading message, and 445 GAIA tests stayed green because none imported the real class.
This scan resolves each import (module AND imported names) against the installed package, so an
upstream removal fails at upgrade time instead.

Ratchet: known-dead imports live in sdk_import_baseline.json; only NEW unresolved imports fail, and
imports that start resolving again are reported so the baseline can be pruned.
Usage: python scripts/ci/sdk_import_scan.py [--self-test | --write-baseline]
"""

from __future__ import annotations

import ast
import importlib
import json
import sys
import tempfile
from pathlib import Path


SDK_ROOTS = ("gaia",)
SRC = Path(__file__).resolve().parents[2] / "src"
BASELINE = Path(__file__).with_name("sdk_import_baseline.json")


def _is_sdk(module: str | None) -> bool:
    return bool(module) and module.split(".")[0] in SDK_ROOTS


def unresolved(module: str, names: list[str]) -> list[str]:
    """Failures for one import statement: the module itself, or each name missing from it."""
    try:
        mod = importlib.import_module(module)
    except Exception as exc:
        return [f"{module} ({type(exc).__name__})"]
    bad = []
    for name in names:
        if name == "*" or hasattr(mod, name):
            continue
        try:
            importlib.import_module(f"{module}.{name}")  # `from pkg import submodule`
        except Exception:
            bad.append(f"{module}:{name}")
    return bad


def scan(root: Path) -> set[str]:
    found: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        rel = path.relative_to(root.parent).as_posix()
        for node in ast.walk(tree):  # includes imports nested in functions / try blocks
            if isinstance(node, ast.ImportFrom) and _is_sdk(node.module) and node.level == 0:
                found |= {
                    f"{rel}::{b}" for b in unresolved(node.module, [a.name for a in node.names])
                }
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_sdk(alias.name):
                        found |= {f"{rel}::{b}" for b in unresolved(alias.name, [])}
    return found


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "src"
        root.mkdir()
        (root / "good.py").write_text("from gaia.llm.lemonade_client import LemonadeClient\n")
        (root / "bad.py").write_text(
            "def f():\n    from gaia.agents.no_such_pkg.agent import Nope\n"
        )
        (root / "bad_name.py").write_text("from gaia.llm.lemonade_client import NoSuchClass\n")
        got = scan(root)
    want_bad = {k.split("::")[0] for k in got}
    ok = want_bad == {"src/bad.py", "src/bad_name.py"}
    print(
        ("OK" if ok else "FAIL")
        + f" self-test: flagged {sorted(want_bad)} (want bad.py + bad_name.py, not good.py)"
    )
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    current = scan(SRC)
    if "--write-baseline" in argv:
        BASELINE.write_text(json.dumps(sorted(current), indent=1) + "\n")
        print(f"baseline written: {len(current)} known-unresolved SDK import(s)")
        return 0
    baseline = set(json.loads(BASELINE.read_text())) if BASELINE.exists() else set()
    new, healed = sorted(current - baseline), sorted(baseline - current)
    print(f"sdk imports: {len(current)} unresolved (baseline {len(baseline)})")
    for h in healed:
        print(f"  healed, prune baseline: {h}")
    for n in new:
        print(f"  NEW unresolved: {n}")
    if new:
        print(
            "An SDK import no longer resolves on the installed version. Fix or remove it; do NOT re-baseline."
        )
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
