#!/usr/bin/env python3
"""Research-hygiene linter — makes an unverifiable claim FAIL rather than merely exist.

Implements the recommendations of the 2026-08-11 corpus audit
(vault/reports/20260811-research-corpus-audit.md), which measured, over 1,705 research
documents:

    218 assert a negative; 144 of them (66%) show NO evidence the instrument could have
        found what they report as absent
  1,436 (84%) have no limits/caveats section
    256 have quoted YAML dates that mis-bucket in any date query; 276 have none

WHY THIS IS WORTH A TOOL. The failure it targets is not carelessness, it is
indistinguishability: a proven negative and an unproven one read identically. On the day of
the audit, three live instruments returned empty for mechanical reasons — an arXiv HTTP 429,
a rate-limited GitHub query, and a DOI regex that captured URL fragments — and each would
have entered the corpus as a permanent "not found" if a control had not fired.

DESIGN NOTES, both learned the hard way on the same day:

  * This linter counts DISTINCT claims, not occurrences. The audit's first version ranked a
    file top-of-list for 11 "negatives" that turned out to be ONE claim quoted eight times
    inside an adversarial self-review that was interrogating whether it held -- good hygiene
    scored as bad. Lines that are quotations (leading '>' or wrapped in quotes) are excluded.

  * Every check is keyword-based and therefore a PROXY. A document can state its limits
    without using any word this searches for. Findings are ADVISORY by default; --strict
    turns them into a non-zero exit for CI. It is deliberately not fail-closed out of the
    box: a linter that blocks honest work gets disabled, and then it checks nothing.

Read-only unless --fix-dates is passed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# A claim that something is ABSENT. These are the statements that need an instrument.
NEGATIVE = re.compile(
    r"\b(?:not found|no evidence|does not exist|doesn'?t exist|none found|no results|"
    r"nothing found|no such|could not find|couldn'?t find|zero (?:hits|results|occurrences|"
    r"matches)|no (?:hits|matches|occurrences))\b",
    re.I,
)
# Evidence that the instrument was shown to work before its silence was believed.
CONTROL = re.compile(
    r"\b(?:control quer\w+|positive control|negative control|phase[- ]0|control fires|"
    r"control (?:passes|passed|failed|ok)|calibrat\w+|known[- ]good|must return|"
    r"sanity[- ]check|verified the (?:probe|instrument)|instrument (?:works|verified))\b",
    re.I,
)
LIMITS_HEADING = re.compile(
    r"^#{1,6}\s*.*\b(?:limit|caveat|what (?:i|we) did not|did not check|not verified|"
    r"honest limits|uncertain|unverified|scope|blind spot|out of scope)\w*",
    re.I | re.M,
)
FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
DATE_LINE = re.compile(r"^(date|updated|discovered):\s*(.+?)\s*$", re.I | re.M)
GOOD_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Finding:
    path: str
    rule: str
    detail: str


@dataclass
class Report:
    files: int = 0
    findings: list[Finding] = field(default_factory=list)

    def add(self, path: str, rule: str, detail: str) -> None:
        self.findings.append(Finding(path, rule, detail))


def _is_quotation(line: str) -> bool:
    """Quoted text is someone ELSE's claim; it must not be scored as this document's."""
    s = line.strip()
    return s.startswith(">") or (s.startswith(('"', "*\"", "- \"", "'")) and len(s) > 2)


def distinct_negatives(text: str) -> set[str]:
    """Distinct negative claims, excluding quotations and code blocks."""
    out: set[str] = set()
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or _is_quotation(line):
            continue
        for m in NEGATIVE.findall(line):
            out.add(m.lower())
    return out


def check_file(p: Path, root: Path) -> list[Finding]:
    rel = str(p.relative_to(root))
    try:
        text = p.read_text(errors="replace")
    except Exception as exc:  # noqa: BLE001
        return [Finding(rel, "unreadable", str(exc))]
    if len(text) < 400:
        return []  # stubs and pointers are not research documents

    found: list[Finding] = []

    negs = distinct_negatives(text)
    if negs and not CONTROL.search(text):
        found.append(
            Finding(
                rel,
                "unproven-negative",
                f"{len(negs)} distinct negative claim(s) {sorted(negs)[:3]} with no control-query "
                "evidence that the instrument could have found it",
            )
        )

    if not LIMITS_HEADING.search(text):
        found.append(
            Finding(rel, "no-limits-section", f"{len(text)} chars, no limits/caveats heading")
        )

    m = FM.match(text)
    if not m:
        found.append(Finding(rel, "no-frontmatter", "research document without frontmatter"))
    else:
        body = m.group(1)
        dates = DATE_LINE.findall(body)
        if not dates:
            found.append(Finding(rel, "no-date", "frontmatter has no date field"))
        for key, val in dates:
            raw = val.strip()
            if raw.startswith(("'", '"')):
                found.append(
                    Finding(rel, "quoted-date", f"{key}: {raw} — quoted dates mis-bucket in queries")
                )
            elif not GOOD_DATE.match(raw):
                found.append(Finding(rel, "malformed-date", f"{key}: {raw} — expected YYYY-MM-DD"))
    return found


def fix_dates(p: Path) -> bool:
    """Strip surrounding quotes from frontmatter date values. Returns True if changed."""
    text = p.read_text(errors="replace")
    m = FM.match(text)
    if not m:
        return False
    body = m.group(1)

    def _unquote(mm: re.Match) -> str:
        key, val = mm.group(1), mm.group(2).strip()
        if len(val) > 1 and val[0] == val[-1] and val[0] in "\"'":
            inner = val[1:-1]
            if GOOD_DATE.match(inner):
                return f"{key}: {inner}"
        return mm.group(0)

    new_body = DATE_LINE.sub(_unquote, body)
    if new_body == body:
        return False
    p.write_text(text.replace(body, new_body, 1))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", help="files or directories (default: vault research dirs)")
    ap.add_argument("--strict", action="store_true", help="exit non-zero when findings exist")
    ap.add_argument("--rule", action="append", help="only report these rules")
    ap.add_argument("--fix-dates", action="store_true", help="unquote frontmatter dates IN PLACE")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--limit", type=int, default=25, help="max findings printed per rule")
    args = ap.parse_args()

    vault = Path.home() / "vaults" / "cohezion-vault"
    if args.paths:
        targets = [Path(p) for p in args.paths]
        root = Path.cwd()
    else:
        targets = [vault / d for d in ("reports", "research", "reviews", "decisions", "handoffs")]
        root = vault

    files: list[Path] = []
    for t in targets:
        if t.is_dir():
            files.extend(sorted(t.rglob("*.md")))
        elif t.is_file():
            files.append(t)

    rep = Report(files=len(files))
    for f in files:
        try:
            rel_root = root if str(f).startswith(str(root)) else f.parent
            rep.findings.extend(check_file(f, rel_root))
        except ValueError:
            rep.findings.extend(check_file(f, f.parent))

    if args.rule:
        rep.findings = [x for x in rep.findings if x.rule in args.rule]

    if args.fix_dates:
        changed = 0
        for f in files:
            try:
                if fix_dates(f):
                    changed += 1
            except Exception:  # noqa: BLE001
                pass
        print(f"unquoted frontmatter dates in {changed} file(s)")

    if args.json:
        print(json.dumps({"files": rep.files,
                          "findings": [x.__dict__ for x in rep.findings]}, indent=1))
    else:
        by_rule: dict[str, list[Finding]] = {}
        for x in rep.findings:
            by_rule.setdefault(x.rule, []).append(x)
        print(f"research-hygiene: {rep.files} file(s) checked, {len(rep.findings)} finding(s)")
        for rule in sorted(by_rule, key=lambda r: -len(by_rule[r])):
            items = by_rule[rule]
            print(f"\n  {rule}  ({len(items)})")
            for x in items[: args.limit]:
                print(f"    {x.path[:70]}\n        {x.detail[:110]}")
            if len(items) > args.limit:
                print(f"    ... and {len(items) - args.limit} more")
        print(
            "\nADVISORY by default. These are keyword PROXIES: a document may state its limits "
            "without using a word this searches for. Use --strict in CI once the backlog is "
            "triaged — a linter that blocks honest work gets disabled, and then it checks nothing."
        )

    return 1 if (args.strict and rep.findings) else 0


if __name__ == "__main__":
    sys.exit(main())
