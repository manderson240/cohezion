#!/usr/bin/env python3
"""Environment pre-flight readiness gate for an AI coding session on the local AMD box.

Deterministic, zero-LLM, stdlib-only. Checks the failure classes that repeatedly
caused total Bash outages, OOM stalls, and blocked commits (see /insights friction
analysis 2026-07-12, kanban c19163c63eb7):

  1. bwrap mount points    .claude/commands & .claude/agents exist  -> else EROFS Bash outage
  2. cwd-under-.claude      session cwd not under a .claude/ dir      -> else .gitconfig EROFS
  3. memory headroom        MemAvailable > 20GB (N3 OOM guard)
  4. lemonade router        :13305 reachable + models served         -> local inference alive
  5. SurrealDB              :8001 reachable                          -> persistence (soft)
  6. leaked ro mount        .git/worktrees not a leaked ro bind      -> else git worktree add fails

Exit 0 when no BLOCK-level issue; exit 1 if any BLOCK. WARN/OK never fail.
Usage: python3 env_preflight.py [--repo PATH] [--json]
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import urllib.request
from pathlib import Path

REPO_DEFAULT = Path(__file__).resolve().parents[2]
BLOCK, WARN, OK = "BLOCK", "WARN", "OK"


def _mem_available_gb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    return -1.0


def _http_ok(url: str, headers: dict | None = None, data: bytes | None = None, timeout: int = 5) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, data=data, headers=headers or {})  # noqa: S310 localhost
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return r.status == 200, r.read(100_000).decode(errors="ignore")
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:80]


def checks(repo: Path) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []

    # 1. bwrap mount points
    missing = [d for d in ("commands", "agents") if not (repo / ".claude" / d).is_dir()]
    out.append((
        "bwrap-mounts", BLOCK if missing else OK,
        f"missing .claude/{{{','.join(missing)}}} - create <dir>/.keep (Write tool)" if missing
        else ".claude/commands & agents present",
    ))

    # 2. cwd under .claude/
    under = ".claude" in Path.cwd().resolve().parts
    out.append((
        "cwd-not-under-.claude", BLOCK if under else OK,
        f"cwd under .claude/ ({Path.cwd()}) - relaunch from a dir NOT under .claude/" if under
        else "cwd is safe",
    ))

    # 3. memory headroom
    mem = _mem_available_gb()
    lvl = BLOCK if 0 <= mem < 20 else (WARN if mem < 30 else OK)
    out.append(("memory-headroom", lvl, f"MemAvailable={mem:.1f}GB (need >20 for local inference; N3)"))

    # 4. lemonade :13305
    ok, detail = _http_ok("http://localhost:13305/api/v1/models")
    served = 0
    if ok:
        try:
            served = len(json.loads(detail if detail.strip().startswith("{") else "{}").get("data", []))
        except Exception:  # noqa: BLE001
            served = -1
    out.append(("lemonade-:13305", OK if ok else BLOCK,
                f"{served} models served" if ok else f"unreachable: {detail}"))

    # 5. SurrealDB :8001 (soft)
    auth = "Basic " + base64.b64encode(b"root:root").decode()
    ok, detail = _http_ok(
        "http://localhost:8001/sql",
        headers={"surreal-ns": "cohezion", "surreal-db": "main", "Content-Type": "text/plain", "Authorization": auth},
        data=b"INFO FOR DB;",
    )
    out.append(("surrealdb-:8001", OK if ok else WARN, "reachable" if ok else f"down (persistence degrades): {detail}"))

    # 6. leaked ro mount on .git/worktrees
    wt = repo / ".git" / "worktrees"
    try:
        opts = subprocess.run(["findmnt", "-T", str(wt), "-no", "OPTIONS"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
        leaked = opts.startswith("ro") or ",ro," in f",{opts}," or opts == "ro"
        out.append(("worktrees-writable", WARN if leaked else OK,
                    "LEAKED ro bind - `sudo umount .git/worktrees` (real terminal); git worktree add will fail"
                    if leaked else "not ro-leaked"))
    except (FileNotFoundError, subprocess.SubprocessError):
        out.append(("worktrees-writable", OK, "findmnt unavailable - skipped"))

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Environment pre-flight readiness gate")
    ap.add_argument("--repo", type=Path, default=REPO_DEFAULT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = checks(args.repo.resolve())
    blocks = [r for r in results if r[1] == BLOCK]

    if args.json:
        print(json.dumps({"ok": not blocks, "checks": [{"name": n, "level": lvl, "detail": d} for n, lvl, d in results]}))
    else:
        icon = {OK: "✓", WARN: "⚠", BLOCK: "✗"}
        print("=== env pre-flight ===")
        for name, lvl, detail in results:
            print(f"  {icon[lvl]} [{lvl:5}] {name:24} {detail}")
        print(f"\n{'BLOCKED' if blocks else 'READY'} - {len(blocks)} blocker(s), "
              f"{sum(1 for r in results if r[1] == WARN)} warning(s)")
    return 1 if blocks else 0


if __name__ == "__main__":
    raise SystemExit(main())
