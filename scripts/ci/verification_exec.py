#!/usr/bin/env python3
"""verification_exec.py — do the inline `**Verification**:` commands in harness.md RUN?

WHY THIS EXISTS (2026-08-28)
----------------------------
harness.md carries 93 invariants, each ending in a `**Verification**:` command that says
"run this and it proves the invariant". Two sibling gates already check the docs:

    doc_code_consistency.py  REFERENTIAL truth — do the names in the doc resolve?
    pass_count_check.py      ENUMERATIVE truth — does "-> 12 passed" match the test count?

Neither ever EXECUTES the command. That is the third kind of truth — OPERATIONAL — and the
repo has already paid for its absence twice, both recorded in harness.md itself:

    S2  (stealthskater)  the tradition was silently dropped in a rewrite. The invariant sat
                         green-by-assumption until someone RAN its one-line command, months
                         later. harness.md's own note: "inline verifications must be RUN,
                         not assumed green."
    LM3 (generate_text)  the snippet put `assert` inside a list comprehension — a SyntaxError.
                         It was never executable, so it had never verified anything, ever.

A command nobody runs is a claim, not evidence. This script runs them.

WHAT IT CHECKS
  V1  every `**Verification**:` block yields an extractable command      -> UNPARSED is an ERROR
  V2  every python snippet COMPILES                                      -> SYNTAX = never a check
  V3  every python snippet EXITS 0                                       -> ASSERT = live regression
  V4  every repo-local shell command exits 0                             -> STALE tooling
  V5  a snippet must be a COMMAND, not prose typed in command position   -> PROSE = no verification

CLASSIFICATION IS THE POINT. The failure modes mean different things and must not be pooled:

    SYNTAX     the check never ran, so the invariant has never been verified  (worst kind)
    PROSE      a sentence in command position; reads like a check, cannot be one
    STALE_REF  Import/Attribute/NameError — the code moved and the doc did not
    ASSERT     the command ran and the assertion FAILED — the invariant is violated NOW
    TIMEOUT    an unbounded "verification" is not one (cf. EB1b: bound every drain)
    EXTERNAL   needs a live port / a CLI outside this repo — SKIPPED, never counted green

DELIBERATELY REPORT-ONLY. pass_count_check.py records why: doc_code_consistency.py is a
BLOCKING gate whose self-test has been broken before as a downstream symptom of an unrelated
revert. Prove a new gate out on real drift before wiring it into automerge_guard.

Run:  python scripts/ci/verification_exec.py                # report (exit 0)
      python scripts/ci/verification_exec.py --classify-only # ~40ms, no subprocesses
      python scripts/ci/verification_exec.py --strict        # exit 1 on any hard failure
      python scripts/ci/verification_exec.py --with-pytest   # also run the 49 pytest targets
      python scripts/ci/verification_exec.py --json out.json
      python scripts/ci/verification_exec.py --self-test     # prove each class can go RED
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / ".claude" / "rules" / "harness.md"

TIMEOUT_S = 120

# A fenced block (```python ... ```) or an inline span (`...`). Kept separate on purpose:
# a single pattern with an optional `(?:bash|sh|python)?` language prefix silently EATS the
# literal word `python` from an inline shell command, turning
#   `python scripts/ci/foo.py --self-test`  into  `scripts/ci/foo.py --self-test`
# which then fails as a NameError and reads as a stale reference. Found while probing.
FENCE_RE = re.compile(r"```(?:bash|sh|shell|python|py)?\n(.+?)```", re.S)
INLINE_RE = re.compile(r"`([^`\n]+(?:\n[^`]*?)?)`", re.S)

# `tests/foo.py::Klass::test_x` cited with no `pytest` keyword — a pytest target all the same.
NODEID_RE = re.compile(r"^tests/[\w/.-]+\.py(?:::\w+)*$")
PY_DASH_C_RE = re.compile(r'python3?\s+-c\s+(?P<q>["\'])(?P<body>.+)(?P=q)\s*$', re.S)

# Needs something this process cannot or must not stand up: a live inference port, the
# `claude` CLI, a user's shell profile. Skipped with a reason — never silently passed.
EXTERNAL_MARKERS = (
    "localhost:",
    "127.0.0.1",
    ":13305",
    ":13306",
    ":13307",
    ":13309",
    "claude --print",
    "source ~/",
    "curl ",
    "surreal ",
    "http://",
)

# Leading tokens that make a snippet unambiguously Python even when it fails to parse.
PY_KEYWORDS = frozenset(
    {
        "assert",
        "import",
        "from",
        "def",
        "class",
        "if",
        "for",
        "while",
        "with",
        "return",
        "lambda",
        "print",
        "raise",
        "try",
        "async",
        "await",
        "del",
        "global",
    }
)

Kind = str  # python | pytest | shell | grep | prose | external | unparsed


@dataclass
class Result:
    line: int
    kind: Kind
    status: str  # PASS | SYNTAX | PROSE | STALE_REF | ASSERT | TIMEOUT | FAIL | SKIP | UNPARSED
    command: str
    detail: str = ""

    @property
    def hard(self) -> bool:
        """A failure that means the invariant is not actually verified."""
        return self.status in {
            "SYNTAX",
            "PROSE",
            "STALE_REF",
            "ASSERT",
            "TIMEOUT",
            "FAIL",
            "UNPARSED",
        }


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)
    interpreter: str = ""
    interpreter_warning: str = ""


def find_interpreter() -> tuple[str, str]:
    """The repo venv, explicitly — never bare `sys.executable` (coding-standards L367).

    A worktree without its own `.venv` is the live hazard here: `sys.executable` under
    `uv run` resolves to whichever venv launched the process, which during development of
    this script was *another worktree's* venv. That silently verifies the wrong tree.
    """
    local = REPO / ".venv" / "bin" / "python3"
    if local.exists():
        return str(local), ""
    # A worktree under <main>/.worktrees/<name> — walk up to the main checkout.
    for parent in REPO.parents:
        cand = parent / ".venv" / "bin" / "python3"
        if cand.exists() and (parent / "pyproject.toml").exists():
            return str(cand), f"no .venv in {REPO}; using main checkout venv {cand}"
    return (
        sys.executable,
        f"no repo .venv found; falling back to sys.executable ({sys.executable})",
    )


def iter_blocks(text: str):
    """Yield (line_no, body) for each `**Verification**:` block, including wrapped lines."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "**Verification**" not in line:
            continue
        chunk = [line]
        j = i + 1
        while (
            j < len(lines)
            and lines[j].strip()
            and not lines[j].lstrip().startswith("- **")
            and not lines[j].startswith("#")
        ):
            chunk.append(lines[j])
            j += 1
        yield (
            i + 1,
            "\n".join(chunk).split("**Verification**", 1)[1].lstrip(": ").strip(),
        )


