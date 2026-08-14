"""Find enum members whose names are substrings of siblings, then find code that
substring-matches them against text. That combination silently flips verdicts.

THE BUG THIS GENERALISES (src/cohezion/swarm/democratic_debate.py, found 2026-08-14):

    class VoteValue(Enum):
        STRONGLY_AGREE = 2; AGREE = 1; NEUTRAL = 0; DISAGREE = -1; STRONGLY_DISAGREE = -2

    for v in VoteValue:
        if v.name in response.upper(): vote = v; break

"AGREE" is a substring of "DISAGREE", and AGREE precedes DISAGREE in the enum, so EVERY
dissent parsed as agreement. Five agents unanimously voting STRONGLY_DISAGREE scored 0.750
consensus=True against a true 0.000 -- a consensus module reporting agreement on unanimous
dissent, silently.

TWO STAGES, because either alone is noise:

    HAZARD  an enum with substring-overlapping member names. Common and usually harmless --
            reported as informational only, never as a defect.
    DEFECT  code that matches those names against text with `in` (or startswith/find).
            Only this is reported as a finding.

A scanner that flagged every overlapping enum would cry wolf on ordinary code and be
switched off, which is worse than not having it. The two-stage split is what keeps the
signal.

SELF-TEST: `--self-test` builds a known-hazardous fixture and a known-clean one and asserts
the scan separates them. A scanner that cannot be shown to FAIL certifies nothing.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Matching an enum NAME against free text. Regex/word-boundary matching is the fix, so
# `re.search` is deliberately absent from this list.
_MATCH_CALLS = {"startswith", "endswith", "find", "index", "count"}

# The worst shape of this hazard: the longer name is the shorter one NEGATED, so a
# substring match does not merely pick the wrong member — it INVERTS the meaning.
# VALID/INVALID_CHARS, COMPATIBLE/INCOMPATIBLE, AVAILABLE/UNAVAILABLE, OPEN/HALF_OPEN,
# AGREE/DISAGREE are all this. Several sit in security and reliability code, where an
# inverted verdict fails OPEN.
_NEGATION_PREFIXES = ("IN", "UN", "DIS", "NON", "NOT_", "NO_", "HALF_")


def is_inversion(short: str, long: str) -> bool:
    """True when `long` reads as `short` negated — the meaning-flipping subclass."""
    idx = long.find(short)
    prefix = long[:idx].rstrip("_")
    return bool(prefix) and any(prefix.endswith(p.rstrip("_")) for p in _NEGATION_PREFIXES)


def enum_hazards(tree: ast.AST) -> dict[str, list[tuple[str, str]]]:
    """Enums where one member name is a substring of another. {enum: [(short, long)]}."""
    out: dict[str, list[tuple[str, str]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            (isinstance(b, ast.Name) and "Enum" in b.id)
            or (isinstance(b, ast.Attribute) and "Enum" in b.attr)
            for b in node.bases
        ):
            continue
        names = [
            t.id
            for stmt in node.body
            if isinstance(stmt, ast.Assign)
            for t in stmt.targets
            if isinstance(t, ast.Name) and t.id.isupper()
        ]
        pairs = [
            (a, b) for a in names for b in names if a != b and a in b
        ]
        if pairs:
            out[node.name] = pairs
    return out


def match_sites(tree: ast.AST) -> list[tuple[int, str]]:
    """Sites matching a `.name` attribute against text -- the part that turns a hazard
    into a defect."""
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        # `X.name in <something>`
        if isinstance(node, ast.Compare) and any(
            isinstance(op, ast.In) for op in node.ops
        ):
            left = node.left
            if isinstance(left, ast.Attribute) and left.attr == "name":
                hits.append((node.lineno, "`.name in <text>` — substring match"))
        # `<text>.startswith(X.name)` and friends
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _MATCH_CALLS:
                for a in node.args:
                    if isinstance(a, ast.Attribute) and a.attr == "name":
                        hits.append((node.lineno, f"`.{node.func.attr}(<enum>.name)`"))
    return hits


def scan(paths: list[Path]) -> tuple[list[str], list[str]]:
    hazards: list[str] = []
    defects: list[str] = []
    for p in paths:
        try:
            tree = ast.parse(p.read_text(errors="replace"))
        except (SyntaxError, OSError):
            continue
        haz = enum_hazards(tree)
        if not haz:
            continue
        rel = p.relative_to(ROOT) if p.is_relative_to(ROOT) else p
        for enum, pairs in haz.items():
            shown = ", ".join(f"{a!r}<{b!r}" for a, b in pairs[:3])
            inv = [f"{a}/{b}" for a, b in pairs if is_inversion(a, b)]
            tag = f"  INVERSION[{', '.join(inv[:2])}]" if inv else ""
            hazards.append(f"{rel}:{enum}  {shown}{tag}")
        sites = match_sites(tree)
        for lineno, why in sites:
            defects.append(f"{rel}:{lineno}  {why}  (enums here overlap: {', '.join(haz)})")
    return hazards, defects


def self_test() -> int:
    """Prove the scan discriminates before trusting a clean result."""
    hazardous = (
        "from enum import Enum\n"
        "class V(Enum):\n    AGREE = 1\n    DISAGREE = -1\n"
        "def f(resp):\n"
        "    for v in V:\n"
        "        if v.name in resp.upper():\n            return v\n"
    )
    clean_enum_only = (
        "from enum import Enum\n"
        "class V(Enum):\n    AGREE = 1\n    DISAGREE = -1\n"
        "def f(resp):\n    return V[resp]\n"          # exact lookup, no substring match
    )
    no_overlap = (
        "from enum import Enum\n"
        "class V(Enum):\n    YES = 1\n    NO = 0\n"
        "def f(resp):\n"
        "    for v in V:\n"
        "        if v.name in resp.upper():\n            return v\n"
    )
    tmp = Path("/tmp/claude-1000/_enum_scan_selftest")
    tmp.mkdir(parents=True, exist_ok=True)
    cases = {"hazardous.py": hazardous, "clean.py": clean_enum_only, "nooverlap.py": no_overlap}
    for name, src in cases.items():
        (tmp / name).write_text(src)

    fails = []
    _, d = scan([tmp / "hazardous.py"])
    if not d:
        fails.append("hazardous fixture produced NO defect — scan is blind")
    h2, d2 = scan([tmp / "clean.py"])
    if d2:
        fails.append(f"exact-lookup fixture flagged as a defect — false positive: {d2}")
    if not h2:
        fails.append("overlapping enum not reported as a hazard")
    _, d3 = scan([tmp / "nooverlap.py"])
    if d3:
        fails.append(f"non-overlapping enum flagged — false positive: {d3}")

    for f in cases:
        (tmp / f).unlink(missing_ok=True)
    for f in fails:
        print("  SELF-TEST FAIL:", f)
    print("  self-test PASS" if not fails else "  SELF-TEST FAILED")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any defect")
    ap.add_argument("paths", nargs="*", default=None)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    targets = (
        [Path(p) for p in args.paths]
        if args.paths
        else sorted((ROOT / "src").rglob("*.py"))
    )
    hazards, defects = scan(targets)
    # Frozen copies under */-archive/ are not live code. Counting them would make a CI
    # gate red forever for a file nobody runs, which is how gates get switched off.
    live_defects = [d for d in defects if "-archive/" not in d]
    archived = len(defects) - len(live_defects)

    print(f"scanned {len(targets)} files\n")
    print(f"HAZARDS — enums with substring-overlapping member names ({len(hazards)})")
    print("  informational: an overlapping enum is only dangerous if matched against text.")
    print("  INVERSION marks pairs where the longer name is the shorter NEGATED, so a")
    print("  substring match would flip the verdict rather than merely mis-pick it.\n")
    for h in hazards[:24]:
        print(f"  {h}")
    print(f"\nDEFECTS in LIVE code — enum names substring-matched against text ({len(live_defects)})")
    if not live_defects:
        print("  none")
    for d in live_defects:
        print(f"  {d}")
    if archived:
        print(f"\n  ({archived} further defect(s) in frozen -archive/ copies, not gated)")
    print(
        "\nFIX: word-boundary regex, longest-name-first, and a THIRD state for "
        "'no readable verdict' — never infer an outcome from a missing keyword."
    )
    return 1 if (args.strict and live_defects) else 0


if __name__ == "__main__":
    sys.exit(main())
