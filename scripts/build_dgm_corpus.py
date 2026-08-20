#!/usr/bin/env python3
"""Digest the CS236 Deep Generative Models notes on local silicon, with a groundedness gate.

Why a gate: the prior Strix Halo corpus quarantined a note in which the model invented 15
benchmark numbers, because that page's tables rendered as images and the extracted text had
headings but no data. The same trap is live here — the published HTML DROPS display equations,
turning "optimization of $q$ by applying the update <eq>" into prose with holes. We therefore
digest the **markdown sources** (LaTeX intact), and verify every technical token a note claims
actually occurs in its source.

Usage: python scripts/build_dgm_corpus.py <md_dir> <out_dir>
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from durable_swarm_output import DurableRun  # noqa: E402

LEMONADE = "http://localhost:13305/api/v1/chat/completions"
MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"

PROMPT = """You are building a LEARNING CORPUS note from a Stanford CS236 (Deep Generative
Models) source page. The source is markdown with LaTeX intact.

ABSOLUTE RULE: use ONLY what is in the source below. Do not add background knowledge, do not
invent equations, do not supply numbers. If the source does not state something, omit it. A
shorter, fully-grounded note is CORRECT; a longer note with one invented detail is WORTHLESS.

Write a compact study note with exactly these sections:

CORE IDEA: two sentences.
KEY OBJECTS: the named mathematical objects/distributions this page defines (names only, as the
source writes them).
CENTRAL RESULT: the single most important equation or inequality, described in words plus its
LaTeX exactly as it appears in the source.
WHY IT MATTERS: two sentences on what problem this solves.
GOTCHA: one thing the source explicitly warns about or calls difficult.

SOURCE PAGE ({name}):
---
{body}
---
"""


def call(body: str, name: str, timeout: int = 600) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT.format(name=name, body=body[:16000])}],
        # Thinking model: measured 8,798 chars of reasoning_content on vae.md, which consumed
        # 2,723 of a 3,000-token budget and left content EMPTY. See
        # skill thinking-model-token-budget-gate-trap.
        "max_tokens": 9000,
        "temperature": 0.15,
    }).encode()
    req = urllib.request.Request(LEMONADE, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return (d["choices"][0]["message"].get("content") or "").strip()


def groundedness(note: str, source: str) -> dict:
    """Fraction of the note's technical tokens that occur in the source.

    Deliberately crude and deliberately strict about the class that matters: NUMBERS and
    LaTeX commands are what get fabricated. Prose words are excluded from the numeric score
    because a summary legitimately paraphrases.
    """
    src = source.lower()
    nums = re.findall(r"\d+(?:\.\d+)?", note)
    tex = re.findall(r"\\[a-zA-Z]+", note)
    checked = [t for t in nums + tex if len(t) >= 2]
    # An empty or token-free note must NOT score 1.0. Measured 2026-08-19: the first run of
    # this script returned 0-byte notes for vae and gan (thinking-model budget exhaustion) and
    # this gate passed both at score 1.0 because there was nothing to check. A gate that cannot
    # register a failure is not a gate.
    if len(note.strip()) < 200:
        return {"checked": 0, "grounded": 0, "score": 0.0, "missing": ["<empty-or-stub-note>"]}
    if not checked:
        # Real prose but zero numbers and zero LaTeX — for these pages that means the required
        # CENTRAL RESULT equation was omitted. Not fabrication, but not usable either.
        return {"checked": 0, "grounded": 0, "score": 0.0, "missing": ["<no-technical-tokens>"]}
    missing = [t for t in checked if t.lower() not in src]
    return {
        "checked": len(checked),
        "grounded": len(checked) - len(missing),
        "score": round((len(checked) - len(missing)) / len(checked), 3),
        "missing": sorted(set(missing))[:12],
    }


def main() -> None:
    md_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    run = DurableRun.attach("dgm-cs236-corpus")
    print(f"run dir: {run.dir}")

    for f in sorted(md_dir.glob("*.md")):
        src = f.read_text(encoding="utf-8", errors="replace")
        try:
            note = call(src, f.stem)
        except Exception as e:  # noqa: BLE001
            note, err = "", f"{type(e).__name__}: {e}"
            run.record_lane({"lane": f.stem, "rejected": err})
            print(f"  {f.stem:<16} FAILED {err}")
            continue
        g = groundedness(note, src)
        verdict = "OK" if g["score"] >= 0.8 else "QUARANTINED"
        (out_dir / f"{f.stem}.md").write_text(note)
        run.record_lane({"lane": f.stem, "verdict": verdict, "groundedness": g,
                         "chars": len(note), "rejected": "" if verdict == "OK" else "ungrounded"})
        print(f"  {f.stem:<16} {verdict:<12} score={g['score']:<6} "
              f"checked={g['checked']:<4} missing={g['missing'][:5]}")

    run.finalize({"source": "github.com/deepgenerativemodels/notes", "model": MODEL})
    print(f"finalized: {run.dir}")


if __name__ == "__main__":
    main()
