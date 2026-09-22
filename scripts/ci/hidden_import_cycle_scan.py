#!/usr/bin/env python3
"""Hidden import-cycle scan -- "did a guarded re-export silently vanish?"

Cohezion's package ``__init__.py`` files wrap re-exports in ``contextlib.suppress(Exception)``
or ``try/except Exception: pass`` so an optional heavy dependency cannot break the package.
The same guard also swallows ``ImportError: cannot import name X from partially initialized
module`` -- an import CYCLE -- so the name just disappears, and WHICH names disappear depends
on import order. Measured 2026-09-22: ``JourneyPersistence`` vanished from
``cohezion.compound.exp_persistence`` (cycle surreal_client -> reliability -> semantic_cache ->
exp_persistence -> journey -> surreal_client), then ``AdversarialCritique`` vanished from
``cohezion.compound.tdd_adversarial`` only when tests/compound was collected first. Nothing
failed; a consumer just got ``ImportError`` far away, or a test passed alone and failed in a
batch. mypy and ruff cannot see this: the guard's contract IS to succeed silently.

Method (stdlib only):
  1. AST-find every name imported inside a guarded block (``with suppress(...)`` or a ``try``
     whose handler catches Exception/BaseException/ImportError/bare) in
     ``src/cohezion/**/__init__.py``.
  2. For each guarded package, in FRESH subprocesses, import it under several orders (alone,
     and after each hub module). ``sys.monitoring`` EXCEPTION_HANDLED records every exception a
     guarded ``__init__`` swallows -- the real exception, not a re-run that may now succeed.
  3. Classify each missing name by the swallowed exception:
       defect   -- ImportError naming a ``cohezion`` module (cycle / partially initialized /
                   cannot-import-name / stale module path), or a name missing in SOME orders
                   but present in others (order dependence == cycle signature)
       optional -- ModuleNotFoundError / ImportError for a third-party module (legitimate)
       error    -- any other exception raised at import time (reported, not ratcheted:
                   usually environment-coupled)
  4. Ratchet: the set of defect keys may only shrink (``hidden_import_cycle_baseline.txt``).

Usage:
    python scripts/ci/hidden_import_cycle_scan.py              # gate against the baseline
    python scripts/ci/hidden_import_cycle_scan.py --update     # rewrite baseline (never grows)
    python scripts/ci/hidden_import_cycle_scan.py --report     # print full report, no gate
    python scripts/ci/hidden_import_cycle_scan.py --json out.json
    python scripts/ci/hidden_import_cycle_scan.py --self-test  # prove it can fail
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
ROOT_PKG = "cohezion"
BASELINE_FILE = Path(__file__).resolve().parent / "hidden_import_cycle_baseline.txt"
_PROVENANCE = "# measured-by: hidden_import_cycle_scan.py --update"
HUBS = (
    "cohezion.core.surreal_client",
    "cohezion.reliability",
    "cohezion.compound",
    "cohezion.inference",
)
_BROAD = {"Exception", "BaseException", "ImportError", "ModuleNotFoundError"}
_TIMEOUT_S = 180


# --------------------------------------------------------------------------- AST phase
def _tail(node: ast.expr) -> str:
    return node.id if isinstance(node, ast.Name) else getattr(node, "attr", "")


def _handler_is_broad(h: ast.ExceptHandler) -> bool:
    if h.type is None:
        return True
    types = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
    return any(_tail(t) in _BROAD for t in types)


def _is_suppress(item: ast.withitem) -> bool:
    call = item.context_expr
    return isinstance(call, ast.Call) and _tail(call.func) == "suppress"


def _imports_in(stmts: list[ast.stmt]) -> list[dict]:
    """Names bound by import statements in a guarded body (not inside nested defs)."""
    out: list[dict] = []
    stack = list(stmts)
    while stack:
        node = stack.pop(0)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    out.append(
                        {
                            "name": alias.asname or alias.name,
                            "line": node.lineno,
                            "end": node.end_lineno or node.lineno,
                        }
                    )
        elif isinstance(node, ast.Import):
            # `import cohezion.x.y` binds the top package -- only an alias is a re-export.
            for alias in node.names:
                if alias.asname:
                    out.append(
                        {
                            "name": alias.asname,
                            "line": node.lineno,
                            "end": node.end_lineno or node.lineno,
                        }
                    )
        else:
            stack.extend(ast.iter_child_nodes(node))
    return out


def guarded_blocks(path: Path) -> list[dict]:
    """Return guarded blocks: {start, end, kind, names:[{name,line,end}]} for one __init__."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    blocks: list[dict] = []

    def visit(stmts: list[ast.stmt]) -> None:
        for node in stmts:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, ast.With) and any(_is_suppress(i) for i in node.items):
                names = _imports_in(node.body)
                if names:
                    blocks.append(
                        {
                            "start": node.lineno,
                            "end": node.end_lineno,
                            "kind": "suppress",
                            "names": names,
                        }
                    )
                continue
            if isinstance(node, ast.Try) and any(_handler_is_broad(h) for h in node.handlers):
                names = _imports_in(node.body)
                if names:
                    blocks.append(
                        {
                            "start": node.lineno,
                            "end": node.end_lineno,
                            "kind": "try",
                            "names": names,
                        }
                    )
                visit(node.orelse)
                visit(node.finalbody)
                continue
            if isinstance(node, (ast.If, ast.With, ast.Try)):
                visit(node.body)
                visit(getattr(node, "orelse", []))

    visit(tree.body)
    return blocks


