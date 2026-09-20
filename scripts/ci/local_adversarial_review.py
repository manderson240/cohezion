#!/usr/bin/env python3
"""Local multiperspective adversarial review of a diff -- three lenses, three model families,
all on the :13305 router, $0, with every claim carrying its own evidence.

Why this exists (2026-09-20). The two existing review scripts route their perspectives to
Ollama Cloud and keep one local lane. Tonight's attempt at a local QA lane on a 506-line diff
NARRATED for 1,800 tokens and never produced a verdict (the standing local-lane failure mode),
while a 30-line AST check adjudicated the same diff and caught a misreport. So this script
designs against both:

1. **No prose is accepted.** Each lane must answer with ONE JSON object in a fixed schema
   (thinking disabled, low temperature, short budget). Unparseable output is recorded as
   UNKNOWN for that lane -- never as a pass, never as a finding.
2. **Every finding names a falsifier.** A finding is a claim plus a shell command from the
   repo root whose output demonstrates it. The script RUNS the falsifier and attaches the
   output. A finding with no runnable evidence is kept but marked `unverified`; a finding
   whose falsifier runs is `evidence-attached`. The lanes generate hypotheses; the machine
   collects evidence; the human (or the next gate) adjudicates.
3. **Divergence is the signal, majority is not truth** (memories: adversarial-review-
   divergence-is-the-signal, cloud-lane-majority-is-not-a-truth-procedure). Findings that two
   lanes locate within 5 lines of each other are grouped as `converged`; the rest are listed
   per lane. A silent lane counts as UNKNOWN, not as approval.

Usage:
  python scripts/ci/local_adversarial_review.py --range 215fe125f..9005859cf
  python scripts/ci/local_adversarial_review.py --range HEAD~1..HEAD --out reviews/x.md
  python scripts/ci/local_adversarial_review.py --self-test        # schema + parser + grouping
Exit code is 0 (advisory) unless --gate is passed AND >= 2 lanes return verdict "hold".
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTER = "http://localhost:13305/v1/chat/completions"
MAX_DIFF_CHARS = 60_000
FALSIFIER_TIMEOUT_S = 120
CONVERGE_LINES = 5

LENSES: dict[str, tuple[str, str]] = {
    # lens: (model id on :13305, what this lens is told to hunt)
    "scientific-rigor": (
        "Qwen3.6-35B-A3B-GGUF",
        "claims the code makes that its tests cannot falsify; a test that would pass against "
        "a plausible WRONG implementation; a number, threshold or invariant asserted without a "
        "measurement; a docstring that promises more than the body does",
    ),
    "edge-case-hunter": (
        "Gemma-4-31B-it-GGUF",
        "inputs that break it: empty, None, NaN, negative, huge, unicode, concurrent; an "
        "exception that escapes a path documented as non-blocking; state that leaks between "
        "calls; a fallback that silently substitutes a value",
    ),
    "security": (
        "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "injection into SurrealQL/shell/f-strings from untrusted values; secrets or hosts "
        "hard-coded; writes to production stores reachable from tests; anything that reports "
        "success it did not verify",
    ),
}

SCHEMA = (
    '{"lens": "<name>", "verdict": "ship" | "hold", '
    '"findings": [{"file": "<path in diff>", "line": <int or null>, '
    '"severity": "high" | "medium" | "low", "claim": "<one sentence>", '
    '"falsifier": "<ONE shell command run from the repo root whose OUTPUT demonstrates the '
    'claim, e.g. a pytest node, a python -c, a grep -n; or null if none exists>"}]}'
)


@dataclass
class Finding:
    lens: str
    file: str
    line: int | None
    severity: str
    claim: str
    falsifier: str | None
    evidence: str | None = None
    status: str = "unverified"  # unverified | evidence-attached | falsifier-failed


@dataclass
class LaneResult:
    lens: str
    model: str
    verdict: str  # ship | hold | UNKNOWN
    findings: list[Finding] = field(default_factory=list)
    seconds: float = 0.0
    raw: str = ""


def _diff(range_: str) -> str:
    out = subprocess.run(
        ["git", "diff", range_, "--", "src/", "scripts/", "tests/", "muttest/"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    ).stdout
    if len(out) > MAX_DIFF_CHARS:
        out = out[:MAX_DIFF_CHARS] + f"\n... [diff truncated at {MAX_DIFF_CHARS} chars]\n"
    return out


def _prompt(lens: str, hunt: str, diff: str) -> str:
    return (
        f"You are the {lens} lens of an adversarial code review. Assume the change is BROKEN "
        f"and hunt specifically for: {hunt}.\n\n"
        "Judge ONLY from the diff below. Do not invent code that is not shown; if the diff does "
        "not show enough to be sure, do not report it. Report at most 6 findings, most severe "
        "first. Every finding MUST carry a falsifier: one shell command, run from the repo root, "
        "whose output demonstrates the claim (a pytest node id, `python -c ...`, `grep -n ...`). "
        "If you cannot name one, set falsifier to null.\n\n"
        f"Answer with ONE JSON object and nothing else, exactly this schema:\n{SCHEMA}\n\n"
        f"DIFF:\n{diff}"
    )


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    for candidate in (m.group(0), text):
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def parse_lane(lens: str, model: str, text: str, seconds: float) -> LaneResult:
    obj = _extract_json(text)
    if obj is None or "findings" not in obj:
        return LaneResult(lens, model, "UNKNOWN", [], seconds, text[-600:])
    verdict = obj.get("verdict") if obj.get("verdict") in ("ship", "hold") else "UNKNOWN"
    verdict = verdict or "UNKNOWN"
    findings = []
    for f in obj.get("findings") or []:
        if not isinstance(f, dict) or not f.get("claim"):
            continue
        line = f.get("line")
        findings.append(
            Finding(
                lens=lens,
                file=str(f.get("file") or "?"),
                line=int(line) if isinstance(line, int) else None,
                severity=str(f.get("severity") or "low"),
                claim=str(f["claim"]).strip(),
                falsifier=(str(f["falsifier"]).strip() or None) if f.get("falsifier") else None,
            )
        )
    return LaneResult(lens, model, verdict, findings, seconds, text[-600:])


def _ask(model: str, prompt: str, *, max_tokens: int = 1200, timeout: int = 900) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        ROUTER,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 -- localhost router
        r = json.loads(resp.read())
    return r["choices"][0]["message"]["content"]


def run_lane(lens: str, diff: str) -> LaneResult:
    model, hunt = LENSES[lens]
    prompt = _prompt(lens, hunt, diff)
    t0 = time.time()
    try:
        text = _ask(model, prompt)
        res = parse_lane(lens, model, text, time.time() - t0)
        if res.verdict == "UNKNOWN":  # one retry, JSON-only nudge
            text = _ask(model, prompt + "\n\nREMINDER: output the JSON object only.")
            res = parse_lane(lens, model, text, time.time() - t0)
        return res
    except Exception as exc:  # lane down is UNKNOWN, never a pass
        return LaneResult(lens, model, "UNKNOWN", [], time.time() - t0, f"lane error: {exc}")


_ALLOWED_PREFIXES = (
    "pytest",
    ".venv/bin/python3 -m pytest",
    "python -m pytest",
    "python3 -m pytest",
    "python -c",
    "python3 -c",
    ".venv/bin/python3 -c",
    "grep",
    "rg",
    "git grep",
    "git log",
    "git show",
    "sed -n",
    "cat ",
    "head",
    "wc",
    ".venv/bin/python3 scripts/ci/",
)


def run_falsifier(cmd: str) -> tuple[str, str]:
    """Run a lane's falsifier under a narrow allow-list; return (status, evidence)."""
    c = cmd.strip()
    if not c.startswith(_ALLOWED_PREFIXES):
        return "falsifier-failed", f"refused (not in allow-list): {c[:120]}"
    # route interpreters through the repo venv (L367); a bare `pytest` becomes a module run
    if c.startswith("pytest"):
        c = ".venv/bin/python3 -m " + c
    elif c.startswith(("python3 ", "python ")):
        c = ".venv/bin/python3 " + c.split(" ", 1)[1]
    try:
        p = subprocess.run(
            c,
            shell=True,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=FALSIFIER_TIMEOUT_S,
        )
        tail = "\n".join((p.stdout + p.stderr).splitlines()[-20:])
        return "evidence-attached", f"$ {c}\n[exit {p.returncode}]\n{tail}"
    except subprocess.TimeoutExpired:
        return "falsifier-failed", f"$ {c}\n[timeout {FALSIFIER_TIMEOUT_S}s]"


