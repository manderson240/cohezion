"""The Artemis II study as goals and loops, not a one-off trace.

Each finding in README.md was produced once, by running a script, and then written down. That is a
linear trace: nothing re-checks that the written claim still matches the data. This module recasts
the study with ``cohezion.compound.goals_and_loops_orchestrator``:

  * a **Goal** per group of findings, with deterministic **acceptance criteria**. Each criterion
    recomputes something from the inputs or committed outputs, and records its evidence;
  * an **ExecutionLoop** per goal: exec (recompute the outputs) -> verify (run every criterion) ->
    another cycle if verification failed. Cycles retry transient failures, such as a network
    fetch. They never change a reference value to make a check pass.

A goal is SATISFIED only when every criterion passes in the same cycle. ``study_goals.json`` records
each goal's status, cycles and per-criterion evidence. If a finding stops holding, the next run says
so instead of the README silently going stale.

Usage:
    python research/artemis2/study_goals.py TRANSCRIPT_DIR [--out PATH] [--skip-network]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.append(str(HERE))
sys.path.append(str(REPO / "src"))

from cohezion.compound.goals_and_loops_orchestrator import (  # noqa: E402
    GoalsAndLoopsOrchestrator,
    GoalStatus,
)


def committed(name: str) -> dict:
    return json.loads((HERE / name).read_text())


def as_json(obj) -> object:
    """Normalise a freshly computed result the way the scripts serialise it."""
    return json.loads(json.dumps(obj, default=str))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Study:
    """Recomputes the study's outputs from its inputs; one instance per loop cycle."""

    def __init__(self, transcript_dir: Path, network: bool) -> None:
        self.transcript_dir = transcript_dir
        self.network = network
        self.cache: dict[str, object] = {}

    def get(self, key: str, fn: Callable[[], object]) -> object:
        if key not in self.cache:
            self.cache[key] = fn()
        return self.cache[key]

    def hobo(self) -> dict:
        import analyze_hobo as hobo

        def run():
            paths = hobo.fetch(HERE / "data")
            dfs = {sn: hobo.load(c) for sn, (c, _x) in paths.items()}
            labels = {sn: hobo.label_stats(x) for sn, (_c, x) in paths.items()}
            return as_json(hobo.analyse(dfs, labels))

        return self.get("hobo", run)

    def transcripts(self):
        import transcripts as trn

        return self.get("transcripts", lambda: trn.load(self.transcript_dir))

    def tasks(self) -> dict:
        import verifiable_tasks as vt

        return self.get("tasks", lambda: as_json(vt.build(HERE / "data", self.transcript_dir)))

    def flashes(self) -> dict:
        import flash_map as fm

        def run():
            im = fm.embedded_jpeg(fm.fetch(HERE / "data"))
            models = fm.fit_models(fm.grid_points(im), fm.horizons_view())
            return as_json(fm.locate(fm.markers(im), models))

        return self.get("flashes", run)


Check = tuple[str, str, Callable[[Study], tuple[bool, str]]]


# --- acceptance criteria ---------------------------------------------------------------------


def hobo_reproduces(s: Study) -> tuple[bool, str]:
    fresh, old = s.hobo(), committed("hobo_results.json")
    diff = sorted(k for k in set(fresh) | set(old) if fresh.get(k) != old.get(k))
    return not diff, "all keys identical" if not diff else f"differs in: {diff}"


def locker_dry_in_flight(s: Study) -> tuple[bool, str]:
    ah = s.hobo()["SN1104"]["abs_humidity_by_phase_gm3"]
    pad, flight = ah["1 pre-launch (pad)"], ah["2 flight"]
    ok = (
        abs(flight - pad) < 0.5 and 4.6 <= flight <= 5.6
    )  # README: "~5.1 g/m3", "as dry as on the pad"
    return ok, f"SN1104 mean AH pad {pad} vs flight {flight} g/m3"


def locker_e_event(s: Study) -> tuple[bool, str]:
    ev = s.hobo()["fd09_relocation"]["locker_E_event"]
    return ev[
        "RH_jump_vs_prev_min"
    ] == 12.32, f"Locker E jump {ev['RH_jump_vs_prev_min']} % RH at {ev['peak_at']}"


