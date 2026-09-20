#!/usr/bin/env python3
"""Lineage scan (gating): reflex modules must be loadable without the deliberative stack.

Fourth sibling of dormancy_scan ("has a consumer?"), doc_code_consistency ("do the docs tell
the truth?") and phantom_attr_scan ("does the attribute exist?"): **"can the reflex run when
the LLM layer is dead?"**

ORIGIN (2026-09-19): `import cohezion.reliability.resource_guard` -- the memory-pressure guard --
cost 10.3 s and 496 MB RSS and loaded torch, the orchestrator and the executor, because package
`__init__` files import eagerly. Loaded by FILE PATH in a fresh process the same module costs
88 ms / 17 MB / zero cohezion modules. The reflex code was clean; nothing asserted it stayed
clean, and nothing stopped the package layer from wrapping it in 500 MB. A static import-graph
BFS reported 0 deliberative reach -- a blind instrument -- so this scan MEASURES a fresh
interpreter instead of reading imports. (Two-lineage rule; council 2026-09-19, kimi's form.)

Contract per reflex root, loaded by path with a real module name in a fresh interpreter:
  * wall time  < BUDGET_MS      (1000 ms; measured 2-88 ms, ~10x headroom)
  * RSS growth < BUDGET_MB      (60 MB;   measured 1-10 MB above interpreter baseline)
  * no DELIBERATIVE module in sys.modules afterwards (orchestrator, fleet, executor, refiner...)
  * no `torch` in sys.modules

Usage:
  python scripts/ci/lineage_scan.py --self-test   # prove it can go RED before trusting GREEN
  python scripts/ci/lineage_scan.py               # gate
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUDGET_MS = 1000
BUDGET_MB = 60

# Reflex roots: must function when the deliberative (LLM) layer is dead. Curated, not inferred.
REFLEX_ROOTS: list[str] = [
    "src/cohezion/reliability/resource_guard.py",
    "src/cohezion/compound/safe_exec.py",
    "src/cohezion/compound/sandboxed_exec.py",
    "src/cohezion/inference/hotswap.py",
]

# Deliberative markers: any of these resident after a reflex import = lineage leak.
DELIBERATIVE = (
    "torch",
    "cohezion.inference.orchestrator",
    "cohezion.inference.fleet",
    "cohezion.inference.gaia_adapter",
    "cohezion.inference.triune_orchestrator",
    "cohezion.compound.executor",
    "cohezion.compound.local_inference",
    "cohezion.compound.skill_refiner",
)

_PROBE = r"""
import importlib.util, json, resource, sys, time
path, name = sys.argv[1], sys.argv[2]
# ru_maxrss is a process PEAK; a child spawned from a fat parent (pytest with torch resident)
# can inherit page mappings before exec settles. Report the import's OWN increment.
base_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t = time.perf_counter()
spec = importlib.util.spec_from_file_location(name, path)
mod = importlib.util.module_from_spec(spec)
sys.modules[name] = mod  # dataclasses/introspection need a registered module
err = ""
try:
    spec.loader.exec_module(mod)
except Exception as e:  # report, never raise: the gate decides
    err = f"{type(e).__name__}: {e}"[:200]
ms = (time.perf_counter() - t) * 1000
rss_mb = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - base_kb) / 1024
leaks = sorted(m for m in sys.modules if any(m == d or m.startswith(d + ".") for d in json.loads(sys.argv[3])))
print(json.dumps({"ms": round(ms, 1), "rss_mb": round(rss_mb, 1), "leaks": leaks, "error": err}))
"""


def probe(path: str, deliberative: tuple[str, ...] = DELIBERATIVE) -> dict:
    """Load one file by path in a FRESH interpreter (never this one) and measure it."""
    name = "lineage_probe_" + Path(path).stem
    out = subprocess.run(
        [sys.executable, "-c", _PROBE, str(REPO_ROOT / path), name, json.dumps(deliberative)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO_ROOT,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin", "TERM": "dumb"},
    )
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    try:
        data = json.loads(line)
        return (
            dict(data)
            if isinstance(data, dict)
            else {"ms": -1, "rss_mb": -1, "leaks": [], "error": "probe returned non-object"}
        )
    except (json.JSONDecodeError, ValueError):
        return {"ms": -1, "rss_mb": -1, "leaks": [], "error": f"probe crashed: {out.stderr[-300:]}"}


def verdicts(path: str, r: dict) -> list[str]:
    bad = []
    if r["error"]:
        bad.append(f"{path}: import failed: {r['error']}")
    if r["ms"] > BUDGET_MS or r["ms"] < 0:
        bad.append(f"{path}: {r['ms']} ms > {BUDGET_MS} ms budget")
    if r["rss_mb"] > BUDGET_MB or r["rss_mb"] < 0:
        bad.append(f"{path}: {r['rss_mb']} MB RSS > {BUDGET_MB} MB budget")
    if r["leaks"]:
        bad.append(f"{path}: deliberative modules loaded: {r['leaks'][:6]}")
    return bad


def scan(roots: list[str]) -> list[str]:
    failures: list[str] = []
    for path in roots:
        r = probe(path)
        failures.extend(verdicts(path, r))
        status = "FAIL" if verdicts(path, r) else "ok"
        print(f"  [{status}] {path}: {r['ms']} ms, {r['rss_mb']} MB, leaks={len(r['leaks'])}")
    return failures


def self_test() -> int:
    """Falsification proof: a planted leak MUST go red; a clean reflex MUST stay green."""
    import tempfile

    leaky = Path(tempfile.mkdtemp(prefix="lineage_selftest_")) / "leaky_reflex.py"
    # A reflex that drags the deliberative stack in -- the exact defect class of 2026-09-19.
    leaky.write_text(
        "import sys\nsys.path.insert(0, 'src')\n"
        "import cohezion.inference.orchestrator  # planted leak\n"
    )
    red = verdicts(str(leaky), probe(str(leaky)))
    if not any("deliberative" in v or "budget" in v for v in red):
        print(f"SELF-TEST FAILED: planted leak did not go red: {red}")
        return 1
    clean = "src/cohezion/compound/safe_exec.py"
    green = verdicts(clean, probe(clean))
    if green:
        print(f"SELF-TEST FAILED: known-clean reflex flagged: {green}")
        return 1
    print("SELF-TEST OK: planted leak goes red; clean reflex stays green.")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    failures = scan(REFLEX_ROOTS)
    if failures:
        print("LINEAGE SCAN FAILED -- a reflex cannot run without the deliberative stack:")
        for f in failures:
            print("  " + f)
        print("\nA reflex that needs the LLM layer to load is not a reflex (two-lineage rule).")
        return 1
    print(f"lineage scan OK -- all {len(REFLEX_ROOTS)} reflex roots load within budget, no leaks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
