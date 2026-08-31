#!/usr/bin/env python3
"""Falsifiability scan -- the sibling of ``dormancy_scan.py``.

``dormancy_scan.py`` asks: **is this capability consumed?**
This asks the other question: **can this invariant FAIL?**

They are different defects. A capability can be fully consumed and still be guarded by an invariant
that no possible state could violate -- at which point the invariant is documentation wearing a
test's clothes, and its green result carries no information.

FOUND BY ACCIDENT 2026-07-26, which is why this exists. Harness invariant **U1** is documented as
"the Universal HIHO Theorem -- same attractor across all 7 substrates", asserting every physics
substrate returns coherence == 1.0 at x == 0.5. All seven hard-code the identical literal
``4.0 * x * (1.0 - x)`` (lenr.py:88, ionic_cluster.py:92, bec_bridge.py:86/139, mhd_plasma.py:91,
toroidal_moment.py:71, colibre_bridge.py:95). U1 verifies that one formula was typed seven times.
It cannot fail. Two of those substrates carry extra multiplicative factors and only reach 1.0 when
those are unity -- and U1's own verification snippet supplies exactly those values, so it is
*arranged* to pass, not merely guaranteed to.

Nothing was hunting for that. It surfaced because an unrelated physics paper prompted a look at the
substrates. Three sibling defects turned up the same day (a lint ratchet at baseline 749 while real
debt was 471; a ``--timeout`` abort logged as a suite result; ``save_validated_query`` containing a
docstring asking the model to self-certify). The common shape: **a declaration nothing verified
against its referent.** This script makes the search mechanical instead of accidental.

WHAT IT FLAGS (deterministic, no LLM, no network):

  EXISTENCE-ONLY -- the stated verification can only prove a symbol EXISTS: ``hasattr``,
    ``inspect.signature(...).parameters``, ``in dir(...)``, ``'name' in inspect.getsource(...)``,
    ``dataclasses.fields`` membership, grep-for-def. These pass for a symbol that is defined and
    does nothing. Structural checks are legitimate and cheap (the V-model
    structural-before-behavioral rule earns them), but an invariant with ONLY a structural check has
    no behavioural guarantee, and that should be visible rather than implied.

  SELF-REFERENTIAL -- the verification compares a value against a literal restated from the same
    document, or asserts a constant equals itself. The U1 shape.

WHAT IT DELIBERATELY DOES NOT DO: decide whether a behavioural check is a GOOD one. That needs
judgment. This narrows 127 documented invariants to the subset provably incapable of failing, so a
human reads a short list instead of everything.

REPORT MODE BY DEFAULT, matching ``systemd_unit_audit.py`` and ``graph_cardinality_audit.py``:
findings are pre-existing and expected. ``--strict`` exits non-zero for later CI wiring, once a
baseline is agreed.

    python scripts/ci/falsifiability_scan.py            # report (always exit 0)
    python scripts/ci/falsifiability_scan.py --strict   # exit 1 if any EXISTENCE-ONLY found
    python scripts/ci/falsifiability_scan.py --self-test
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]

DOCS = [
    Path.home() / ".claude" / "rules" / "harness.md",
    REPO / ".claude" / "rules" / "harness.md",
    REPO / "src" / "cohezion" / "compound" / "CLAUDE.md",
]

# A verification built only from these proves a symbol exists. It cannot observe behaviour.
EXISTENCE_ONLY = (
    r"hasattr\s*\(",
    r"inspect\.signature\s*\(",
    r"\bin\s+dir\s*\(",
    r"inspect\.getsource\s*\(",
    r"dataclasses\.fields\s*\(",
    r"\{\s*f\.name\s+for\s+f\s+in",
    r"grep\s+-n?E?\s*[\"']?def\s",
)

# A verification containing one of these actually runs something that can disagree with reality.
BEHAVIOURAL = (
    r"\bpytest\b",
    r"\bcurl\b",
    r"journalctl",
    r"\bassert\s+abs\s*\(",  # numeric comparison
    r"==\s*-?\d+\.\d+",  # compared against a specific value
    r"<=|>=|<|>",  # a threshold
    r"\.run\s*\(|\.check_|\(\)\s*==",
)

INVARIANT_RE = re.compile(r"^#{2,4}\s+([A-Z][A-Za-z0-9_]*\d[a-z]?)\s*[:\-—]", re.M)
VERIFY_RE = re.compile(r"\*\*Verification\*\*\s*:?(.+?)(?=\n\s*[-*]\s*\*\*|\n#{2,4}\s|\Z)", re.S)


def classify(verification: str) -> str:
    """EXISTENCE-ONLY / BEHAVIOURAL / SELF-REFERENTIAL, from the verification text alone."""
    has_existence = any(re.search(p, verification) for p in EXISTENCE_ONLY)
    has_behaviour = any(re.search(p, verification) for p in BEHAVIOURAL)
    if has_existence and not has_behaviour:
        return "EXISTENCE-ONLY"
    # `X == X` with the same token on both sides proves nothing about the world.
    for lhs, rhs in re.findall(r"([\w.\[\]'\"]+)\s*==\s*([\w.\[\]'\"]+)", verification):
        if lhs == rhs:
            return "SELF-REFERENTIAL"
    return "BEHAVIOURAL" if has_behaviour else "UNCLASSIFIED"


def scan(paths: list[Path]) -> list[tuple[str, str, str, str]]:
    """-> [(doc, invariant, verdict, first line of the verification)]"""
    out: list[tuple[str, str, str, str]] = []
    for doc in paths:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        marks = [(m.group(1), m.start()) for m in INVARIANT_RE.finditer(text)]
        for i, (name, start) in enumerate(marks):
            end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
            block = text[start:end]
            v = VERIFY_RE.search(block)
            if not v:
                out.append((doc.name, name, "NO-VERIFICATION", ""))
                continue
            body = v.group(1).strip()
            out.append((doc.name, name, classify(body), " ".join(body.split())[:88]))
    return out


def self_test() -> int:
    """Discriminating: each case must be classified differently from the others."""
    cases = [
        ("`hasattr(SkillRefiner(), '_goal_epoch')`", "EXISTENCE-ONLY"),
        ("`'promotion_gate' in inspect.signature(X.__init__).parameters`", "EXISTENCE-ONLY"),
        ("`uv run pytest tests/compound/test_jepa_gate.py -q` -> 20 passed", "BEHAVIOURAL"),
        ("`assert abs(higuchi_fd(series) - 1.5) < 1e-6`", "BEHAVIOURAL"),
        ("`_MIN_TIER_FREQUENCY == _MIN_TIER_FREQUENCY`", "SELF-REFERENTIAL"),
    ]
    bad = [(t, want, got) for t, want in cases if (got := classify(t)) != want]
    for t, want, got in bad:
        print(f"  SELF-TEST FAIL: want {want}, got {got}: {t}")
    print(f"self-test: {len(cases) - len(bad)}/{len(cases)} passed")
    return 1 if bad else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    rows = scan(DOCS)
    if not rows:
        print("falsifiability scan: no invariant blocks found -- check DOCS paths")
        return 0

    buckets: dict[str, list[tuple[str, str, str, str]]] = {}
    for r in rows:
        buckets.setdefault(r[2], []).append(r)

    print(f"falsifiability scan -- {len(rows)} documented invariants\n")
    for verdict in (
        "EXISTENCE-ONLY",
        "SELF-REFERENTIAL",
        "NO-VERIFICATION",
        "UNCLASSIFIED",
        "BEHAVIOURAL",
    ):
        hits = buckets.get(verdict, [])
        if not hits:
            continue
        mark = "OK " if verdict == "BEHAVIOURAL" else "!! "
        print(f"{mark}{verdict}: {len(hits)}")
        if verdict != "BEHAVIOURAL":
            for doc, name, _, snippet in hits[:40]:
                print(f"     {name:<10} {doc:<26} {snippet}")
        print()

    weak = len(buckets.get("EXISTENCE-ONLY", []))
    print(f"{weak} invariant(s) can only prove a symbol EXISTS -- no behavioural guarantee.")
    print("Structural checks are legitimate (V-model structural-before-behavioural); an invariant")
    print(
        "with ONLY one is a declaration, and its green result carries no behavioural information."
    )
    if "--strict" in sys.argv and weak:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
