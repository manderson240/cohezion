"""Durable output for expensive local-inference runs.

WHY THIS EXISTS (2026-08-16, after losing ~30 lanes of local inference):
`$TMPDIR` is `/tmp/claude-1000`, and `/tmp` on this box is **tmpfs** — RAM-backed. A reboot
destroys it with certainty, so writing swarm results there is not a risk, it is a guarantee of
loss on any OOM/crash/reboot. Measured that day: 8 of 9 swarm result files were destroyed by a
single reboot; the only survivor was written afterwards. `~/vaults`, `~/.cohezion` and `.git`
are ZFS, and everything written there survived — including a commit whose branch was later
deleted.

TWO failure modes, and durable storage alone only fixes the first:

1. **Wrong filesystem.** Results on tmpfs die with the machine. Fixed by writing under
   ``~/vaults/cohezion-vault/swarm-runs/`` (ZFS, already the established convention).

2. **Write-at-the-end.** The lost runs serialised their JSON once, after every lane finished.
   A crash during the last lane therefore destroyed the completed lanes too. Fixed by
   ``record_lane()`` — each lane is persisted the moment it returns, so a crash costs only the
   in-flight lane rather than the whole run.

Writes are atomic (tmp file in the same directory + ``os.replace``) so a crash mid-write leaves
the previous good file rather than a truncated one.

Usage::

    run = DurableRun("go-article-review")
    for result in completed_lanes:
        run.record_lane(result)          # persisted immediately
    run.finalize({"speedup": 2.31})      # summary + index entry
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


# ZFS, not tmpfs. The whole point of this module.
DURABLE_ROOT = Path.home() / "vaults" / "cohezion-vault" / "swarm-runs"


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON so a crash mid-write cannot corrupt an existing good file.

    The temp file must live in the SAME directory as the target: os.replace is only atomic
    within a filesystem, and /tmp is a different (and volatile) one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp, "w") as fh:
        json.dump(payload, fh, indent=2, default=str)
        fh.flush()
        os.fsync(fh.fileno())  # survive a power/OOM event, not just a process exit
    os.replace(tmp, path)
    # fsync the file alone is NOT enough: os.replace makes the CONTENT durable but the
    # directory ENTRY naming it is separate metadata. Without this the file can exist on disk
    # yet be unreachable after a crash. ZFS's transactional CoW makes that unlikely in
    # practice, but the fix is two syscalls and is correct on any filesystem.
    # (Raised by an adversarial review lane against this very function, 2026-08-16.)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    except OSError:
        pass  # some filesystems reject directory fsync; the replace itself still stands
    finally:
        os.close(dir_fd)


def _stamp_to_epoch(stamp: str) -> float:
    """Parse a ``%Y%m%d-%H%M%S`` run stamp back to epoch so elapsed_s spans the WHOLE run,
    not just the process that happened to finalize it. Falls back to now on a malformed stamp."""
    try:
        return time.mktime(time.strptime(stamp, "%Y%m%d-%H%M%S"))
    except (ValueError, TypeError):
        return time.time()


def _load_lanes(d: Path) -> list[dict]:
    """Rebuild the in-memory lane list from disk, in filename order (lane-NN-*)."""
    lanes: list[dict] = []
    for p in sorted(d.glob("lane-*.json")):
        try:
            lanes.append(json.loads(p.read_text()))
        except (OSError, json.JSONDecodeError):
            lanes.append({"lane": p.stem, "rejected": "unreadable-on-reattach"})
    return lanes


class DurableRun:
    """A swarm run whose artifacts land on durable storage as they are produced."""

    def __init__(
        self,
        slug: str,
        *,
        session: str = "",
        meta: dict | None = None,
        run_dir: str | Path | None = None,
    ) -> None:
        """Start a new run, or REATTACH to an existing one via ``run_dir``.

        Reattach exists because a workflow spread over several *processes* (an agent shelling
        out to python repeatedly) otherwise mints a fresh timestamped directory per call, so
        N lanes land in N one-lane directories and ``finalize()`` only ever sees the last one.
        Measured 2026-08-19: a 6-lane run produced 6 directories.

        When reattaching, existing ``lane-*.json`` files are loaded so lane numbering continues
        instead of overwriting, and ``finalize()`` reports the whole run rather than this slice.
        """
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug)[:60]
        self.slug = safe
        self._lanes: list[dict] = []

        if run_dir is not None:
            self.dir = Path(run_dir)
            if not self.dir.is_dir():
                raise FileNotFoundError(f"run_dir does not exist: {self.dir}")
            existing = (
                json.loads((self.dir / "run.json").read_text())
                if (self.dir / "run.json").exists()
                else {}
            )
            stamp = existing.get("started_utc") or time.strftime("%Y%m%d-%H%M%S")
            self._lanes = _load_lanes(self.dir)
            self.started = _stamp_to_epoch(stamp)
            # Re-open the run: a previously finalized run becomes in_progress again, and the
            # original session/meta are preserved unless the caller supplies new ones.
            _atomic_write_json(
                self.dir / "run.json",
                {
                    "slug": existing.get("slug", safe),
                    "session": session or existing.get("session", ""),
                    "started_utc": stamp,
                    "status": "in_progress",
                    "meta": meta or existing.get("meta", {}),
                    "reattached": True,
                },
            )
            return

        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.dir = DURABLE_ROOT / f"{stamp}-{safe}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.started = time.time()
        _atomic_write_json(
            self.dir / "run.json",
            {
                "slug": safe,
                "session": session,
                "started_utc": stamp,
                "status": "in_progress",
                "meta": meta or {},
            },
        )

    @classmethod
    def attach(cls, slug: str, *, create: bool = True, **kw) -> DurableRun:
        """Reattach to the most recent run for ``slug``, or start one if none exists.

        This is the form a multi-process caller actually needs: separate invocations know the
        slug but not the timestamped directory, so they cannot pass ``run_dir`` themselves.
        """
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug)[:60]
        if DURABLE_ROOT.exists():
            matches = sorted(
                d for d in DURABLE_ROOT.iterdir() if d.is_dir() and d.name.endswith(f"-{safe}")
            )
            if matches:
                return cls(slug, run_dir=matches[-1], **kw)
        if not create:
            raise FileNotFoundError(f"no existing run for slug {safe!r}")
        return cls(slug, **kw)

    def record_lane(self, result: dict) -> Path:
        """Persist ONE lane immediately. Call as each lane returns, never in a final batch."""
        self._lanes.append(result)
        name = str(result.get("lane") or f"lane{len(self._lanes)}")
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)[:50]
        path = self.dir / f"lane-{len(self._lanes):02d}-{safe}.json"
        _atomic_write_json(path, result)
        return path

    def finalize(self, summary: dict | None = None) -> Path:
        """Write the run summary. Safe to skip — lanes are already durable without it."""
        payload = {
            "slug": self.slug,
            "elapsed_s": round(time.time() - self.started, 1),
            "lanes": len(self._lanes),
            "usable": sum(1 for r in self._lanes if not r.get("rejected")),
            "status": "complete",
            "summary": summary or {},
            "dev": self._lanes,
        }
        path = self.dir / "run.json"
        _atomic_write_json(path, payload)
        return path


def recover_incomplete() -> list[dict]:
    """List runs that never finalised — i.e. were interrupted by a crash or OOM.

    Their per-lane files are still on disk and readable; this is what makes an interrupted
    run recoverable instead of a total loss.
    """
    out: list[dict] = []
    if not DURABLE_ROOT.exists():
        return out
    for d in sorted(DURABLE_ROOT.iterdir()):
        meta = d / "run.json"
        if not (d.is_dir() and meta.exists()):
            continue
        try:
            data = json.loads(meta.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("status") != "complete":
            lanes = sorted(d.glob("lane-*.json"))
            out.append(
                {
                    "dir": str(d),
                    "slug": data.get("slug"),
                    "lanes_salvaged": len(lanes),
                    "started_utc": data.get("started_utc"),
                }
            )
    return out
