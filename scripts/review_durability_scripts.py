"""Live end-to-end check of swarm_harness durability, using it to review its own siblings.

Dogfooding on purpose: it proves the harness works under real inference AND produces a genuine
review of the two new durability scripts. Uses only the currently-FREE devices (gpu, cpu) so it
does not contend with another session's NPU work.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swarm_harness import run_swarm  # noqa: E402

FMT = """
After ===FINAL=== write exactly these two labelled lines, then at most four bullets:
FINDING: <one sentence - the single most important flaw, or "no blocking flaw">
CONFIDENCE: <high|medium|low> - <the specific thing that would change it>
- <up to four concrete bullets>
"""

CONTEXT = """\
Two new scripts were written to stop losing expensive local-inference results to OOM/reboot.

MEASURED PROBLEM: $TMPDIR is /tmp/claude-1000 and /tmp on this machine is tmpfs (RAM-backed,
64GB). A reboot destroyed 8 of 9 swarm result files. Everything on ZFS (~/vaults, .git objects,
SurrealDB) survived, including a commit whose branch was later deleted. A SECOND failure was
independent of storage: the swarms serialised their JSON once at the END, so a crash during the
last lane also destroyed the already-completed lanes.

SCRIPT 1 - durable_swarm_output.py. class DurableRun writes under
~/vaults/cohezion-vault/swarm-runs/<timestamp>-<slug>/ (ZFS). record_lane() persists ONE lane
per file the moment it returns. Writes are atomic: json.dump to a temp file in the SAME
directory, fh.flush(), os.fsync(fd), then os.replace(). finalize() writes a run.json summary
with status 'complete'. recover_incomplete() lists run dirs whose run.json status is not
'complete' and counts their salvageable lane-*.json files.

SCRIPT 2 - snapshot_worktree.sh. Snapshots a worktree's UNCOMMITTED work to refs/snapshots/<name>
without touching the worktree's index. Stages into a TEMP index (GIT_INDEX_FILE) because the two
cases where a snapshot matters most are exactly the two where `git add` fails: a read-only
.git/worktrees mount, and a session pinned to a worktree. Uses git hash-object -w --path (so
.gitattributes filters apply), git update-index --cacheinfo, git write-tree, git commit-tree,
git update-ref. Includes tracked-modified plus untracked-not-ignored files; skips deletions;
chains onto the previous snapshot as a second parent so the ref keeps history.
"""

LANES = [
    {
        "name": "durability_holes",
        "device": "gpu",
        "model": "Gemma-4-E4B-it-GGUF",
        "prompt": CONTEXT
        + """
QUESTION: Attack SCRIPT 1's durability claim. Under what concrete failure does it STILL lose
data? Consider specifically: what happens if the machine dies BETWEEN os.replace() of a lane
file and the next lane completing; whether fsync on the file alone is sufficient without also
fsyncing the parent DIRECTORY entry; and whether ZFS changes that answer. Also: is writing one
file per lane a problem at high lane counts? Be concrete about what is still lost."""
        + FMT,
    },
    {
        "name": "snapshot_correctness",
        "device": "cpu",
        "model": "Gemma-4-E2B-it-GGUF",
        "prompt": CONTEXT
        + """
QUESTION: Attack SCRIPT 2's correctness. It snapshots tracked-modified plus
untracked-not-ignored files and SKIPS deletions on the grounds that HEAD already holds the prior
content. Is that reasoning sound - can a snapshot that omits deletions ever mislead someone
recovering from it? Also assess: hardcoding file mode 100644 (what about executable files or
symlinks?), and chaining each snapshot onto the previous one as a second parent (does that ref
grow without bound?)."""
        + FMT,
    },
]


async def main() -> None:
    await run_swarm(
        LANES,
        "review-durability-scripts",
        fields=("FINDING:", "CONFIDENCE:"),
        max_tokens=4000,
        session="s-fd4fad2d23a1",
    )


if __name__ == "__main__":
    asyncio.run(main())
