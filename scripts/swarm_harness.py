"""Heterogeneous local-inference swarm harness with a gate that can fail and durable output.

Lives in the repo, NOT in $TMPDIR: /tmp is tmpfs on this box, and an earlier version of this
harness was destroyed by a reboot along with ~30 lanes of results
(see scripts/durable_swarm_output.py for the measurement).

THE OUTPUT GATE carries three defences, each added after a real failure on 2026-08-15:

  1. marker present   -- a length-only gate ("len > 400") passed 6/6 lanes that contained
     100% reasoning scratchpad and zero answer. Length cannot distinguish 6,000 characters of
     deliberation from 6,000 characters of answer.
  2. split on LAST marker -- models emit the marker while narrating the contract back to
     themselves ("` followed by the answer."), so splitting on the FIRST occurrence captured
     the deliberation as if it were the answer.
  3. required structural fields -- a POSITIVE contract that free-form reasoning does not
     accidentally satisfy. A blocklist of deliberation phrases is endlessly evadable and is
     kept only as a secondary smell test.

A gate that has never been shown to FAIL is not evidence, so ``self_test`` runs before any
lane and asserts rejection of thinking-only, empty and stub outputs.

CONCURRENCY IS MEASURED, never assumed: a swarm that silently serialised on one device returns
answers exactly like a working one. Only ``wall-clock vs serial-sum`` distinguishes them, so it
is printed every run. A speedup near 1.0x means the lanes did not overlap.

MODEL SELECTION IS LOAD-BEARING. Measured 2026-08-15: Gemma-4-26B-A4B ruminates to the token
ceiling (14-17k raw chars) and never terminates on evaluative prompts, while Gemma-4-E4B and the
FLM MoE terminate cleanly at 2-3k. Six prompt variants were spent before recognising this as a
MODEL problem rather than a prompt problem. Suspect the lane before the prompt when every
variant fails identically.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from durable_swarm_output import DurableRun

from cohezion.inference.gaia_adapter import build_gaia_llm_tier


MARKER = "===FINAL==="
DELIBERATION = ("wait,", "let's refine", "*is it", "followed by the answer", "self-correction")

CONTRACT = (
    "\n\nOUTPUT CONTRACT (mandatory): think briefly, then emit the line\n"
    f"{MARKER}\n"
    "and AFTER it write your finished answer. The marker is NOT the end of your response - "
    "the most important content comes after it. Never stop immediately after the marker.\n"
)


def extract(text: str, required_fields: tuple[str, ...] = ()) -> tuple[str, str]:
    """Return ``(answer, rejection_reason)``. Reasons are specific, never a bare bool."""
    if not text or not text.strip():
        return "", "empty"
    if MARKER not in text:
        return "", "no-marker (model never left its reasoning channel)"
    answer = text.rsplit(MARKER, 1)[1].strip()
    # With required_fields, STRUCTURE is the guarantee and the length floor relaxes: a correct
    # terse answer is ~230 chars and a 300-char floor would reject it.
    floor = 120 if required_fields else 300
    if len(answer) < floor:
        return "", f"answer-too-short ({len(answer)} < {floor})"
    missing = [f for f in required_fields if f.lower() not in answer.lower()]
    if missing:
        return "", f"missing-required-fields {missing}"
    hits = [d for d in DELIBERATION if d in answer.lower()]
    if hits:
        return "", f"deliberation-leaked {hits[:3]}"
    return answer, ""


def _must(condition: bool, message: str) -> None:
    """Raise unconditionally on failure.

    Deliberately NOT ``assert``: asserts are stripped under ``python -O``, which would make
    self_test() report a clean pass while checking nothing. A gate that cannot fail is not a
    gate, and this function exists specifically to prove the gate CAN fail — so it must not be
    the one thing in the file an optimisation flag can silently disable.
    """
    if not condition:
        raise AssertionError(message)


def self_test() -> None:
    """Prove the gate can FAIL before trusting any pass it reports."""
    _must(extract("<|channel>thought " + "reasoning " * 200)[0] == "", "accepted thinking-only")
    _must(extract("")[0] == "", "accepted empty")
    _must(extract(f"x{MARKER}\ntiny")[0] == "", "accepted stub")
    ok = f"reasoning {MARKER}\nFINDING: a\nCONFIDENCE: high - b\n" + "- bullet line\n" * 10
    answer, why = extract(ok, ("FINDING:", "CONFIDENCE:"))
    _must(bool(answer) and not why, f"rejected a valid structured answer: {why}")
    _must("reasoning" not in answer, "leaked pre-marker text into the answer")


async def _run_lane(lane: dict, max_tokens: int, fields: tuple[str, ...],
                    run: DurableRun | None) -> dict:
    t0 = time.time()
    try:
        tier = build_gaia_llm_tier(lane["model"], max_tokens=max_tokens, temperature=0.3)
        res = await tier.run(lane["prompt"] + CONTRACT)
        raw = getattr(res, "text", None) or getattr(res, "output", None) or str(res)
        answer, why = extract(raw or "", fields)
        out = {"lane": lane["name"], "device": lane.get("device", "?"), "model": lane["model"],
               "secs": round(time.time() - t0, 1), "raw_chars": len(raw or ""),
               "raw": raw or "", "answer": answer, "rejected": why}
    except Exception as exc:
        out = {"lane": lane["name"], "device": lane.get("device", "?"), "model": lane["model"],
               "secs": round(time.time() - t0, 1), "raw_chars": 0, "raw": "", "answer": "",
               "rejected": f"{type(exc).__name__}: {exc}"}
    if run is not None:
        run.record_lane(out)  # durable the moment it returns, not at the end of the swarm
    return out


async def run_swarm(lanes: list[dict], slug: str, *, fields: tuple[str, ...] = (),
                    max_tokens: int = 4000, session: str = "") -> dict:
    """Dispatch lanes concurrently; persist each result as it lands.

    ``lanes`` items: ``{"name": str, "model": str, "prompt": str, "device": str (optional)}``.
    """
    self_test()
    run = DurableRun(slug, session=session, meta={"lanes": [x["name"] for x in lanes]})
    t0 = time.time()
    results = await asyncio.gather(*(_run_lane(x, max_tokens, fields, run) for x in lanes))
    elapsed = time.time() - t0

    for r in results:
        status = f"REJECTED[{r['rejected']}]" if r["rejected"] else f"{len(r['answer'])} chars"
        print(f"[{r['device']:>4}] {r['lane']:<24} {r['secs']:>6}s "
              f"raw={r['raw_chars']:<6} {status}", flush=True)
    serial = sum(r["secs"] for r in results)
    speedup = serial / elapsed if elapsed else 1.0
    usable = sum(1 for r in results if not r["rejected"])
    print(f"\n[concurrency] wall-clock {elapsed:.1f}s vs serial-sum {serial:.1f}s "
          f"-> {speedup:.2f}x", flush=True)
    if speedup < 1.2 and len(lanes) > 1:
        print("[warn] speedup ~1.0x — lanes likely SERIALISED on one device, not concurrent",
              flush=True)
    print(f"[gate] {usable}/{len(results)} usable", flush=True)

    run.finalize({"elapsed_s": round(elapsed, 1), "serial_sum_s": round(serial, 1),
                  "speedup": round(speedup, 2), "usable": usable, "lanes": len(results)})
    print(f"[durable] {run.dir}", flush=True)
    return {"dir": str(run.dir), "results": results, "speedup": speedup, "usable": usable}


if __name__ == "__main__":
    self_test()
    print("swarm_harness: gate self-test PASSED (rejects thinking-only/empty/stub)")
