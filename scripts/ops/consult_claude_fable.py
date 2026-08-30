#!/usr/bin/env python3
"""REMOVED 2026-08-20 — this script FABRICATED its output. Do not restore it.

What it did: defined a hardcoded string `FABLE_CONSULTATION = \"\"\"# The Fable of the Loom, the
Metron, and the Palimpsest ...\"\"\"`, wrote that string to a vault file, and printed it. Measured
before removal: **0 network calls**, 0 subprocess calls, 0 API clients. It never consulted Fable, or
anything else. It was a 79-line constant with a filename that claimed otherwise.

Why this matters more than a dead script: its output was HARVESTED INTO THE KNOWLEDGE BASE as
`~/vaults/cohezion-vault/research/FABLE_CONSULT_BRIEF_20260819.md` (5,014 bytes), where it is
indistinguishable from a real consultation. Fabrication that reaches durable storage outlives the
process that produced it. Treat that artifact as unsourced until re-derived.

The file could not be unlinked: `<repo>/scripts` is bind-mounted `ro` (verify with
`findmnt -T scripts`), so `rm` and `git rm` both fail from an agent shell. It is neutralised in place
instead, and now FAILS LOUDLY rather than emitting a canned answer. To finish the removal:

    rm scripts/ops/consult_claude_fable.py

TO ACTUALLY CONSULT FABLE, use a real inference path — a headless session:

    source ~/.config/cohezion/safe-env.sh
    claude --print --model claude-fable-5 "$(cat prompt.txt)"

(`safe-env.sh` first: it strips the invalid PATH-like env vars that otherwise break bwrap and take
Bash down entirely — harness invariants H2/H3.)
"""

from __future__ import annotations

import sys


_REASON = (
    "consult_claude_fable.py was removed on 2026-08-20: it fabricated its output "
    "(hardcoded string, zero network calls) and its result was harvested into the vault. "
    "Use a real inference path: "
    "`claude --print --model claude-fable-5 \"$(cat prompt.txt)\"` "
    "after sourcing ~/.config/cohezion/safe-env.sh."
)


def main() -> int:
    print(f"REMOVED: {_REASON}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
