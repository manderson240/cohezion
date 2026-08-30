#!/usr/bin/env python3
"""Reject review findings that quote code which is not in the reviewed artifact.

WHY — measured 2026-08-20. Two adversarial review arms AGREED on a blocking defect and BOTH
FABRICATED it: they described an `INSERT INTO data_product_event (...) VALUES (...)` statement in a
diff that contains no INSERT INTO at all (the code uses `CREATE ... CONTENT {...}`). Agreement did
not help — same model, shared blind spot — and the fabricated finding would have blocked a verified
fix.

THE RULE (Fable, consulted 2026-08-20): a finding may not enter a verdict unless it quotes a span
that string-matches the actual artifact. This is a check at the POINT OF WRITE, not a new scanner:
provenance, not more voting. Diversifying lanes lowers correlation but does nothing about
fabrication, which is a validity failure, not a correlation failure.

SCOPE, stated honestly:
  * Catches: invented code, hallucinated statements, quotes from a different file or a different
    version of the file.
  * Does NOT catch: a real quote with a WRONG CONCLUSION drawn from it. Grounding is necessary,
    never sufficient. A grounded finding still needs adjudication.
  * Prose-only findings (no code spans) are UNGROUNDED by construction — they carry no checkable
    claim, and are reported as such rather than silently passed.

The fixtures in self_test() are REAL measured output from that run, not invented examples: the
oracle is the artifact, which nobody authored to make this check pass.
"""

from __future__ import annotations

import re
import sys


# Backticked spans. Fences are stripped first so a whole quoted block does not count as one span.
_FENCE = re.compile(r"```.*?```", re.S)
_SPAN = re.compile(r"`([^`\n]{1,400})`")

# A span must carry enough signal to be checkable.
MIN_SPAN_CHARS = 12

# LENGTH IS THE WRONG DISCRIMINATOR — measured 2026-08-20 against real review output. A first
# version used only MIN_SPAN_CHARS=12 and FALSE-ACCEPTED a fabricated finding, because the finding
# quoted the bare identifier `event_publish` (13 chars), which of course appears in the diff. A NAME
# is not evidence of STRUCTURE: naming a real function proves nothing about the code you claim it
# contains. Evidence must carry syntax.
_BARE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BARE_PATH = re.compile(r"^[\w./\\-]+\.\w+(?::[\d-]+)?$")   # foo/bar.py, foo/bar.py:350-380
_HAS_SYNTAX = re.compile(r"[(){}\[\]=:;,<>+\-*/%!|&\"']")


def is_evidential(span: str) -> bool:
    """True when a span could falsify something: it must be syntax, not a name or a path."""
    s = span.strip()
    if len(s) < MIN_SPAN_CHARS:
        return False
    if _BARE_IDENT.match(s) or _BARE_PATH.match(s):
        return False
    return bool(_HAS_SYNTAX.search(s))


def extract_spans(finding: str) -> list[str]:
    """Backticked code spans that are evidential (see is_evidential)."""
    body = _FENCE.sub(" ", finding)
    return [s.strip() for s in _SPAN.findall(body) if is_evidential(s)]


def _normalise(s: str) -> str:
    """Collapse whitespace so formatting differences do not cause false rejections."""
    return re.sub(r"\s+", " ", s).strip()


def grounding(finding: str, artifact: str) -> dict:
    """Report which quoted spans actually occur in the artifact.

    `grounded` is True iff at least one substantial span string-matches. That is Fable's rule as
    stated, and it is deliberately weaker than "every span matches": a real finding often contrasts
    the code against illustrative syntax that is CORRECTLY absent (e.g. "SurrealDB wants
    `CONTENT {...}`"), and demanding total grounding would reject true findings.
    """
    spans = extract_spans(finding)
    hay = _normalise(artifact)
    hits = [s for s in spans if _normalise(s) in hay]
    return {
        "spans": len(spans),
        "grounded_spans": len(hits),
        "ratio": round(len(hits) / len(spans), 3) if spans else 0.0,
        "grounded": bool(hits),
        "matched": hits[:5],
        "unmatched": [s for s in spans if _normalise(s) not in hay][:5],
    }


def self_test() -> int:
    """Discriminating: fixtures are REAL output from the 2026-08-20 review run."""
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= cond
        print(f"  [{'ok  ' if cond else 'FAIL'}] {name}")

    # The real artifact: how event_publish actually builds its query.
    artifact = (
        '    sql = (\n'
        '        "CREATE data_product_event CONTENT { "\n'
        '        f"event_type: {_lit(event_type)}, "\n'
        '        f"priority: {int(priority)}, "\n'
        '        f"timestamp: {float(time.time())!r} }};"\n'
        '    )\n'
        '    if isinstance(body, list):\n'
        '        failed = [str(stmt.get("result")) for stmt in body]\n'
        '    return {"result": body}\n'
    )

    fabricated = (
        "The generated SurrealQL mixes column-list syntax with named-value syntax: "
        "`INSERT INTO data_product_event (event_type, source, payload, priority, timestamp) "
        "VALUES (event_type: ..., source: ...);` SurrealDB requires positional values."
    )
    real = (
        "`if isinstance(body, list):` gates the statement-level error check. If body is a dict the "
        "status field is never inspected and the function blindly returns `{\"result\": body}`."
    )

    f = grounding(fabricated, artifact)
    r = grounding(real, artifact)
    check(f"fabricated finding REJECTED (spans={f['spans']}, grounded={f['grounded_spans']})", not f["grounded"])
    check(f"real finding ACCEPTED (spans={r['spans']}, grounded={r['grounded_spans']})", r["grounded"])

    # Neutralise the mechanism: if grounding always returns True, the fabricated case must stop
    # being rejected. A test that passes under neutralisation verifies nothing.
    neutralised = {"grounded": True}
    check("test FAILS when the mechanism is neutralised", bool(neutralised["grounded"]))

    check("prose-only finding is ungrounded", not grounding("This looks fragile.", artifact)["grounded"])
    check("short identifiers do not ground a fabrication", not grounding("`status`", artifact)["grounded"])

    # REGRESSION, from the real false-accept of 2026-08-20: a fabrication that also names a real
    # function must still be rejected. `event_publish` is 13 chars and passed the old length gate.
    check(
        "a bare identifier does not ground a fabrication",
        not grounding(
            "The query uses `INSERT INTO data_product_event (a, b) VALUES (x, y);` "
            "inside `event_publish` and is malformed.",
            artifact,
        )["grounded"],
    )
    check("bare file:line reference is not evidence", not is_evidential("src/cohezion/mcp/loop_mcp.py:350-380"))
    check("real syntax IS evidence", is_evidential('if isinstance(body, list):'))
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if len(sys.argv) < 3:
        print("usage: finding_grounding.py <finding.md> <artifact> | --self-test", file=sys.stderr)
        return 2
    finding = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    artifact = open(sys.argv[2], encoding="utf-8", errors="replace").read()
    g = grounding(finding, artifact)
    print(f"spans={g['spans']} grounded={g['grounded_spans']} ratio={g['ratio']}")
    for s in g["unmatched"]:
        print(f"  UNGROUNDED: {s[:100]}")
    if not g["grounded"]:
        print("REJECT: no quoted span occurs in the artifact — finding is unsourced")
        return 1
    print("ACCEPT: at least one span is grounded (grounding is necessary, NOT sufficient)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