def quotes_verbatim(s: Study) -> tuple[bool, str]:
    import transcripts as trn

    found, missing = trn.verify_events(s.transcripts())
    return not missing, f"{len(found)} of {len(trn.EVENTS)} quotes match" + (
        f"; missing {missing}" if missing else ""
    )


def loop_cuts_reproduce(s: Study) -> tuple[bool, str]:
    import transcripts as trn

    fresh = as_json(trn.loop_gaps(s.transcripts()))["cuts"]
    old = committed("transcript_events.json")["loop_gaps"]["cuts"]
    mins = [c["removed_min"] for c in fresh]
    return fresh == old, f"{len(fresh)} cuts, minutes removed {mins}"


def flashes_reproduce(s: Study) -> tuple[bool, str]:
    old = committed("flash_annotations.json")["flashes"]
    fresh = s.flashes()
    same = {k: fresh[k]["models"] == old[k]["models"] for k in old}
    return all(same.values()), f"model coordinates identical per flash: {same}"


def earth_view() -> tuple[float, float]:
    """Earth's sub-observer point on the Moon, as committed by flash_map.py (JPL Horizons)."""
    v = committed("flash_annotations.json")["earth_view"]
    return v["sub_lon"], v["sub_lat"]


def flashes_far_side(_s: Study) -> tuple[bool, str]:
    """Every mapped flash is more than 100 deg from Earth's sub-observer point, i.e. at least
    10 deg beyond Earth's limb, in both grid fits (render orientation assumed)."""
    earth = earth_view()
    beyond = {
        k: round(min(_gc_deg(earth, (m["lon_E"], m["lat"])) for m in f["models"].values()) - 90, 1)
        for k, f in committed("flash_annotations.json")["flashes"].items()
        if f["models"]
    }
    return min(beyond.values()) >= 10, f"degrees beyond Earth's limb per flash: {beyond}"