def discover(src: Path, root_pkg: str) -> dict[str, dict]:
    """Map package name -> {file, blocks} for every __init__ with guarded re-exports."""
    found: dict[str, dict] = {}
    for init in sorted((src / root_pkg).rglob("__init__.py")):
        pkg = ".".join(init.parent.relative_to(src).parts)
        blocks = guarded_blocks(init)
        if blocks:
            found[pkg] = {"file": str(init.resolve()), "blocks": blocks}
    return found


# --------------------------------------------------------------------------- worker phase
# Runs in a FRESH interpreter per import order. sys.monitoring EXCEPTION_HANDLED fires for
# both `except` clauses and `with suppress(...)`, so we capture the exception the guard ate.
_WORKER = r"""
import importlib, json, sys
spec = json.load(open(sys.argv[1]))
files = {v["file"]: k for k, v in spec["packages"].items()}
swallowed = []
M = sys.monitoring
TID = 4
M.use_tool_id(TID, "hidden_import_cycle_scan")

def _cb(code, offset, exc):
    fn = code.co_filename
    if fn not in files:
        return
    line = None
    tb = exc.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == fn:
            line = tb.tb_lineno
        tb = tb.tb_next
    swallowed.append({"pkg": files[fn], "line": line, "type": type(exc).__name__,
                      "msg": str(exc)[:300], "name": getattr(exc, "name", None),
                      "is_import": isinstance(exc, ImportError)})

M.register_callback(TID, M.events.EXCEPTION_HANDLED, _cb)
M.set_events(TID, M.events.EXCEPTION_HANDLED)
failed = {}
for mod in spec["order"]:
    try:
        importlib.import_module(mod)
    except BaseException as e:  # the package itself failed; record, continue
        failed[mod] = type(e).__name__ + ": " + str(e)[:200]
M.set_events(TID, 0)
missing = {}
for pkg, info in spec["packages"].items():
    m = sys.modules.get(pkg)
    if m is None:
        continue
    missing[pkg] = [n["name"] for b in info["blocks"] for n in b["names"]
                    if n["name"] not in m.__dict__]
print("@@RESULT@@" + json.dumps({"order": spec["order"], "swallowed": swallowed,
                                 "missing": missing, "failed": failed}))
sys.stdout.flush()
import os; os._exit(0)
"""


def _run_order(order: list[str], spec: dict, env: dict, py: str) -> dict:
    fd, spec_file = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump({**spec, "order": order}, fh)
    try:
        proc = subprocess.run(
            [py, "-c", _WORKER, spec_file],
            capture_output=True,
            text=True,
            env=env,
            timeout=_TIMEOUT_S,
            cwd=str(REPO),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"order": order, "error": f"timeout after {_TIMEOUT_S}s"}
    finally:
        os.unlink(spec_file)
    for ln in proc.stdout.splitlines():
        if ln.startswith("@@RESULT@@"):
            return json.loads(ln[len("@@RESULT@@") :])
    return {"order": order, "error": f"worker exit {proc.returncode}: {proc.stderr[-400:]}"}


def _python() -> str:
    venv = REPO / ".venv" / "bin" / "python3"
    return str(venv) if venv.exists() else sys.executable


# --------------------------------------------------------------------------- classify
def classify(exc: dict, root_pkg: str) -> str:
    """defect = cohezion-internal ImportError; optional = third-party; error = non-import."""
    name = exc.get("name") or ""
    is_root = name == root_pkg or name.startswith(root_pkg + ".")
    if exc["is_import"]:
        if "partially initialized" in exc["msg"] or is_root:
            return "defect"
        if not name and f"'{root_pkg}" in exc["msg"]:
            return "defect"
        return "optional"
    return "error"


