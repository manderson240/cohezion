#!/usr/bin/env python3
"""Recursive-trace value gate — the test that can actually return RETIRE.

Spec: docs/research/RECURSIVE_TRACE_FALSIFIABLE_GATE_2026-06-05.md

CORRECTED after advisor review (2026-06-05): the original synthetic A/B in this file
was CIRCULAR — the task generator drew `solving_strategy` from the *same* `failure_map`
the mechanism consults, so the verdict was fixed by the chosen coupling p. It proved
only "a correct lookup table retrieves correct answers" — which the unit test
`test_failure_map_routes_to_mapped_strategy_first` already proves. It is retained below
ONLY as an explicitly-labelled mechanism-correctness sanity check, NOT as a value test.

The REAL question (Stage 2): does cohezion's *real* failure stream have empirical
coupling p = P(fixing_strategy == failure_map[failure_class]) meaningfully above the
0.25 chance baseline? That can only be measured from outcomes the code did NOT generate.
This script scans for such a corpus and reports the only verdict the data supports:

    corpus exists, p > 0.25 + margin  -> KEEP   (value proven on real data)
    corpus exists, p ~= 0.25          -> RETIRE (it's autoresearch with a dedup cache)
    no corpus                         -> UNPROVEN (implemented+tested; value pending data)
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path


FAILURE_MAP = {
    "latency": "semantic_remap",
    "coherence_drop": "contextual_modifier",
    "structural_mismatch": "chain_insertion",
}
CHANCE = 0.25          # 1 / |strategies|
MARGIN = 0.10          # p must clear chance by this to count as real signal

# Known places a (failure_class, fixing_strategy) corpus could live.
CORPUS_PATHS = [
    Path.home() / ".cohezion-research" / "ouroboros" / "debug",
    Path.home() / ".cohezion-research" / "logs" / "traces.jsonl",
    Path.home() / ".cohezion-research" / "logs",
]


def _iter_records():
    """Yield dicts from any JSON / JSONL files in the corpus locations."""
    for base in CORPUS_PATHS:
        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = [p for p in base.rglob("*") if p.suffix in (".json", ".jsonl")]
        else:
            continue
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if f.suffix == ".jsonl":
                for line in text.splitlines():
                    line = line.strip()
                    if line:
                        with contextlib.suppress(json.JSONDecodeError):
                            yield json.loads(line)
            else:
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, list):
                    yield from (o for o in obj if isinstance(o, dict))
                elif isinstance(obj, dict):
                    yield obj


def _extract_pair(rec: dict) -> tuple[str, str] | None:
    """Pull (failure_class, fixing_strategy) from a record if both are present."""
    fc = rec.get("failure_class")
    strat = (
        rec.get("solving_strategy")
        or rec.get("fixing_strategy")
        or rec.get("resolved_by")
    )
    if isinstance(fc, str) and isinstance(strat, str):
        return fc, strat
    return None


def measure_real_coupling() -> tuple[int, float | None]:
    pairs = [p for rec in _iter_records() if (p := _extract_pair(rec))]
    if not pairs:
        return 0, None
    hits = sum(1 for fc, strat in pairs if FAILURE_MAP.get(fc) == strat)
    return len(pairs), hits / len(pairs)


def main() -> int:
    n, p = measure_real_coupling()
    print("# Recursive-Trace VALUE Gate (Stage 2 — real corpus)\n")
    if p is None:
        print(f"  corpus pairs found: {n}")
        print("  No (failure_class, fixing_strategy) corpus exists in any known location:")
        for path in CORPUS_PATHS:
            print(f"    - {path}  [{'present' if path.exists() else 'absent'}]")
        print("\n  VERDICT: UNPROVEN")
        print("  The mechanism is implemented and unit-tested, but its production value")
        print("  cannot be confirmed or refuted without real failure-resolution data.")
        print("  This script will return KEEP or RETIRE the moment such a corpus exists.")
        return 0

    print(f"  corpus pairs found: {n}")
    print(f"  empirical p = P(fixing_strategy == failure_map[failure_class]) = {p:.3f}")
    print(f"  chance baseline = {CHANCE:.3f}, margin = {MARGIN:.3f}")
    if p > CHANCE + MARGIN:
        print("\n  VERDICT: KEEP — real failure data carries exploitable failure->strategy signal.")
    else:
        print("\n  VERDICT: RETIRE — coupling ~= chance; recursive-trace == autoresearch + dedup cache.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
