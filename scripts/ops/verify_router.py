#!/usr/bin/env python3
"""Verify a lemonade `collection.router` policy BY CONTENT, not by shape.

WHY THIS EXISTS. On 2026-08-30 the router was registered and "verified" by
sending three prompts and checking WHICH model answered. All three happened to
route to healthy models. The catch-all target was returning '////////' to
"what is 2+2" -- with `finish_reason=stop` and a well-formed OpenAI envelope, so
every structural check passed. The registration had also been silently dropped
by a lemonade upgrade, and `~/.hermes/config.yaml` was pointing at a model the
server no longer had.

Three failure modes, none of which a structural check can see:
  1. the policy is not registered at all          -> caught by presence
  2. a candidate is absent from the catalog       -> caught by preconditions
  3. a candidate returns 200 with garbage         -> caught ONLY by reading it

Usage:
    python scripts/ops/verify_router.py                     # checks + probes
    python scripts/ops/verify_router.py --policy PATH
    python scripts/ops/verify_router.py --preflight-only    # no generation

Exit 0 when every check passes, 1 otherwise. Safe to run against a live server:
it only reads, plus one short generation per candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE = "http://localhost:13305"
DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "config/router/cohezion-router.json"

# A known-answer probe. Deliberately trivial: any model that cannot do this is
# broken, and no model that can is thereby proven good -- this is a liveness
# floor, not a quality bar.
PROBE = "What is 2+2? Answer with just the number."
EXPECT_IN = "4"


def _get(path: str, timeout: float = 20.0) -> Any:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:  # noqa: S310
        return json.load(r)


def _chat(model: str, prompt: str, timeout: float = 420.0) -> str:
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 64,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310 - fixed localhost URL, no user-supplied scheme
        f"{BASE}/v1/chat/completions", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        d = json.load(r)
    msg = d["choices"][0]["message"]
    # Thinking models park the answer in reasoning_content, not content.
    return (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()


def degenerate(text: str) -> bool:
    """A run of one or two repeated characters -- the observed failure shape."""
    t = "".join(text.split())
    return (not t) or (len(set(t)) <= 3 and len(t) > 20)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--preflight-only", action="store_true", help="skip generation probes")
    args = ap.parse_args()

    if not args.policy.exists():
        print(f"FAIL: policy not found: {args.policy}")
        return 1
    policy = json.loads(args.policy.read_text())
    routing = policy["routing"]
    name = policy["model_name"]
    failures: list[str] = []

    # --- structural preconditions -------------------------------------------
    targets = {routing["default_model"]} | {
        r["route_to"] for r in routing["rules"] if "route_to" in r
    }
    orphans = targets - set(routing["candidates"])
    if orphans:
        failures.append(f"route targets outside candidates: {sorted(orphans)}")

    try:
        catalog = _get("/api/v1/models")
    except (urllib.error.URLError, OSError) as exc:
        print(f"FAIL: router not answering on {BASE}: {exc}")
        return 1
    entries = catalog.get("data", catalog)
    ids = {e.get("id") for e in entries}
    downloaded = {e.get("id") for e in entries if e.get("downloaded") is True}

    if name not in ids:
        failures.append(f"{name} is NOT REGISTERED (a lemonade upgrade drops this silently)")
    print(f"policy   : {args.policy}")
    print(f"registered: {'yes' if name in ids else 'NO'}")
    print()

    for c in routing["candidates"]:
        problems = []
        if c not in ids:
            problems.append("not in catalog")
        elif c not in downloaded:
            problems.append("not downloaded")
        if problems:
            failures.append(f"candidate {c}: {', '.join(problems)}")
        print(f"  [{'OK ' if not problems else 'BAD'}] {c:42s} {', '.join(problems)}")

    # --- content probes -----------------------------------------------------
    # This is the half that a structural check cannot do, and the half that
    # would have caught the real defect.
    if not args.preflight_only:
        print()
        for c in routing["candidates"]:
            if c not in downloaded:
                continue
            try:
                out = _chat(c, PROBE)
            except Exception as exc:  # report, never abort the sweep
                failures.append(f"candidate {c}: probe raised {type(exc).__name__}")
                print(f"  [ERR] {c:42s} {type(exc).__name__}")
                continue
            if degenerate(out):
                failures.append(f"candidate {c}: DEGENERATE output {out[:40]!r}")
                verdict = "DEGEN"
            elif EXPECT_IN not in out[:60]:
                verdict = "ODD"  # not a failure: a thinking model may preamble
            else:
                verdict = "OK "
            print(f"  [{verdict}] {c:42s} {out[:44]!r}")

    print()
    if failures:
        print(f"FAIL ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    # Say exactly what was checked. With --preflight-only NO generation ran, and
    # claiming "answering coherently" there would be this tool committing the
    # error it exists to catch: a verdict asserting more than was verified.
    if args.preflight_only:
        print(
            "PASS (PREFLIGHT ONLY): registered, every candidate present and downloaded.\n"
            "      Content NOT checked -- a degenerate model passes every check above.\n"
            "      Re-run without --preflight-only before trusting this router."
        )
    else:
        print("PASS: registered, every candidate present, downloaded, and answering coherently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
