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
import shlex
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
        "whose output demonstrates the claim. Only read-only commands run: `pytest <node id>`, "
        "`grep -n ...`, `git log/show/grep ...`, `sed -n N,Mp <file>`, `head`/`cat`/`wc`; "
        "inline code (`python -c`) and anything that writes a file is refused. "
        "If you cannot name one, set falsifier to null.\n\n"
        f"Answer with ONE JSON object and nothing else, exactly this schema:\n{SCHEMA}\n\n"
        f"DIFF:\n{diff}"
    )


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    # Third attempt: local models put RAW newlines inside string values (Gemma-4-31B did, first
    # live run) -- invalid JSON, but structurally intact; newlines outside strings are whitespace,
    # so flattening them is lossless for the object and recovers the lane instead of UNKNOWN.
    for candidate in (m.group(0), text, m.group(0).replace("\n", " ")):
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
    if verdict == "UNKNOWN" and obj.get("findings") == []:
        verdict = "ship"  # a parsed empty list is an answer; silence is not (Gemma-4-31B, run 3)
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
    last_exc: Exception | None = None
    for attempt in range(2):  # a 404/503 during a model swap on :13305 is transient (measured)
        try:
            text = _ask(model, prompt)
            res = parse_lane(lens, model, text, time.time() - t0)
            if res.verdict == "UNKNOWN":  # one retry, JSON-only nudge
                text = _ask(model, prompt + "\n\nREMINDER: output the JSON object only.")
                res = parse_lane(lens, model, text, time.time() - t0)
            return res
        except Exception as exc:  # lane down is UNKNOWN, never a pass
            last_exc = exc
            if attempt == 0:
                time.sleep(30)
    return LaneResult(lens, model, "UNKNOWN", [], time.time() - t0, f"lane error: {last_exc}")


_SHELL_META = re.compile(r"[;&|`$<>\\]|\$\(")

# Positive allow-list over argv (2026-09-21 adversarial review). The falsifier is written by a
# local model reading an untrusted diff, so it is untrusted input: it may READ the repo, never
# write a file or run code of its own. Refused, by construction: interpreter inline code
# (python -c), git --output / --ext-diff / -O / global -c, sed write/exec commands (w W e) and
# -i / -f / -e, rg --pre, pytest file-writing and plugin flags.
_PYTHONS = ("python", "python3", ".venv/bin/python", ".venv/bin/python3")
_READ_TOOLS = {"grep", "cat", "head", "wc"}
_GIT_READ_SUBCOMMANDS = {"log", "show", "grep"}
_GIT_REFUSED = ("--output", "--ext-diff", "--textconv", "-O", "--open-files-in-pager")
_RG_REFUSED = ("--pre",)
_SED_PRINT_SCRIPT = re.compile(r"^\d+(,\d+)?p$")
_PYTEST_FLAGS = {"-q", "-qq", "-v", "-x", "-s", "-rA", "--no-header", "--co", "--collect-only"}
_PYTEST_FLAGS_WITH_VALUE = {"-k", "-m"}
_PYTEST_FLAG_PREFIXES = ("--tb=", "-p", "--version")
_SCRIPT_FLAGS = {"--self-test", "--help"}


def _refuse_reason(argv: list[str]) -> str | None:
    """None when *argv* is an allowed read-only falsifier, else why it is refused."""
    if not argv:
        return "empty"
    head, rest = argv[0], argv[1:]
    if head in _READ_TOOLS:
        return None
    if head == "rg":
        bad = [a for a in rest if a.startswith(_RG_REFUSED)]
        return f"rg {bad[0]} runs a command" if bad else None
    if head == "git":
        if not rest or rest[0] not in _GIT_READ_SUBCOMMANDS:
            return "git: only log/show/grep, with no global options"
        # short options bundle (`-nO<cmd>`), so any single-dash token carrying O is refused
        bad = [
            a
            for a in rest[1:]
            if a.startswith(_GIT_REFUSED) or (a[:1] == "-" and a[1:2] != "-" and "O" in a)
        ]
        return f"git {bad[0]} writes a file or runs a program" if bad else None
    if head == "sed":
        if not rest or rest[0] != "-n" or len(rest) < 2:
            return "sed: only `sed -n <N[,M]p> <file>...`"
        if not _SED_PRINT_SCRIPT.match(rest[1]):
            return "sed: script must be a line-range print (N[,M]p)"
        opts = [a for a in rest[2:] if a.startswith("-")]
        return f"sed: no options after the script ({opts[0]})" if opts else None
    if head == "pytest":
        return _pytest_refusal(rest)
    if head in _PYTHONS:
        if rest[:2] == ["-m", "pytest"]:
            return _pytest_refusal(rest[2:])
        if len(rest) >= 1 and re.fullmatch(r"scripts/ci/[A-Za-z0-9_]+\.py", rest[0]):
            extra = [a for a in rest[1:] if a not in _SCRIPT_FLAGS]
            return f"scripts/ci: only --self-test/--help ({extra[0]})" if extra else None
        return "python: only `-m pytest` or `scripts/ci/<name>.py --self-test` (no inline code)"
    return "not in allow-list"


