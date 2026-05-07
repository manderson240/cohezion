#!/usr/bin/env python3
"""Poll open merge/* PRs, re-merge dirty ones, re-enable auto-merge.

Handles the serial merge cascade: when PR N auto-merges to main, the remaining
PRs go CONFLICTING. This script detects DIRTY state and re-runs merge_branch.py
only on the affected PRs, then force-pushes and re-enables auto-merge.

Usage:
    uv run python scripts/ci/cascade_watcher.py [--once]
    # --once: single poll cycle (for testing or ScheduleWakeup integration)
"""

import subprocess, sys, json, time, argparse

REPO = "/home/mike-anderson/dev/cohezion"
LOG = f"{REPO}/autoresearch-prs.jsonl"
SLEEP_S = 90  # poll every 90s (CI cycles are 3-5 min, cache stays warm at <270s)

# Map: PR head branch → source branch
BRANCH_MAP = {
    "merge/context-graceful-load": "polish/context-graceful-load",
    "merge/design-artifacts": "polish/design-artifacts",
    "merge/meta": "polish/meta",
    "merge/research-deep-think": "polish/research-deep-think",
    "merge/sigma-lint-bulk": "polish/sigma-lint-bulk",
    "merge/sigma-mypy-deepfix": "polish/sigma-mypy-deepfix",
    "merge/sigma-orphan-cleanup-v2": "polish/sigma-orphan-cleanup-v2",
    "merge/sigma-tests": "polish/sigma-tests",
    "merge/tests": "polish/tests",
    "merge/zeta-executor-source-bugs": "polish/zeta-executor-source-bugs",
    "merge/zeta-zero-coverage-tests": "polish/zeta-zero-coverage-tests",
}


def gh(*args):
    r = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    return r.stdout.strip()


def git_update_ref(branch, commit):
    subprocess.run(["git", "-C", REPO, "update-ref", f"refs/heads/{branch}", commit], check=True)


def force_push(branch):
    r = subprocess.run(
        ["git", "-C", REPO, "push", "--force-with-lease", "origin", branch],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0, r.stderr.strip()


def get_open_prs():
    raw = gh(
        "pr",
        "list",
        "--repo",
        "manderson240/cohezion",
        "--state",
        "open",
        "--json",
        "number,headRefName,mergeable,mergeStateStatus,autoMergeRequest",
    )
    if not raw:
        return []
    return json.loads(raw)


def remerge_branch(src_branch, pr_branch):
    r = subprocess.run(
        [sys.executable, f"{REPO}/scripts/ci/merge_branch.py", src_branch],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    lines = r.stdout.splitlines()
    commit_line = next((l for l in lines if l.strip().startswith("Commit:")), None)
    if not commit_line:
        return None, 0
    commit = commit_line.split()[-1]
    conf_line = next((l for l in lines if "Resolved" in l and "/" in l), "")
    conflicts = int(conf_line.split("/")[0].split()[-1]) if conf_line else 0
    return commit, conflicts


def log_entry(**kwargs):
    kwargs["timestamp"] = int(time.time() * 1000)
    with open(LOG, "a") as f:
        f.write(json.dumps(kwargs) + "\n")


def run_cycle():
    # Fetch latest main
    subprocess.run(["git", "-C", REPO, "fetch", "origin", "--quiet"], check=False)

    prs = get_open_prs()
    merge_prs = [p for p in prs if p["headRefName"] in BRANCH_MAP]

    if not merge_prs:
        print(f"[{ts()}] No open merge/* PRs — cascade complete!")
        return False  # signal done

    dirty = [p for p in merge_prs if p["mergeStateStatus"] == "DIRTY"]
    clean = [p for p in merge_prs if p["mergeStateStatus"] != "DIRTY"]

    print(f"[{ts()}] Open: {len(merge_prs)} | Dirty: {len(dirty)} | Clean: {len(clean)}")

    if not dirty:
        print("  All clean — waiting for CI/auto-merge...")
        return True

    for p in dirty:
        pr_branch = p["headRefName"]
        src_branch = BRANCH_MAP[pr_branch]
        print(f"  Re-merging #{p['number']} {pr_branch}...")

        commit, conflicts = remerge_branch(src_branch, pr_branch)
        if not commit:
            print("    ❌ No commit produced")
            log_entry(
                pr=p["number"], branch=src_branch, pr_branch=pr_branch, status="remerge_failed"
            )
            continue

        git_update_ref(pr_branch, commit)
        ok, err = force_push(pr_branch)
        if not ok:
            print(f"    ❌ Push failed: {err}")
            log_entry(
                pr=p["number"],
                branch=src_branch,
                pr_branch=pr_branch,
                commit=commit,
                status="push_failed",
                error=err,
            )
            continue

        print(f"    ✅ Pushed {commit[:12]} ({conflicts} conflicts resolved)")
        log_entry(
            pr=p["number"],
            branch=src_branch,
            pr_branch=pr_branch,
            commit=commit,
            conflicts_resolved=conflicts,
            status="cascade_rebased",
        )

        # Re-enable auto-merge if lost after force-push
        if not p.get("autoMergeRequest"):
            gh(
                "pr",
                "merge",
                str(p["number"]),
                "--repo",
                "manderson240/cohezion",
                "--auto",
                "--squash",
                "--delete-branch",
            )
            print(f"    🔁 Re-enabled auto-merge on #{p['number']}")

    return True


def ts():
    return time.strftime("%H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="Single poll cycle")
    args = ap.parse_args()

    print(f"Cascade watcher started. Polling every {SLEEP_S}s.")
    while True:
        try:
            still_running = run_cycle()
        except Exception as e:
            print(f"[{ts()}] Error: {e}")
            still_running = True

        if args.once or not still_running:
            break
        print(f"  Sleeping {SLEEP_S}s...")
        time.sleep(SLEEP_S)

    print("Done.")


if __name__ == "__main__":
    main()