def extract(body: str) -> str | None:
    """The command, with NEWLINES PRESERVED.

    Collapsing whitespace with `" ".join(cmd.split())` is the obvious normalisation and it
    is wrong: a multi-line `python -c "..."` script becomes one line, its indented
    continuation lines land mid-statement, and the snippet reports SyntaxError. That
    manufactures the exact "this was never executable" finding the gate exists to detect --
    a false positive indistinguishable from the real thing. Markdown wraps the block with
    leading indentation, so strip per line and drop blank lines, but keep the structure.
    """
    m = FENCE_RE.search(body) or INLINE_RE.search(body)
    if not m:
        return None
    lines = [ln.strip() for ln in m.group(1).splitlines()]
    return "\n".join(ln for ln in lines if ln)


def classify(cmd: str) -> Kind:
    if any(marker in cmd for marker in EXTERNAL_MARKERS):
        return "external"
    if "pytest" in cmd or NODEID_RE.match(cmd):
        return "pytest"
    if cmd.startswith("grep"):
        return "grep"
    body = PY_DASH_C_RE.search(cmd)
    if body:
        return "python"
    # A bare snippet that parses as Python AND does real work (imports or binds names) is a
    # python check. One that only evaluates an expression against names it never defines is
    # PROSE -- a sentence typed where a command belongs (`result.metrics["suggested_tier"]
    # in {"npu", ...}` is a claim about a variable no interpreter will ever have).
    try:
        tree = ast.parse(cmd)
    except SyntaxError:
        # Unparseable. Deciding shell-vs-python here decides the DIAGNOSIS, so be positive
        # about shell rather than falling through to it: `assert [x for x in r assert x]`
        # matches any "looks like a program invocation" shape, and routing it to the shell
        # lane reports FAIL ("it ran and failed") for a snippet that never compiled. The
        # first token settles it -- a Python keyword means broken Python, full stop.
        # Caught by this script's own --self-test on its first run.
        first = cmd.split(maxsplit=1)[0] if cmd.split() else ""
        return "python" if first in PY_KEYWORDS else "shell"
    if any(
        isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.Assert))
        for n in ast.walk(tree)
    ):
        return "python"
    return "prose" if tree.body else "python"