def _gc_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    (l1, p1), (l2, p2) = (tuple(math.radians(v) for v in x) for x in (a, b))
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(l1 - l2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def flashes_far_side_any_rotation(_s: Study) -> tuple[bool, str]:
    """A flash closer to Orion's view centre than that centre is to Earth's limb stays on the
    far side however the crew's picture was rotated. Required for #1 and #2 (README claim)."""
    fa = committed("flash_annotations.json")
    v = fa["horizons_view"]
    centre = (v["sub_lon"], v["sub_lat"])
    safe = _gc_deg(centre, earth_view()) - 90  # how far beyond Earth's limb the view centre is
    dist = {
        k: round(max(_gc_deg(centre, (m["lon_E"], m["lat"])) for m in f["models"].values()), 1)
        for k, f in fa["flashes"].items()
        if f["models"]
    }
    ok = all(dist[k] < safe for k in ("1", "2"))
    return ok, f"view centre {safe:.1f} deg beyond Earth's limb; flash distances from it {dist}"


README_REGISTER: list[tuple[str, Callable[[], bool]]] = [
    # (text that must appear in README.md, check that the committed JSON still supports it)
    ("12.3 % in one minute", lambda: committed("hobo_results.json")["fd09_relocation"]["locker_E_event"]["RH_jump_vs_prev_min"] == 12.32),
    ("about 18 minutes after splashdown", lambda: committed("hobo_results.json")["splashdown_humidity"]["SN1104"]["AH_onset_5sigma_at"].startswith("2026-04-11 00:24")),
    ("37 are flicker", lambda: committed("flash_search_video.json")["triage"] == {"from_dark": 3, "existing_source_brightening": 37}),
    ("102–164°E", lambda: _lon_span() == (102, 164)),
    ("about 15° beyond", lambda: round(_nearest_beyond_limb()) == 15),
    ("6,355", lambda: committed("transcript_events.json")["quality"]["rows"] == 6355),
    ("61 `[[inaudible", lambda: committed("transcript_events.json")["quality"]["inaudible_markers"] == 61),
    ("24.77 °C", lambda: _answer("hobo-rh-jump-temperature") == 24.77),
    ("5.114 g/m³", lambda: _answer("hobo-warmer-logger-absolute-humidity") == 5.114),
    ("71 (Hansen)", lambda: _answer("loops-crew-rows-2026-04-07") == 71),
    ("21,489 (Wiseman)", lambda: _answer("transcripts-crew-word-count") == 21489),
    ("565.7 min", lambda: _answer("loops-longest-removed-audio") == 565.7),
]  # fmt: skip


def _lon_span() -> tuple[int, int]:
    lons = [m["lon_E"] for f in committed("flash_annotations.json")["flashes"].values() if f["models"]
            for m in f["models"].values()]  # fmt: skip
    return int(min(lons)), round(max(lons))


def _nearest_beyond_limb() -> float:
    earth = earth_view()
    return min(
        _gc_deg(earth, (m["lon_E"], m["lat"])) - 90
        for f in committed("flash_annotations.json")["flashes"].values()
        if f["models"]
        for m in f["models"].values()
    )


def _answer(task_id: str) -> float:
    return next(
        t["answer"] for t in committed("verifiable_tasks.json")["tasks"] if t["id"] == task_id
    )


def readme_numbers_trace(_s: Study) -> tuple[bool, str]:
    text = (HERE / "README.md").read_text()
    bad = [phrase for phrase, check in README_REGISTER if phrase not in text or not check()]
    return (
        not bad,
        f"{len(README_REGISTER) - len(bad)}/{len(README_REGISTER)} registered README figures match"
        + (f"; failing: {bad}" if bad else ""),
    )


def video_no_flash(_s: Study) -> tuple[bool, str]:
    v = committed("flash_search_video.json")
    n, tri = len(v["corroborated"]), v["triage"]
    ok = n == 40 and tri["from_dark"] + tri["existing_source_brightening"] == n
    return ok, f"{n} corroborated events, triage {tri}"


def tasks_reproduce(s: Study) -> tuple[bool, str]:
    fresh, old = s.tasks(), committed("verifiable_tasks.json")
    same = fresh == old
    agreed = all(t["checks"]["two_implementations_agree"] for t in fresh["tasks"])
    return same and agreed, (
        f"{len(fresh['tasks'])} kept, {len(fresh['rejected'])} dropped; identical to committed: "
        f"{same}; both implementations agree on every kept task: {agreed}"
    )


def tests_green(_s: Study) -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/research/", "-q", "-p", "no:warnings", "--noconftest"],
        cwd=REPO, capture_output=True, text=True, timeout=600, check=False,
    )  # fmt: skip
    tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    return r.returncode == 0, tail


def inputs_recorded(s: Study) -> tuple[bool, str]:
    files = sorted((HERE / "data").glob("*.csv")) + sorted(
        s.transcript_dir.rglob("*_trn-csv_v01.csv")
    )
    digest = hashlib.sha256("".join(f"{p.name}:{sha256(p)}\n" for p in files).encode()).hexdigest()
    s.cache["input_digest"] = digest
    return bool(files), f"{len(files)} input files, combined SHA-256 {digest[:16]}"


GOALS: list[tuple[str, str, str, list[Check], bool]] = [
    # (id, title, objective, criteria, needs_network)
    ("inputs", "Inputs are pinned", "Record what data every other goal was checked against", [
        ("I1", "HOBO and transcript inputs are present and hashed", inputs_recorded),
    ], False),
    ("lockers", "Locker findings hold", "Section 1 claims follow from the MD5-verified HOBO files", [
        ("L1", "Re-running the analysis reproduces hobo_results.json exactly", hobo_reproduces),
        ("L2", "Lockers were as dry in flight as on the pad (~5.1 g/m3)", locker_dry_in_flight),
        ("L3", "Locker E 12.32 % RH one-minute jump on flight day 9", locker_e_event),
    ], True),
    ("transcripts", "Transcript findings hold", "Section 3 quotes and gaps match the archive CSVs", [
        ("T1", "Every curated quote matches a row verbatim at its UTC stamp", quotes_verbatim),
        ("T2", "Stitched-recording cuts reproduce the committed list", loop_cuts_reproduce),
    ], False),
    ("flashes", "Impact-flash findings hold", "Section 3 flash map and camera searches", [
        ("F1", "Re-fitting the crew's annotation map reproduces every flash coordinate", flashes_reproduce),
        ("F2", "In the render's orientation, all mapped flashes lie >=10 deg beyond Earth's limb", flashes_far_side),
        ("F4", "Flashes #1 and #2 are far-side under any rotation of the crew's picture", flashes_far_side_any_rotation),
        ("F3", "SAW3 video: all 40 corroborated events are triaged; none left unexplained", video_no_flash),
    ], True),
    ("questions", "Verifiable questions hold", "Section 4 question set is reproducible and checked", [
        ("Q1", "Rebuilding reproduces verifiable_tasks.json and both implementations agree", tasks_reproduce),
    ], True),
    ("writeup", "The write-up matches the data", "README figures named by reviewers still trace to the JSON", [
        ("W1", "Every registered README figure is present and supported", readme_numbers_trace),
    ], False),
    ("regressions", "Past fixes stay fixed", "Every bug found by review keeps its regression test green", [
        ("R1", "tests/unit/research passes", tests_green),
    ], False),
]  # fmt: skip


