#!/usr/bin/env python3
"""Measured branching ratio (sigma) per link of the autopoietic loop (stdlib only).

sigma_L = unique children at the next link attributable to parents at L / unique parents at L.
~0: activity dies at L; >1: fan-out/duplication. From logged artifacts only; an unreadable source
is UNKNOWN (never 0) and propagates; "n/a (0 parents)" = parent count MEASURED as 0. COHORT-FORWARD
attribution: parents = queue items created in the window; children counted by explicit id
reference whatever their own date (right-censored near the window end, so biased LOW).
  SENSE  unique work-queue ids with created_at >= cutoff (GET /api/work-queue)
  DECIDE unique (item_id, sha1(proposal)) in ada_proposals.jsonl + (item_id, task id) in
         compound_tasks.json with item_id in SENSE                               parent SENSE
  ACT    prose: compound tasks done+success from SENSE items (text produced)     parent DECIDE
         diff: unique SENSE ITEMS with >=1 `git log --all` commit naming the item id or the
         `Compound-Task: N` of a task from it (bare "task N" NOT matched: 283 human commits say
         it). Commit count reported separately as notes.act_diff_commits.
  LEARN  ACT(diff) items with a commit touching src/cohezion/skills/ or *_PRIME.md +
         prompt_version rows (all-time, unattributable: upper bound)          parent ACT(diff)
  CLOSE  ACT(diff) items with a commit that is an ancestor of origin/main     parent ACT(diff)
  RESCAN actioner journal sum(processed) / unique ids processed (the runaway signal).
event_log is NOT a loop source (git-post-commit + claude-code-session rows only); not queried.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


C = Path.home() / ".cohezion"
# the checkout whose git history is measured (the loop's), overridable via COHEZION_REPO
REPO = Path(os.environ.get("COHEZION_REPO", Path.home() / "dev/cohezion"))
WQ_URL, SURREAL = "http://localhost:8080/api/work-queue", "http://localhost:8001/sql"
HEX12 = re.compile(r"\b[0-9a-f]{12}\b")
TASKREF = re.compile(r"compound[-_ ]task\s*[:#]?\s*#?(\d+)", re.I)
KEYS = ["SENSE", "DECIDE", "ACT_prose", "ACT_diff", "LEARN", "CLOSE"]
LINKS = [("SENSE", "DECIDE"), ("DECIDE", "ACT_prose"), ("DECIDE", "ACT_diff"), ("ACT_diff", "LEARN"), ("ACT_diff", "CLOSE")]  # fmt: skip


class SourceUnknownError(Exception):
    """A source could not be read. Distinct from a measured zero."""


def _ts(v):
    t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")) if v else None
    return t.replace(tzinfo=t.tzinfo or dt.UTC) if t else None


def _read(label, fn):
    try:
        return fn()
    except Exception as e:
        raise SourceUnknownError(f"{label}: {e}") from e


def _run(cmd):
    p = _read(cmd[0], lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=600))
    if p.returncode != 0 or not p.stdout.strip():
        raise SourceUnknownError(f"{cmd[0]} rc={p.returncode}: {p.stderr.strip()[:120]}")
    return p.stdout


def read_prompt_versions():
    hdr = {"surreal-ns": "cohezion", "surreal-db": "main", "Accept": "application/json",
           "Authorization": "Basic " + base64.b64encode(b"root:root").decode()}  # fmt: skip
    q = b"SELECT count() AS n FROM prompt_version GROUP ALL;"
    req = urllib.request.Request(SURREAL, data=q, headers=hdr)
    res = _read("surrealdb", lambda: json.load(urllib.request.urlopen(req, timeout=15))[0])  # noqa: S310
    if res.get("status") != "OK":  # HTTP 200 can carry a statement error
        raise SourceUnknownError(f"surrealdb: {res.get('result')}")
    return int(res["result"][0]["n"]) if res["result"] else 0


def read_commits(repo=REPO):
    git = ["git", "-C", str(repo)]
    out = _run([*git, "log", "--all", "--name-only", "--format=\x1e%H\x1f%B\x1f"])
    main = set(_run([*git, "rev-list", "origin/main"]).split())
    commits = []
    for rec in out.split("\x1e")[1:]:
        sha, msg, files = [*rec.split("\x1f"), "", ""][:3]
        commits.append((sha, msg, [f for f in files.split("\n") if f.strip()]))
    return commits, main


def read_actioner_runs(days):
    cmd = ["journalctl", "--user", "-u", "cohezion-actioner", "--since", f"-{days}d"]
    raw = _run([*cmd, "--no-pager", "-o", "short-unix"])
    first = float(raw.split(None, 1)[0])
    body = re.sub(r"(?m)^\S+ \S+ [^:]+: ", "", raw)
    runs = []
    for m in re.finditer(r"(?ms)^\{$.*?^\}$", body):
        try:
            d = json.loads(m.group(0))
            ids = list(d.get("skipped_no_match", []))
            ids += [a["id"] if isinstance(a, dict) else a for a in d.get("actioned", [])]
            runs.append((int(d.get("processed", len(ids))), ids))
        except (json.JSONDecodeError, TypeError, KeyError, ValueError, AttributeError):
            pass
    return runs, round(min((dt.datetime.now().timestamp() - first) / 86400, days), 2)


def _file(name):
    text = (C / name).read_text()
    return json.loads(text) if name.endswith(".json") else [json.loads(x) for x in text.splitlines() if x.strip()]  # fmt: skip


# fmt: off
LIVE = {"queue": lambda: _read("work-queue", lambda: json.load(urllib.request.urlopen(WQ_URL, timeout=15))["items"]),
        "proposals": lambda: _read("ada_proposals", lambda: _file("ada_proposals.jsonl")),
        "tasks": lambda: _read("compound_tasks", lambda: _file("compound_tasks.json")),
        "prompt_versions": read_prompt_versions, "commits": read_commits, "runs": read_actioner_runs}
# fmt: on


def _get(src, name, *a):
    try:
        return src[name](*a), None
    except SourceUnknownError as e:
        return None, str(e)


def compute(src, days, now=None, dedup=True):  # dedup=False is the planted bug self-test catches
    cut, uniq = (now or dt.datetime.now(dt.UTC)) - dt.timedelta(days=days), (set if dedup else list)
    notes, n = {}, dict.fromkeys(KEYS)
    (q, e0), (props, e1), (tasks, e2), (cm, e3), (pv, e4) = (
        _get(src, k) for k in ("queue", "proposals", "tasks", "commits", "prompt_versions"))  # fmt: skip
    S = D = tasks_S = A = None
    if e0:
        notes["SENSE"] = e0
    else:
        S = {i["id"] for i in q if _ts(i.get("created_at")) and _ts(i["created_at"]) >= cut}
        notes["residual_no_created_at"] = sum(1 for i in q if not i.get("created_at"))
        n["SENSE"] = len(S)
    if S is None or e1 or e2:
        notes["DECIDE"] = e1 or e2 or "parent UNKNOWN"
    else:
        tasks_S = [t for t in tasks if t.get("source_item_id") in S]
        h = lambda s: hashlib.sha1(s.encode(), usedforsecurity=False).hexdigest()  # noqa: E731
        D = uniq([(p["item_id"], h(p.get("proposal", ""))) for p in props if p.get("item_id") in S]
                 + [(t["source_item_id"], f"task:{t['id']}") for t in tasks_S])  # fmt: skip
        notes["decided_items"], n["DECIDE"] = len({d[0] for d in D}), len(D)
        n["ACT_prose"] = len(uniq(t["id"] for t in tasks_S if t.get("done") and t.get("success")))
        notes["tasks_done_of_tasks"] = f"{n['ACT_prose']}/{len(tasks_S)}"  # sigma denom: +proposals
        notes["task_items"] = len({t["source_item_id"] for t in tasks_S})  # item-level  # fmt: skip
        notes["act_prose_items"] = len({t["source_item_id"] for t in tasks_S if t.get("done") and t.get("success")})  # fmt: skip
    if D is None or e3:
        notes["ACT_diff"] = e3 or "parent UNKNOWN"
    else:
        item_of_task = {str(t["id"]): t["source_item_id"] for t in tasks_S}
        # items a commit acts on: SENSE ids it names + source items of Compound-Task trailers
        its = lambda m: (set(HEX12.findall(m)) & S) | {item_of_task[t] for t in TASKREF.findall(m) if t in item_of_task}  # noqa: E731  # fmt: skip
        A = [(sha, f, its(msg)) for sha, msg, f in cm[0] if its(msg)]
        A = list({sha: (sha, f, i) for sha, f, i in A}.values()) if dedup else A
        # the contract is UNIQUE ITEMS: 2 commits for one item are one ACT child, not two
        items = lambda rows: len(uniq(i for *_x, ii in rows for i in sorted(ii)))  # noqa: E731
        n["ACT_diff"], notes["act_diff_commits"] = items(A), len(A)
        n["CLOSE"] = items([r for r in A if r[0] in cm[1]])
        notes["close_commits"] = sum(1 for r in A if r[0] in cm[1])
    if A is None or e4:
        notes["LEARN"] = e4 or "parent UNKNOWN"
    else:
        skill = [r for r in A if any("src/cohezion/skills/" in x or x.endswith("_PRIME.md") for x in r[1])]  # fmt: skip
        n["LEARN"], notes["prompt_version_rows_all_time"] = items(skill) + (pv if A else 0), pv
    runs, e5 = _get(src, "runs", days)
    rescan = {"status": f"UNKNOWN: {e5}"}
    if not e5:
        (rs, cov), part = runs, f"PARTIAL ({runs[1]}d of {days}d retained)"
        total, u = sum(p for p, _ in rs), len({i for _, ids in rs for i in ids})
        rescan = {"runs": len(rs), "processing_events": total, "unique_items": u,
                  "amplification": round(total / u, 1) if u else None, "coverage_days": cov,
                  "status": "OK" if cov >= days - 0.5 else part}  # fmt: skip
    sig = {f"{p}->{c}": "UNKNOWN" if n[p] is None or n[c] is None else "n/a (0 parents)" if n[p] == 0 else round(n[c] / n[p], 4) for p, c in LINKS}  # fmt: skip
    return {"window_days": days, "counts": n, "sigma": sig, "rescan": rescan, "notes": notes,
            "end_to_end_yield": n["CLOSE"] / n["SENSE"] if n["CLOSE"] is not None and n["SENSE"] else "UNKNOWN"}  # fmt: skip


# ---------------------------------------------------------------- self-test
def _fixture(dead_act=False, broken=None, fanout=False):
    now, h = dt.datetime(2026, 9, 21, tzinfo=dt.UTC), "{:012x}".format
    ago = lambda d: (now - dt.timedelta(days=d)).isoformat()  # noqa: E731
    q = [{"id": h(i), "created_at": ago(1)} for i in range(10)]
    q += [{"id": "a" * 12, "created_at": ago(40)}, {"id": "b" * 12}]  # out of window; undated
    # item 0 fans out to 2 DISTINCT proposals; item 1's single proposal was written 5x (dup rows)
    props = [{"item_id": h(0), "proposal": "x"}, {"item_id": h(0), "proposal": "y"}]
    props += [{"item_id": h(1), "proposal": "z"}] * 5 + [{"item_id": "a" * 12, "proposal": "o"}]
    if fanout:  # one item -> 3 distinct decisions, each logged 4x: sigma must be 3.0, not 12.0
        q = [{"id": "c" * 12, "created_at": ago(0)}]
        props = [{"item_id": "c" * 12, "proposal": p} for p in "pqr" * 4]
    tasks = [{"id": 7, "source_item_id": h(2), "done": True, "success": True},
             {"id": 8, "source_item_id": h(3), "done": True, "success": False}]  # fmt: skip
    c1 = ("c1", f"fix: item {h(0)}", ["src/cohezion/skills/X_PRIME.md"])
    commits = [] if dead_act else [c1, c1, ("c2", "feat: x\n\nCompound-Task: 7", ["a.py"]),
                                   ("c3", "docs: Task 7 of the plan", ["b.md"]),
                                   ("c4", f"fix: follow-up {h(0)}", ["c.py"])]  # same item as c1  # fmt: skip
    runs = ([(3, [h(i) for i in range(3)])] * 4, 1.0)
    src = {"queue": lambda: q, "proposals": lambda: props, "tasks": lambda: tasks,
           "prompt_versions": lambda: 0, "commits": lambda: (commits, {"c1"}),
           "runs": lambda _d: runs}  # fmt: skip
    if broken:  # an unreadable source: the reader raises
        src[broken] = lambda *_a: (_ for _ in ()).throw(SourceUnknownError("x"))
    return src, now


def self_test(dedup=True):
    now = _fixture()[1]
    run = lambda **kw: compute(_fixture(**kw)[0], 7, now, dedup)  # noqa: E731
    r, dead, noc = run(), run(dead_act=True), run(broken="commits")
    # fmt: off
    cases = [
        ("SENSE excludes 40d-old + undated", r["counts"]["SENSE"], 10),
        ("DECIDE dedups rows (x,y,z,task7,task8)", r["counts"]["DECIDE"], 5),
        ("sigma S->D", r["sigma"]["SENSE->DECIDE"], 0.5), ("decided items", r["notes"]["decided_items"], 4),
        ("ACT_prose", r["counts"]["ACT_prose"], 1), ("LEARN", r["counts"]["LEARN"], 1),
        ("ACT_diff items: c1+c4 same item once, c2 trailer, c3 ignored", r["counts"]["ACT_diff"], 2),
        ("act_diff_commits: c1 once, c4, c2", r["notes"]["act_diff_commits"], 3),
        ("CLOSE", r["counts"]["CLOSE"], 1), ("rescan amplification", r["rescan"]["amplification"], 4.0),
        ("duplicating link sigma > 1", run(fanout=True)["sigma"]["SENSE->DECIDE"], 3.0),
        ("dead link sigma == 0", dead["sigma"]["DECIDE->ACT_diff"], 0.0),
        ("downstream of dead link", dead["sigma"]["ACT_diff->CLOSE"], "n/a (0 parents)"),
        ("dead yield", dead["end_to_end_yield"], 0.0), ("UNKNOWN yield", noc["end_to_end_yield"], "UNKNOWN"),
        ("unreadable -> UNKNOWN", noc["sigma"]["DECIDE->ACT_diff"], "UNKNOWN"),
        ("UNKNOWN propagates", noc["sigma"]["ACT_diff->CLOSE"], "UNKNOWN"),
        ("known link unaffected", noc["sigma"]["SENSE->DECIDE"], 0.5),
        ("UNKNOWN != 0", run(broken="queue")["counts"]["SENSE"], None),
        ("rescan UNKNOWN", run(broken="runs")["rescan"]["status"], "UNKNOWN: x"),
    ]
    # fmt: on
    fails = [f"{lbl}: got {g!r} want {w!r}" for lbl, g, w in cases if g != w]
    print("SELF-TEST", "PASS" if not fails else "FAIL", *fails, sep="\n  ")
    return not fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--mutant-raw-counts", action="store_true", help="planted bug: self-test must FAIL")  # fmt: skip
    a = ap.parse_args()
    if a.self_test:
        return 0 if self_test(dedup=not a.mutant_raw_counts) else 1
    r = compute(LIVE, a.window_days)
    rows = [*r["counts"].items(), *(("sigma " + k, v) for k, v in r["sigma"].items())]
    rows += [(k, r[k]) for k in ("end_to_end_yield", "rescan", "notes")]
    text = "\n".join(f"  {k:24} {'UNKNOWN' if v is None else v}" for k, v in rows)
    print(json.dumps(r, indent=2, default=str) if a.json else f"window={a.window_days}d\n{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