def python_source(cmd: str) -> str:
    m = PY_DASH_C_RE.search(cmd)
    return m.group("body") if m else cmd


def run_python(line: int, cmd: str, interp: str, *, execute: bool = True) -> Result:
    src = python_source(cmd)
    try:
        compile(src, f"harness.md:{line}", "exec")
    except SyntaxError as exc:
        # The LM3 class: this command has never been executable, so the invariant it
        # claims to verify has never once been verified.
        return Result(line, "python", "SYNTAX", cmd, f"{exc.msg} (offset {exc.offset})")
    if not execute:
        return Result(line, "python", "SKIP", cmd, "compiles; not executed (classify-only)")
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    try:
        proc = subprocess.run(
            [interp, "-c", src],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return Result(line, "python", "TIMEOUT", cmd, f"exceeded {TIMEOUT_S}s")
    if proc.returncode == 0:
        return Result(line, "python", "PASS", cmd)
    tail = (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1]
    status = (
        "ASSERT"
        if tail.startswith("AssertionError")
        else (
            "STALE_REF"
            if tail.split(":")[0]
            in {"ImportError", "ModuleNotFoundError", "AttributeError", "NameError"}
            else "FAIL"
        )
    )
    return Result(line, "python", status, cmd, tail[:300])


SHELL_METACHARS = frozenset("|&;<>$`(){}[]*?!")


def safe_argv(cmd: str) -> list[str] | None:
    """Split a command for `subprocess` WITHOUT a shell, or None if it needs one.

    These strings come out of a markdown file. Passing them to `shell=True` makes every
    line of harness.md a shell injection site -- and this repo has already shipped one
    real RCE through exactly that reasoning ("it's only our own trusted input"), see the
    H5 / safe_exec allow-list finding. argv execution removes the shell entirely.

    A command that genuinely needs shell features (a pipe, `&&`, a glob) is SKIPPED with a
    reason rather than mangled by shlex into something that runs and means something else:
    a wrong verdict on a gate is worse than an absent one.
    """
    if SHELL_METACHARS & set(cmd):
        return None
    try:
        parts = shlex.split(cmd)
    except ValueError:  # unbalanced quotes
        return None
    return parts or None


EMPTY_EXPECTED_RE = re.compile(r"must (?:return|be)\s+empty|returns? empty|-> *empty", re.I)
MATCH_EXPECTED_RE = re.compile(r"non-empty|returns? a match|must (?:match|appear)", re.I)


def grep_expectation(body: str) -> bool | None:
    """Does this grep invariant want NO matches (True), matches (False), or unstated (None)?

    grep's exit code is a PREDICATE, not a pass/fail: S4 ("no hardcoded stealthskater.com
    URLs") passes when grep exits 1, while H3 ("returns a non-empty result") passes when it
    exits 0. Assuming exit 0 == pass inverts half of them. The expectation lives in the
    surrounding prose, so read it -- and when it is not stated, return None and SKIP rather
    than guess. A coin-flip verdict on a gate is worse than an honest abstention.
    """
    if EMPTY_EXPECTED_RE.search(body):
        return True
    if MATCH_EXPECTED_RE.search(body):
        return False
    return None


def run_grep(line: int, cmd: str, body: str) -> Result:
    expect_empty = grep_expectation(body)
    if expect_empty is None:
        return Result(line, "grep", "SKIP", cmd, "expected polarity not stated in prose")
    argv = safe_argv(cmd)
    if argv is None:
        return Result(line, "grep", "SKIP", cmd, "contains shell metacharacters; not run")
    proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, timeout=TIMEOUT_S)
    matched = proc.returncode == 0
    if matched is not expect_empty:  # matched=False & expect_empty=True -> pass
        return Result(line, "grep", "PASS", cmd)
    want = "no matches" if expect_empty else "at least one match"
    return Result(
        line,
        "grep",
        "FAIL",
        cmd,
        f"expected {want}; got {'matches' if matched else 'none'}",
    )