def scan(
    src: Path = SRC,
    root_pkg: str = ROOT_PKG,
    hubs: tuple[str, ...] = HUBS,
    jobs: int | None = None,
    packages: list[str] | None = None,
) -> dict:
    found = discover(src, root_pkg)
    if packages:
        found = {k: v for k, v in found.items() if k in packages}
    spec = {"root": root_pkg, "packages": found}
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("COHEZION_JOURNEY_PERSIST", "0")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    orders: list[list[str]] = []
    for pkg in found:
        orders.append([pkg])
        orders.extend([h, pkg] for h in hubs if h != pkg)
    jobs = jobs or max(1, min(8, (os.cpu_count() or 2) // 2))
    py = _python()
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        runs = list(pool.map(lambda o: _run_order(o, spec, env, py), orders))
    return aggregate(found, runs, root_pkg)


def aggregate(found: dict, runs: list[dict], root_pkg: str) -> dict:
    stats: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"missing_in": [], "present_in": 0, "causes": {}}
    )
    worker_errors = [r for r in runs if "error" in r]
    for r in runs:
        if "error" in r:
            continue
        by_pkg: dict[str, list[dict]] = defaultdict(list)
        for s in r["swallowed"]:
            by_pkg[s["pkg"]].append(s)
        for pkg, gone in r["missing"].items():
            gone_set = set(gone)
            for b in found[pkg]["blocks"]:
                excs = [s for s in by_pkg[pkg] if s["line"] and b["start"] <= s["line"] <= b["end"]]
                for n in b["names"]:
                    key = (pkg, n["name"])
                    if n["name"] not in gone_set:
                        stats[key]["present_in"] += 1
                        continue
                    stats[key]["missing_in"].append(" -> ".join(r["order"]))
                    # Cause = exception on this name's statement, else the nearest earlier one
                    # in the same block (it aborted the rest of the block).
                    cause = next((e for e in excs if n["line"] <= e["line"] <= n["end"]), None)
                    if cause is None:
                        earlier = [e for e in excs if e["line"] < n["line"]]
                        cause = earlier[-1] if earlier else None
                    if cause:
                        stats[key]["causes"][f"{cause['type']}: {cause['msg']}"] = classify(
                            cause, root_pkg
                        )
    entries = []
    for (pkg, name), st in sorted(stats.items()):
        if not st["missing_in"]:
            continue
        cats = set(st["causes"].values())
        order_dependent = st["present_in"] > 0
        if "defect" in cats or order_dependent:
            cat = "defect"
        elif "error" in cats:
            cat = "error"
        elif "optional" in cats:
            cat = "optional"
        else:
            cat = "unexplained"
        entries.append(
            {
                "key": f"{pkg}:{name}",
                "category": cat,
                "order_dependent": order_dependent,
                "missing_in": len(st["missing_in"]),
                "present_in": st["present_in"],
                "example_order": st["missing_in"][0],
                "causes": st["causes"],
            }
        )
    counts: dict[str, int] = defaultdict(int)
    for e in entries:
        counts[e["category"]] += 1
    return {
        "packages": len(found),
        "runs": len(runs),
        "worker_errors": worker_errors,
        "counts": dict(counts),
        "entries": entries,
    }