def converge(lanes: list[LaneResult]) -> list[list[Finding]]:
    """Group findings that two or more lanes place in the same file within CONVERGE_LINES."""
    all_f = [f for lane in lanes for f in lane.findings]
    groups: list[list[Finding]] = []
    used: set[int] = set()
    for i, a in enumerate(all_f):
        if i in used:
            continue
        grp = [a]
        for j, b in enumerate(all_f[i + 1 :], start=i + 1):
            if j in used or b.lens == a.lens or b.file != a.file:
                continue
            if a.line is None or b.line is None or abs(a.line - b.line) <= CONVERGE_LINES:
                grp.append(b)
                used.add(j)
        if len(grp) > 1:
            used.add(i)
            groups.append(grp)
    return groups


def render(range_: str, lanes: list[LaneResult], groups: list[list[Finding]]) -> str:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    out = [
        "---",
        "type: local-adversarial-review",
        f"range: {range_}",
        f"date: {now}",
        f"lanes: {', '.join(f'{l.lens}={l.model}' for l in lanes)}",
        "cost_usd: 0",
        "---",
        f"# Local multiperspective adversarial review: `{range_}`",
        "",
        "| lens | model | verdict | findings | seconds |",
        "|---|---|---|---|---|",
    ]
    out += [
        f"| {l.lens} | {l.model} | **{l.verdict}** | {len(l.findings)} | {l.seconds:.0f} |"
        for l in lanes
    ]
    unknown = [l.lens for l in lanes if l.verdict == "UNKNOWN"]
    if unknown:
        out += ["", f"**UNKNOWN lanes (no parseable JSON; NOT approval):** {', '.join(unknown)}"]
    out += [
        "",
        f"## Converged ({len(groups)} groups: >= 2 lanes, same file, within {CONVERGE_LINES} lines)",
    ]
    for g in groups:
        out.append(
            f"- `{g[0].file}:{g[0].line}` -- " + " | ".join(f"**{f.lens}**: {f.claim}" for f in g)
        )
    for lane in lanes:
        out += ["", f"## {lane.lens} ({lane.model}) -- {lane.verdict}"]
        if not lane.findings:
            out.append(
                "- (no findings)"
                if lane.verdict != "UNKNOWN"
                else f"- raw tail: `{lane.raw[-300:]!r}`"
            )
        for f in lane.findings:
            out.append(f"- [{f.severity}] `{f.file}:{f.line}` {f.claim}")
            out.append(f"  - status: **{f.status}**")
            if f.evidence:
                out.append("  ```\n  " + f.evidence.replace("\n", "\n  ") + "\n  ```")
    return "\n".join(out) + "\n"


