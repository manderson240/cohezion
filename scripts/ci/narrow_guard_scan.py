#!/usr/bin/env python3
"""Narrow-guard scan — find try-blocks whose handler cannot catch what the body raises.

WHY THIS EXISTS (2026-08-19)
----------------------------
`dormancy_scan.py` asks "does this capability have a consumer?". That is necessary and NOT
sufficient. The worst defect found on 2026-08-19 had a real consumer that had never once
succeeded:

    # core/journey_worker.py:105-110
    try:
        from cohezion.healing import get_healing_system   # <- CAN raise ImportError
        healer = get_healing_system()
        await healer.heal_manifold(...)                   # <- raises AttributeError; the
    except ImportError:                                   #    method does not exist
        logger.debug("Healing system not available in this context.")

The import succeeds. `heal_manifold` does not exist on `SelfHealingSystem`, so the call raises
`AttributeError`, which `except ImportError` does not catch. It propagated into the telemetry
bus, which swallows every subscriber exception at debug/error level. Result: the self-healing
system had never healed, and nothing anywhere said so.

`hasattr` passes. A caller-grep passes. Unit tests pass. Dormancy scan passes — there IS a
consumer. Only running the call reveals it. This scanner finds the SHAPE statically instead.

THE SHAPE: a try whose handlers catch ONLY import-ish exceptions, while its body does more than
import. The import is guarded; everything after it is not. That is almost always unintentional —
the author meant "skip this if the module is missing" and accidentally wrote "skip this if the
module is missing, and crash on anything else".

Deliberately narrow. One shape, high precision, no configuration. A scanner that cries wolf gets
disabled (see dormancy_scan.py's note on the auto-test-scaffold hook).

Run:  python scripts/ci/narrow_guard_scan.py             # report
      python scripts/ci/narrow_guard_scan.py --self-test # prove it can go RED before trusting GREEN
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "cohezion"

# Handlers that mean "this dependency may be absent".
IMPORT_GUARDS = {"ImportError", "ModuleNotFoundError"}


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    """Exception type names in one `except` clause. Empty set == bare `except:`."""
    node = handler.type
    if node is None:
        return set()
    parts = node.elts if isinstance(node, ast.Tuple) else [node]
    names: set[str] = set()
    for p in parts:
        if isinstance(p, ast.Name):
            names.add(p.id)
        elif isinstance(p, ast.Attribute):
            names.add(p.attr)
    return names


def _risky_ops(body: list[ast.stmt]) -> list[str]:
    """Operations in the try body that an import guard cannot possibly catch.

    Imports are exempt (that is what the guard is for). Attribute access and calls are not:
    a missing method raises AttributeError, a signature change raises TypeError.
    """
    ops: list[str] = []
    for stmt in body:
        if isinstance(stmt, ast.Import | ast.ImportFrom):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Attribute):
                    ops.append(f"{ast.unparse(fn)}(...)")
                elif isinstance(fn, ast.Name):
                    ops.append(f"{fn.id}(...)")
            elif isinstance(node, ast.Attribute) and not isinstance(node.ctx, ast.Store):
                ops.append(ast.unparse(node))
    # De-duplicate, preserve order, keep it short enough to read in a report.
    seen: set[str] = set()
    out: list[str] = []
    for o in ops:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out[:4]


def scan_source(src: str, label: str = "<src>") -> list[tuple[str, int, str, list[str]]]:
    """Return (label, lineno, guarded_types, risky_ops) for each narrow-guard try."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    findings: list[tuple[str, int, str, list[str]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try) or not node.handlers:
            continue
        caught: set[str] = set()
        for h in node.handlers:
            names = _handler_names(h)
            if not names:  # bare except catches everything — not this defect
                caught = set()
                break
            caught |= names
        if not caught or not caught.issubset(IMPORT_GUARDS):
            continue
        # An import must actually be present, else the guard is unrelated to imports.
        if not any(isinstance(s, ast.Import | ast.ImportFrom) for s in node.body):
            continue
        risky = _risky_ops(node.body)
        if risky:
            findings.append((label, node.lineno, "/".join(sorted(caught)), risky))
    return findings


_BAD = '''
try:
    from pkg.healing import get_healing_system
    healer = get_healing_system()
    healer.heal_manifold(x, y)
except ImportError:
    pass
'''
_GOOD_IMPORT_ONLY = '''
try:
    import numpy
    from pkg import thing
except ImportError:
    numpy = None
'''
_GOOD_BROAD = '''
try:
    from pkg.healing import get_healing_system
    get_healing_system().heal_manifold(x, y)
except Exception:
    pass
'''
_GOOD_ALSO_CATCHES = '''
try:
    from pkg.healing import get_healing_system
    get_healing_system().heal_manifold(x, y)
except (ImportError, AttributeError):
    pass
'''


def self_test() -> int:
    cases = [
        ("BAD: import guard over a method call", _BAD, 1),
        ("GOOD: try contains only imports", _GOOD_IMPORT_ONLY, 0),
        ("GOOD: broad except Exception", _GOOD_BROAD, 0),
        ("GOOD: also catches AttributeError", _GOOD_ALSO_CATCHES, 0),
    ]
    ok = True
    for name, src, want in cases:
        got = len(scan_source(src, name))
        flag = "ok  " if got == want else "FAIL"
        ok &= got == want
        print(f"  [{flag}] {name}: expected {want}, got {got}")
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--path", default=str(SRC))
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = Path(args.path)
    files = sorted(root.rglob("*.py"))
    all_findings: list[tuple[str, int, str, list[str]]] = []
    for f in files:
        rel = str(f.relative_to(REPO))
        all_findings += scan_source(f.read_text(encoding="utf-8", errors="replace"), rel)

    print(f"scanned {len(files)} files under {root.relative_to(REPO)}")
    print(f"narrow-guard try-blocks: {len(all_findings)}\n")
    for label, line, caught, ops in all_findings:
        print(f"{label}:{line}  except {caught}")
        for o in ops:
            print(f"    unguarded: {o}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