def _pytest_refusal(args: list[str]) -> str | None:
    i = 0
    while i < len(args):
        a = args[i]
        if a in _PYTEST_FLAGS_WITH_VALUE:
            i += 2
            continue
        if a in _PYTEST_FLAGS or (
            a.startswith(_PYTEST_FLAG_PREFIXES) and not _is_plugin_load(a, args, i)
        ):
            i += 2 if a == "-p" else 1
            continue
        if a.startswith("-"):
            return f"pytest: flag {a} is not allow-listed"
        i += 1
    return None


def _is_plugin_load(a: str, args: list[str], i: int) -> bool:
    """`-p no:X` disables a plugin (allowed); any other -p LOADS one (runs its code)."""
    if not a.startswith("-p"):
        return False
    value = a[2:] or (args[i + 1] if i + 1 < len(args) else "")
    return not value.startswith("no:")


def run_falsifier(cmd: str) -> tuple[str, str]:
    """Run a lane's falsifier under a positive argv allow-list; return (status, evidence).

    Found by the scientific-rigor lens on its own first review of this file (2026-09-21): a
    prefix allow-list plus ``shell=True`` let ``grep x; rm -rf /`` through. Then no shell
    metacharacters, ``shlex`` tokenisation, and no shell. A second review the same day found
    the prefix list still admitted ``python3 -c`` (arbitrary code), ``git log --output=<f>``
    and ``sed 'w <f>'``, so the check is now over argv against :func:`_refuse_reason`: a
    falsifier may read the repo and run its tests, never write a file or run inline code.
    """
    c = cmd.strip()
    if _SHELL_META.search(c):
        return "falsifier-failed", f"refused (shell metacharacter): {c[:120]}"
    try:
        argv = shlex.split(c)
    except ValueError as exc:
        return "falsifier-failed", f"refused (unparseable): {exc}: {c[:120]}"
    reason = _refuse_reason(argv)
    if reason is not None:
        return "falsifier-failed", f"refused ({reason}): {c[:120]}"
    # route interpreters through the repo venv (L367); a bare `pytest` becomes a module run.
    # Fall back to this interpreter when the checkout has no .venv (worktrees often don't):
    # a missing binary used to raise FileNotFoundError and discard every lane's results.
    venv_py = REPO_ROOT / ".venv" / "bin" / "python3"
    py = str(venv_py) if venv_py.exists() else sys.executable
    if argv[0] == "pytest":
        argv = [py, "-m", *argv]
    elif argv[0] in _PYTHONS:
        argv = [py, *argv[1:]]
    shown = shlex.join(argv)
    try:
        p = subprocess.run(
            argv, capture_output=True, text=True, cwd=REPO_ROOT, timeout=FALSIFIER_TIMEOUT_S
        )
        # drop import-time logger chatter so the evidence shows the falsifier's answer
        noise = ("Registered model provider", "Vault is locked", "[DBA]")
        lines = [ln for ln in (p.stdout + p.stderr).splitlines() if not any(n in ln for n in noise)]
        tail = "\n".join(lines[-20:])
        return "evidence-attached", f"$ {shown}\n[exit {p.returncode}]\n{tail}"
    except subprocess.TimeoutExpired:
        return "falsifier-failed", f"$ {shown}\n[timeout {FALSIFIER_TIMEOUT_S}s]"
    except (OSError, ValueError) as exc:  # missing binary: this finding only
        return "falsifier-failed", f"$ {shown}\n[could not run: {type(exc).__name__}: {exc}]"


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
            run_falsifier("grep -n x README.md; rm -rf /")[0] == "falsifier-failed",
            "no second command behind a `;`",
        ),
        (run_falsifier("grep -n x README.md | sh")[0] == "falsifier-failed", "no pipe"),
        (run_falsifier("grep -n $(id) README.md")[0] == "falsifier-failed", "no substitution"),
        (
            parse_lane("x", "m", '{"findings": []}', 1.0).verdict == "ship",
            "parsed empty findings is ship, not UNKNOWN",
        ),
        (
            run_falsifier("grep -n 'def self_test' scripts/ci/local_adversarial_review.py")[0]
            == "evidence-attached",
            "grep runs",
        ),
        (
            # In a checkout without .venv this raised FileNotFoundError and killed the review.
            "[exit 0]" in run_falsifier("python3 -m pytest --version")[1],
            "python falsifier runs with or without a repo .venv",
        ),
        (
            run_falsifier('python3 -c "print(7)"')[0] == "falsifier-failed",
            "no inline interpreter code",
        ),
        (run_falsifier("git log -1 --output=x")[0] == "falsifier-failed", "no git --output"),
        (run_falsifier("sed -n 'w x' README.md")[0] == "falsifier-failed", "no sed write"),
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