def self_test() -> int:
    good = '{"lens":"x","verdict":"hold","findings":[{"file":"a.py","line":10,"severity":"high","claim":"c","falsifier":"grep -n c a.py"}]}'
    prose = "Sure! Here is my review. The code looks fine overall..."
    fenced = "```json\n" + good + "\n```"
    r1 = parse_lane("x", "m", good, 1.0)
    r2 = parse_lane("x", "m", prose, 1.0)
    r3 = parse_lane("x", "m", fenced, 1.0)
    checks = [
        (
            r1.verdict == "hold"
            and len(r1.findings) == 1
            and r1.findings[0].falsifier == "grep -n c a.py",
            "schema parse",
        ),
        (r2.verdict == "UNKNOWN" and r2.findings == [], "prose is UNKNOWN, not a pass"),
        (r3.verdict == "hold", "fenced JSON parses"),
        (run_falsifier("rm -rf /")[0] == "falsifier-failed", "allow-list refuses"),
        (
            run_falsifier("grep -n 'def self_test' scripts/ci/local_adversarial_review.py")[0]
            == "evidence-attached",
            "grep runs",
        ),
    ]
    a = Finding("l1", "f.py", 10, "high", "x", None)
    b = Finding("l2", "f.py", 13, "low", "y", None)
    c = Finding("l3", "g.py", 13, "low", "z", None)
    checks.append(
        (
            len(
                converge(
                    [
                        LaneResult("l1", "m", "ship", [a]),
                        LaneResult("l2", "m", "ship", [b]),
                        LaneResult("l3", "m", "ship", [c]),
                    ]
                )
            )
            == 1,
            "converge groups within 5 lines, same file only",
        )
    )
    bad = [label for ok, label in checks if not ok]
    if bad:
        print("SELF-TEST FAILED:", bad)
        return 1
    print(f"SELF-TEST OK: {len(checks)}/{len(checks)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Local multiperspective adversarial review")
    ap.add_argument("--range", default="HEAD~1..HEAD")
    ap.add_argument("--out", default=None, help="markdown path (default: vault reviews/)")
    ap.add_argument("--lenses", default=",".join(LENSES), help="comma list")
    ap.add_argument("--gate", action="store_true", help="exit 1 when >= 2 lanes say hold")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    diff = _diff(args.range)
    if not diff.strip():
        print(f"no diff in {args.range}")
        return 0
    lanes: list[LaneResult] = []
    for lens in args.lenses.split(","):
        lens = lens.strip()
        if lens not in LENSES:
            print(f"unknown lens {lens}", file=sys.stderr)
            return 2
        print(f"[{lens}] {LENSES[lens][0]} ...", flush=True)
        res = run_lane(lens, diff)
        for f in res.findings:
            if f.falsifier:
                f.status, f.evidence = run_falsifier(f.falsifier)
        lanes.append(res)
        print(
            f"[{lens}] verdict={res.verdict} findings={len(res.findings)} {res.seconds:.0f}s",
            flush=True,
        )

    groups = converge(lanes)
    md = render(args.range, lanes, groups)
    out = (
        Path(args.out)
        if args.out
        else (
            Path.home()
            / "vaults"
            / "cohezion-vault"
            / "reviews"
            / f"{datetime.now(UTC):%Y%m%d-%H%M}-local-adversarial-{args.range.replace('..', '-').replace('/', '_')}.md"
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(f"wrote {out}")
    holds = sum(1 for l in lanes if l.verdict == "hold")
    unknowns = sum(1 for l in lanes if l.verdict == "UNKNOWN")
    print(
        f"verdicts: hold={holds} ship={len(lanes) - holds - unknowns} unknown={unknowns}; converged groups={len(groups)}"
    )
    if args.gate and holds >= 2:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