def run_shell(line: int, cmd: str, kind: Kind, interp: str) -> Result:
    argv = safe_argv(cmd.replace("python3 ", f"{interp} ").replace("python ", f"{interp} "))
    if argv is None:
        return Result(line, kind, "SKIP", cmd, "contains shell metacharacters; not run")
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    try:
        proc = subprocess.run(
            argv, cwd=REPO, env=env, capture_output=True, text=True, timeout=TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return Result(line, kind, "TIMEOUT", cmd, f"exceeded {TIMEOUT_S}s")
    if proc.returncode == 0:
        return Result(line, kind, "PASS", cmd)
    tail = (proc.stderr.strip() or proc.stdout.strip() or "(no output)").splitlines()[-1]
    return Result(line, kind, "FAIL", cmd, f"exit {proc.returncode}: {tail[:300]}")


def run_pytest(line: int, cmd: str, interp: str) -> Result:
    target = cmd if NODEID_RE.match(cmd) else None
    if target is None:
        m = re.search(r"pytest\s+((?:tests/[\w/.-]+\.py(?:::\w+)*\s*)+)", cmd)
        if not m:
            return Result(line, "pytest", "SKIP", cmd, "no resolvable test target")
        target = m.group(1).strip()
    argv = [
        interp,
        "-m",
        "pytest",
        *target.split(),
        "-q",
        "-p",
        "no:warnings",
        "--import-mode=append",
    ]
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    try:
        proc = subprocess.run(
            argv,
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S * 4,
        )
    except subprocess.TimeoutExpired:
        return Result(line, "pytest", "TIMEOUT", cmd, f"exceeded {TIMEOUT_S * 4}s")
    if proc.returncode == 0:
        return Result(line, "pytest", "PASS", cmd)
    tail = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    return Result(line, "pytest", "FAIL", cmd, tail[:300])


def audit(
    text: str,
    *,
    with_pytest: bool = False,
    interp: str | None = None,
    execute: bool = True,
) -> Report:
    """Classify every verification block, and (unless `execute=False`) run it.

    `execute=False` is the cheap pass and it is not merely a test-speed dodge: the two
    findings that need no interpreter at all -- UNPARSED (the extractor cannot read the
    block) and PROSE (a sentence typed in command position) -- are pure classification, and
    SYNTAX needs only `compile()`. Those are the highest-signal classes, because each means
    the invariant has never been verified even once. They answer in milliseconds; only
    ASSERT and STALE_REF need the subprocess.
    """
    interpreter, warning = (interp, "") if interp else find_interpreter()
    rep = Report(interpreter=interpreter, interpreter_warning=warning)
    for line, body in iter_blocks(text):
        cmd = extract(body)
        if cmd is None:
            # V1: extractor blindness must be LOUD. A parser that silently skips what it
            # cannot read makes every downstream check pass by construction.
            rep.results.append(
                Result(line, "unparsed", "UNPARSED", body[:120], "no command found in block")
            )
            continue
        kind = classify(cmd)
        if kind == "external":
            rep.results.append(
                Result(line, kind, "SKIP", cmd, "needs a live port or an external CLI")
            )
        elif kind == "prose":
            rep.results.append(
                Result(line, kind, "PROSE", cmd, "reads as a claim, not a runnable command")
            )
        elif kind == "python":
            # compile() is free and needs no environment, so SYNTAX is still detected in
            # the classify-only pass -- it is exactly the class that proves a verification
            # never ran, and it would be perverse to need a subprocess to notice that.
            rep.results.append(run_python(line, cmd, interpreter, execute=execute))
        elif not execute:
            rep.results.append(Result(line, kind, "SKIP", cmd, "classify-only pass"))
        elif kind == "grep":
            rep.results.append(run_grep(line, cmd, body))
        elif kind == "shell":
            rep.results.append(run_shell(line, cmd, kind, interpreter))
        elif kind == "pytest":
            rep.results.append(
                run_pytest(line, cmd, interpreter)
                if with_pytest
                else Result(line, kind, "SKIP", cmd, "pytest target (use --with-pytest)")
            )
    return rep


def render(rep: Report) -> int:
    by_status: dict[str, list[Result]] = {}
    for r in rep.results:
        by_status.setdefault(r.status, []).append(r)
    print(f"verification_exec: {len(rep.results)} blocks in {DOC.relative_to(REPO)}")
    print(f"  interpreter: {rep.interpreter}")
    if rep.interpreter_warning:
        print(f"  WARNING: {rep.interpreter_warning}")
    for status in sorted(by_status, key=lambda s: (s in {"PASS", "SKIP"}, s)):
        print(f"  {status:10} {len(by_status[status])}")
    hard = [r for r in rep.results if r.hard]
    if hard:
        print("\n=== NOT ACTUALLY VERIFIED ===")
        for r in sorted(hard, key=lambda r: r.line):
            print(f"harness.md:{r.line}  [{r.status}] {r.command[:110]}")
            if r.detail:
                print(f"    {r.detail}")
    return len(hard)


def self_test() -> int:
    """Prove each classification can go RED. A gate that cannot fail proves nothing."""
    interp, _ = find_interpreter()
    cases = [
        # (fixture doc, expected status, why this mutant matters)
        (
            "- **Verification**: `assert [x for x in range(3) assert x]`",
            "SYNTAX",
            "the LM3 class: a snippet that never compiled, so never verified anything",
        ),
        (
            "- **Verification**: `import sys; assert 1 == 2`",
            "ASSERT",
            "a live regression: the command runs and the invariant is false",
        ),
        (
            "- **Verification**: `from cohezion.nope_missing import Gone; assert Gone`",
            "STALE_REF",
            "the code moved and the doc did not",
        ),
        (
            "- **Verification**: `result.metrics['tier'] in {'npu'}`",
            "PROSE",
            "a sentence in command position",
        ),
        (
            "- **Verification**: covered elsewhere, see the section above",
            "UNPARSED",
            "V1: extractor blindness must be reported, never skipped",
        ),
        (
            "- **Verification**: `import sys; assert sys.version_info >= (3, 13)`",
            "PASS",
            "negative control: a real check must still pass",
        ),
        (
            "- **Verification**: `curl -s http://localhost:13305/v1/models`",
            "SKIP",
            "external dependency is skipped with a reason, never counted green",
        ),
        # Both of the following are regression pins for FALSE POSITIVES this gate produced
        # on its own first real run against harness.md. A scanner that invents findings is
        # worse than no scanner, so each self-inflicted bug gets a case here.
        (
            '- **Verification**: `uv run python -c "\nimport sys\nassert sys.version_info\n"`',
            "PASS",
            "multi-line python -c must keep its newlines, not collapse to SyntaxError",
        ),
        # Scoped to pyproject.toml, NOT scripts/: a fixture that greps the tree containing
        # the fixture FINDS ITSELF. The first draft searched scripts/ for a token spelled
        # out three lines above, in scripts/ci/verification_exec.py, and the probe matched
        # its own source -- inverting the expected exit code and failing a correct gate.
        (
            '- **Verification**: `grep "no_such_token_here" pyproject.toml` must return empty',
            "PASS",
            "grep polarity: 'must return empty' passes on exit 1, not exit 0",
        ),
        (
            '- **Verification**: `grep -l "cohezion" pyproject.toml` returns a non-empty result',
            "PASS",
            "the inverse polarity still passes on exit 0",
        ),
        (
            '- **Verification**: `grep -r "anything" pyproject.toml`',
            "SKIP",
            "unstated polarity abstains rather than guessing a verdict",
        ),
    ]
    failures = 0
    for doc, expected, why in cases:
        rep = audit(doc, interp=interp)
        got = rep.results[0].status if rep.results else "<none>"
        ok = got == expected
        failures += not ok
        print(f"  [{'ok' if ok else 'RED'}] expected {expected:9} got {got:9}  {why}")
    # The extractor's own negative test: a block it cannot read must not vanish.
    rep = audit("- **Verification**: covered elsewhere")
    if not rep.results:
        print("  [RED] an unparseable block produced NO result — extractor blindness")
        failures += 1
    print(f"\nself-test: {len(cases)} cases, {failures} failed")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--strict", action="store_true", help="exit 1 on any hard failure")
    ap.add_argument("--with-pytest", action="store_true", help="also execute pytest targets")
    ap.add_argument(
        "--classify-only",
        action="store_true",
        help="no subprocesses: still reports UNPARSED, PROSE and SYNTAX",
    )
    ap.add_argument("--json", type=Path, help="write machine-readable results here")
    ap.add_argument("--self-test", action="store_true", help="prove each class can go RED")
    args = ap.parse_args()

    if args.self_test:
        return 1 if self_test() else 0

    rep = audit(
        DOC.read_text(encoding="utf-8"),
        with_pytest=args.with_pytest,
        execute=not args.classify_only,
    )
    hard = render(rep)
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "interpreter": rep.interpreter,
                    "warning": rep.interpreter_warning,
                    "results": [asdict(r) for r in rep.results],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return 1 if (args.strict and hard) else 0


if __name__ == "__main__":
    raise SystemExit(main())
