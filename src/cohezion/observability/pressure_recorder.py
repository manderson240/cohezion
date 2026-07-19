"""Continuous memory/pressure recorder — makes the NEXT freeze diagnosable.

WHY THIS EXISTS (2026-07-18): the box stopped hard at 20:09:41. Post-hoc forensics found
NOTHING attributable: no `Out of memory: Killed process`, no amdgpu MES/ring-timeout, no
shutdown sequence. The last kernel message was 21 minutes earlier and benign.

That is not a gap in the investigation -- it is the defining property of this failure
class. A hard freeze is self-erasing: the machinery that would record the cause is taken
down by the same event. journald persistence was already enabled; the problem is that
nothing was WRITTEN in the window. Reading logs after the fact can never diagnose this.

So: sample continuously and fsync every line. The last durable line before a freeze is the
evidence that did not exist this time. Cheap enough to leave running (a few hundred bytes
per sample), and it holds no locks anything else needs.

Reads /proc directly, with no third-party imports, so a dependency problem can never be
the reason sampling stopped. (cohezion.mass_sim.system_monitor.get_vitals() covers
similar ground but pulls the package import graph; a recorder that must survive the
worst moment on the box should depend on as little as possible.)

RUN IT ON THE HOST, not inside an agent sandbox. /proc/meminfo and /proc/pressure/* are
host-wide and read correctly from anywhere, but /proc process enumeration is PID-namespaced:
inside a bwrap sandbox the `top` field lists only sandbox processes (observed: "uv 19MB")
and is worse than useless, since it looks authoritative while omitting the real consumers.

Run:  uv run python -m cohezion.observability.pressure_recorder --interval 10
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path


LOG = Path.home() / ".cohezion" / "pressure.jsonl"


def _meminfo() -> dict[str, float]:
    out: dict[str, float] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, _, rest = line.partition(":")
            if key in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                out[key] = int(rest.split()[0]) / 1048576  # kB -> GiB
    except (OSError, ValueError, IndexError):
        pass
    return out


def _psi(resource: str) -> dict[str, float]:
    """Pressure Stall Information: the share of time tasks stalled on this resource.

    `full avg10` rising above zero is the signal that matters -- it means EVERY task was
    stalled, which is what a freeze looks like from inside before it becomes total.
    """
    out: dict[str, float] = {}
    try:
        for line in Path(f"/proc/pressure/{resource}").read_text().splitlines():
            kind = line.split()[0]  # "some" | "full"
            for field in line.split()[1:]:
                name, _, value = field.partition("=")
                if name in ("avg10", "avg60"):
                    out[f"{kind}_{name}"] = float(value)
    except (OSError, ValueError, IndexError):
        pass
    return out


def _top_rss(n: int = 3) -> list[dict[str, object]]:
    """Largest resident processes, read straight from /proc (no ps dependency).

    PID-NAMESPACED: inside a container this sees only that namespace's processes. The
    memory and PSI fields stay accurate everywhere; this one silently narrows. Run the
    recorder on the host if you want it to mean anything.
    """
    procs: list[tuple[int, int, str]] = []
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                statm = (entry / "statm").read_text().split()
                rss_mb = int(statm[1]) * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024)
                comm = (entry / "comm").read_text().strip()
            except (OSError, ValueError, IndexError):
                continue
            procs.append((rss_mb, int(entry.name), comm))
    except OSError:
        return []
    procs.sort(reverse=True)
    return [{"rss_mb": r, "pid": p, "comm": c} for r, p, c in procs[:n]]


def sample() -> dict[str, object]:
    """One observation. Never raises — a collection failure must not stop recording."""
    mem = _meminfo()
    row: dict[str, object] = {
        "ts": time.time(),
        "avail_gb": round(mem.get("MemAvailable", -1), 2),
        "swap_used_gb": round(mem.get("SwapTotal", 0) - mem.get("SwapFree", 0), 2),
        "mem_psi": _psi("memory"),
        "io_psi": _psi("io"),
        "cpu_psi": _psi("cpu"),
        "top": _top_rss(),
    }
    with contextlib.suppress(OSError):
        row["load1"] = os.getloadavg()[0]
    return row


def record_forever(interval: float, path: Path = LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Line-buffered append + explicit fsync: the whole point is that the LAST line survives
    # an event that kills the process. Without fsync the tail sits in the page cache and is
    # lost in exactly the scenario this exists for.
    with path.open("a", encoding="utf-8") as fh:
        while True:
            fh.write(json.dumps(sample()) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            time.sleep(interval)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interval", type=float, default=10.0, help="seconds between samples")
    ap.add_argument("--once", action="store_true", help="print one sample and exit")
    args = ap.parse_args()
    if args.once:
        print(json.dumps(sample(), indent=2))
        return 0
    record_forever(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