# --------------------------------------------------------------------------- ratchet
def _read_baseline() -> set[str] | None:
    if not BASELINE_FILE.exists():
        return None
    return {
        ln.strip()
        for ln in BASELINE_FILE.read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def _write_baseline(keys: set[str]) -> None:
    header = textwrap.dedent(f"""\
        {_PROVENANCE}
        # Guarded re-exports that SILENTLY VANISH from a cohezion package because a
        # cohezion-internal ImportError (import cycle / partially initialized module /
        # stale path) is swallowed by suppress(Exception) or except Exception.
        # One `<package>:<name>` per line. Down-only: a NEW entry fails the gate; fix
        # entries (lazy import at point of use) and re-run --update to shrink this file.
        """)
    BASELINE_FILE.write_text(header + "".join(f"{k}\n" for k in sorted(keys)))


def _print_report(res: dict, verbose: bool) -> None:
    print(
        f"hidden_import_cycle_scan: {res['packages']} guarded packages, {res['runs']} "
        f"subprocess orders, counts={res['counts']}"
    )
    for w in res["worker_errors"]:
        print(f"  WORKER ERROR {w['order']}: {w['error'][:200]}")
    for e in res["entries"]:
        if not verbose and e["category"] != "defect":
            continue
        dep = " [order-dependent]" if e["order_dependent"] else ""
        print(
            f"  {e['category'].upper():9} {e['key']}{dep}  "
            f"(missing {e['missing_in']}/{e['missing_in'] + e['present_in']}; "
            f"e.g. {e['example_order']})"
        )
        for c in list(e["causes"])[:2]:
            print(f"      cause: {c[:220]}")


def gate(res: dict) -> int:
    if res["worker_errors"]:
        print("FAIL: worker subprocess errors -- the scan is UNKNOWN, not clean.")
        return 1
    measured = {e["key"] for e in res["entries"] if e["category"] == "defect"}
    base = _read_baseline()
    if base is None:
        print(f"FAIL: no baseline at {BASELINE_FILE}; run --update")
        return 1
    new, fixed = measured - base, base - measured
    if new:
        print(f"FAIL: {len(new)} NEW hidden import-cycle defect(s) (baseline {len(base)}):")
        for k in sorted(new):
            print(f"  + {k}")
        print("Fix with a lazy import at the point of use; never extend the baseline.")
        return 1
    if fixed:
        print(
            f"FAIL: {len(fixed)} baseline entries now fixed -- lock in the paydown: "
            "python scripts/ci/hidden_import_cycle_scan.py --update"
        )
        for k in sorted(fixed):
            print(f"  - {k}")
        return 1
    print(f"PASS: {len(measured)} defect-class hidden names == baseline")
    return 0


# --------------------------------------------------------------------------- self-test
def self_test() -> int:
    """Planted cycle behind suppress MUST be a defect; planted missing third-party MUST NOT."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "zzcyc"
        (pkg / "sub").mkdir(parents=True)
        (pkg / "opt").mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        # Cycle: sub/__init__ -> sub.b -> `from zzcyc.sub import A` while sub is half-built.
        (pkg / "sub" / "__init__.py").write_text(
            textwrap.dedent("""\
            import contextlib
            with contextlib.suppress(Exception):
                from zzcyc.sub.b import B as B
            with contextlib.suppress(Exception):
                from zzcyc.sub.a import A as A
            """)
        )
        (pkg / "sub" / "a.py").write_text("class A: pass\n")
        (pkg / "sub" / "b.py").write_text("from zzcyc.sub import A\nclass B: pass\n")
        (pkg / "opt" / "__init__.py").write_text(
            textwrap.dedent("""\
            try:
                from zzcyc.opt.heavy import Heavy as Heavy
            except Exception:
                pass
            """)
        )
        (pkg / "opt" / "heavy.py").write_text(
            "import zz_not_installed_thirdparty_pkg\nclass Heavy: pass\n"
        )
        res = scan(src=Path(tmp), root_pkg="zzcyc", hubs=("zzcyc.sub.a",), jobs=2)
    by = {e["key"]: e for e in res["entries"]}
    ok = True
    b = by.get("zzcyc.sub:B")
    if not b or b["category"] != "defect":
        print(f"self-test FAIL: planted cycle zzcyc.sub:B not flagged as defect: {b}")
        ok = False
    h = by.get("zzcyc.opt:Heavy")
    if not h or h["category"] != "optional":
        print(f"self-test FAIL: missing third-party zzcyc.opt:Heavy should be optional: {h}")
        ok = False
    if "zzcyc.sub:A" in by:
        print(f"self-test FAIL: zzcyc.sub:A imports cleanly but was flagged: {by['zzcyc.sub:A']}")
        ok = False
    if res["worker_errors"]:
        print(f"self-test FAIL: worker errors {res['worker_errors']}")
        ok = False
    print("self-test PASS" if ok else "self-test FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Hidden import-cycle scan (guarded re-exports)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--report", action="store_true", help="print all categories, no gate")
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--jobs", type=int)
    ap.add_argument("--package", action="append", help="limit to package(s); implies no gate")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    res = scan(jobs=args.jobs, packages=args.package)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=2))
    _print_report(res, verbose=args.report)
    if args.report or args.package:
        return 0
    if args.update:
        if res["worker_errors"]:
            print("refusing --update: worker errors make the measurement UNKNOWN")
            return 1
        measured = {e["key"] for e in res["entries"] if e["category"] == "defect"}
        base = _read_baseline()
        if base is not None and measured - base:
            print(f"refusing --update: would ADD {sorted(measured - base)} -- fix them instead")
            return 1
        _write_baseline(measured)
        print(f"baseline written: {len(measured)} entries")
        return 0
    return gate(res)


if __name__ == "__main__":
    sys.exit(main())
