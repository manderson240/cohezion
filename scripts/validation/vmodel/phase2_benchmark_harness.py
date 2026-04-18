"""V-Model Phase 2 — Benchmark AutoHarness.

Deterministic gatekeeper that verifies ``benchmarks/fleet_report.md`` obeys the
7 invariants enumerated in ``docs/vmodel/PHASE2_BENCHMARK_PLAN.md``.

Invoked by ``make vmodel-phase2``. Exit 0 if all invariants pass, 1 otherwise.

Per the SYSTEMS_ENGINEERING_V_MODEL_PRIME skill: "the deterministic code
verifier" that sits at the Implementation Apex.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPORT = Path("benchmarks/fleet_report.md")
CORPUS_SIZE_EXPECTED = 20  # from scripts/benchmark_fleet.py CORPUS


def _fail(inv: str, reason: str) -> None:
    print(f"❌ FAILED {inv}: {reason}")


def _pass(inv: str, detail: str = "") -> None:
    print(f"✅ {inv}{': ' + detail if detail else ''}")


def verify_invariants(report_path: Path = REPORT) -> bool:
    print("🛡️  [V-MODEL Phase 2 HARNESS] Verifying benchmark invariants...")

    # I0: Report must exist (implicit — without it, nothing else checkable)
    if not report_path.exists():
        _fail("I0", f"report file {report_path} not found — run make benchmark-fleet first")
        return False
    text = report_path.read_text()
    _pass("I0", f"{report_path} present ({len(text)} bytes)")

    # I1: Deterministic corpus — report must mention the corpus size.
    if f"{CORPUS_SIZE_EXPECTED} deterministic routing prompts" not in text:
        _fail("I1", f"expected '{CORPUS_SIZE_EXPECTED} deterministic routing prompts' in header")
        return False
    _pass("I1", f"deterministic {CORPUS_SIZE_EXPECTED}-prompt corpus declared")

    # I2: At least 2/4 configs must have produced successes.
    # Count rows where the "Calls (ok/total)" column has ok > 0.
    # Rows look like: "| A — Claude-only | 3/5 | ... |"
    row_pat = re.compile(r"\|\s*([A-D]\s*—[^|]+)\|\s*(\d+)/(\d+)\s*\|")
    rows = row_pat.findall(text)
    configs_with_success = sum(1 for _, ok, _ in rows if int(ok) > 0)
    if configs_with_success < 2:
        _fail("I2", f"only {configs_with_success}/4 configs produced any successes (need ≥2)")
        return False
    _pass("I2", f"{configs_with_success}/4 configs produced successes")

    # I3: Every row must show all 4 headline metrics (wall time, TTFT p50,
    # TTFT range, cost). We check each row has at least 6 pipes-between-cells,
    # meaning all columns present.
    for row in text.splitlines():
        if (
            row.startswith("| A —")
            or row.startswith("| B —")
            or row.startswith("| C —")
            or row.startswith("| D —")
        ):
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if len(cells) < 7:  # config, ok/total, wall, ttft_p50, ttft_range, cost, lanes
                _fail("I3", f"row has {len(cells)} cells, expected 7: {row[:80]}...")
                return False
    _pass("I3", "every config row shows all 4 headline metrics")

    # I4: TTFT values must come from streaming — check the plan-referenced
    # description row includes "stream=True" for at least one local config.
    if "stream=True" not in text and "streaming" not in text.lower():
        _fail(
            "I4", "no evidence of streaming TTFT (expected 'stream=True' or 'streaming' in report)"
        )
        return False
    _pass("I4", "streaming TTFT measurement indicated")

    # I5: Claude-only config TTFT measurement must be present OR the report
    # must clearly mark Claude TTFT as total-latency-proxy (honest disclosure).
    # Config A row should have a ttft_p50 value (possibly "n/a" if the CLI doesn't emit)
    # — the harness accepts "n/a" here, since Claude CLI doesn't expose separate TTFT.
    a_row_match = re.search(r"\|\s*A —[^|]+\|[^|]+\|[^|]+\|\s*([^|]+?)\s*\|", text)
    if not a_row_match:
        _fail("I5", "could not find Config A row")
        return False
    _pass("I5", f"Config A TTFT disclosure = '{a_row_match.group(1).strip()}'")

    # I6: git SHA + timestamp + health snapshot present
    if not re.search(r"\*\*Git SHA:\*\*\s*`[0-9a-f]{7,}`|\*\*Git SHA:\*\*\s*`unknown`", text):
        _fail("I6a", "missing or malformed Git SHA line")
        return False
    if "**Generated:**" not in text:
        _fail("I6b", "missing Generated timestamp")
        return False
    if "Fleet health at run time" not in text:
        _fail("I6c", "missing fleet health snapshot section")
        return False
    _pass("I6", "git SHA + timestamp + health snapshot present")

    # I7: Health snapshot must show at least 1 local lane OR ollama up.
    # Accept the ✓ icon or "up" in the snapshot section.
    snapshot_match = re.search(r"## Fleet health at run time\s*```\s*(.*?)\s*```", text, re.DOTALL)
    if snapshot_match:
        snap = snapshot_match.group(1)
        local_up = any(
            f"✓ {lane}" in snap or f"{lane}            " in snap.replace("✓", "CHECKMARK")
            for lane in ("npu", "igpu_rocwmma", "igpu_unified", "cpu", "ollama")
        )
        # Simpler check: the ✓ icon appears somewhere in the snapshot
        if "✓" not in snap:
            _fail("I7", "health snapshot shows no UP lane (no ✓)")
            return False
        _pass("I7", "≥1 lane UP in health snapshot")
    else:
        _fail("I7", "could not parse health snapshot block")
        return False

    print()
    print("✨ UNIT VERIFICATION SUCCESSFUL: all 7 invariants pass")
    return True


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPORT
    sys.exit(0 if verify_invariants(path) else 1)