# --- loops -----------------------------------------------------------------------------------


async def run_goal(orch: GoalsAndLoopsOrchestrator, spec, study_factory, max_cycles: int) -> dict:
    gid, title, objective, checks, _net = spec
    goal = orch.create_goal(gid, title, objective, [(cid, desc) for cid, desc, _fn in checks])
    loop = orch.create_loop(gid, max_cycles=max_cycles)
    fns = {cid: fn for cid, _d, fn in checks}
    state: dict[str, Study] = {}

    async def exec_fn() -> None:
        state["study"] = study_factory()  # fresh cache each cycle: recompute, don't reuse

    async def verify_fn() -> tuple[bool, str]:
        for ac in goal.acceptance_criteria:
            try:
                ac.verified, ac.evidence = fns[ac.id](state["study"])
            except Exception as exc:
                ac.verified, ac.evidence = False, f"{type(exc).__name__}: {exc}"
        return goal.is_converged(), "; ".join(
            f"{ac.id}={'ok' if ac.verified else 'FAIL'}" for ac in goal.acceptance_criteria
        )

    await loop.run(exec_fn, verify_fn)
    return {
        "id": gid, "title": title, "objective": objective, "status": goal.status.value,
        "cycles": len(loop.cycle_history),
        "criteria": [{"id": ac.id, "description": ac.description, "verified": ac.verified,
                      "evidence": ac.evidence} for ac in goal.acceptance_criteria],
        "input_digest": state["study"].cache.get("input_digest"),
    }  # fmt: skip


async def run_all(transcript_dir: Path, network: bool, max_cycles: int) -> tuple[dict, str]:
    orch = GoalsAndLoopsOrchestrator()
    results = []
    for spec in GOALS:
        if spec[4] and not network:
            results.append({"id": spec[0], "title": spec[1], "status": "skipped (needs network)"})
            continue
        results.append(
            await run_goal(orch, spec, lambda: Study(transcript_dir, network), max_cycles)
        )
    digest = next((r["input_digest"] for r in results if r.get("input_digest")), None)
    for r in results:
        r.pop("input_digest", None)
    satisfied = sum(r["status"] == GoalStatus.SATISFIED.value for r in results)
    return {
        "inputs_sha256": digest,
        "goals_satisfied": f"{satisfied}/{len(results)}",
        "goals": results,
    }, orch.render_summary()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcripts", type=Path)
    ap.add_argument(
        "--out", type=Path, default=None, help="default: study_goals.json (full runs only)"
    )
    ap.add_argument("--skip-network", action="store_true", help="skip goals that download inputs")
    ap.add_argument("--max-cycles", type=int, default=2)
    args = ap.parse_args()
    result, board = asyncio.run(run_all(args.transcripts, not args.skip_network, args.max_cycles))
    out = args.out or (None if args.skip_network else HERE / "study_goals.json")
    if out:  # a partial run must not overwrite the committed full result
        out.write_text(json.dumps(result, indent=1) + "\n")
    print(board)
    for g in result["goals"]:
        for c in g.get("criteria", []):
            print(f"  {g['id']}/{c['id']} {'ok  ' if c['verified'] else 'FAIL'} {c['evidence']}")
    if any(
        g["status"] not in (GoalStatus.SATISFIED.value, "skipped (needs network)")
        for g in result["goals"]
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
