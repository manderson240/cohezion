#!/usr/bin/env python3
"""Dogfood Claims B/C/D — deterministic behaviors of cohezion.inference.

B — TieredOrchestrator.run(budget_usd=) honors min(self_cap, parent_budget)
C — extend_claude() rejects unknown claude_model BEFORE local loop
D — health._probe_anthropic uses `-p ping --max-budget-usd` not `--version`

Run:
    cd /home/mike-anderson/dev/cohezion
    uv run python /tmp/cohezion-deliver/scripts/dogfood/claim_bcd_deterministic.py

Exit 0 if all three claims pass. Prints PASS/FAIL per claim to stdout.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from unittest.mock import AsyncMock, patch


def _header(name: str) -> None:
    print(f"\n=== {name} ===")


def _pass(claim: str, detail: str = "") -> None:
    print(f"PASS  {claim}{' — ' + detail if detail else ''}")


def _fail(claim: str, detail: str) -> None:
    print(f"FAIL  {claim} — {detail}")


async def verify_claim_b() -> bool:
    _header("Claim B — Nested orchestrator budget pass-through")
    from cohezion.inference.fleet import RouteResult
    from cohezion.inference.orchestrator import QualityGate, TieredOrchestrator

    # Signature check (structural)
    sig = inspect.signature(TieredOrchestrator.run)
    if "budget_usd" not in sig.parameters:
        _fail("B-structural", "run() missing budget_usd kwarg")
        return False
    _pass("B-structural", "run() accepts budget_usd kwarg")

    # Behavioral check: parent $0.01, nested $1.00
    def _rr(text, cost):
        return RouteResult(
            text=text, model="m", lane="test", latency_ms=1.0, ttft_ms=1.0, cost_usd=cost
        )

    inner = TieredOrchestrator(
        tiers=[
            ("inner-t0", QualityGate(min_chars=100)),  # will fail
            ("inner-t1", QualityGate.TRUST),
        ],
        max_cost_usd=1.00,  # generous local ceiling
    )
    parent = TieredOrchestrator(
        tiers=[
            ("parent-t0", QualityGate(min_chars=100)),  # fail, escalate
            (inner, QualityGate.TRUST),
        ],
        max_cost_usd=0.01,  # tight outer cap
    )
    side_effects = [
        _rr("short", 0.009),  # parent-t0 uses $0.009
        _rr("short", 0.005),  # inner-t0 pushes over $0.01
        _rr("unreachable", 0.50),  # inner-t1 must NOT run
    ]

    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(side_effect=side_effects),
    ) as m:
        result = await parent.run("test")

    if m.await_count != 2:
        _fail(
            "B-behavioral", f"expected 2 route() calls (parent-t0 + inner-t0); got {m.await_count}"
        )
        return False
    _pass(
        "B-behavioral",
        f"route() called 2x as expected (inner-t1 correctly skipped); cost=${result.cost_usd:.4f}",
    )
    return True


async def verify_claim_c() -> bool:
    _header("Claim C — extend_claude() rejects unknown model before local loop")
    from cohezion.inference import extend_claude

    mock_route = AsyncMock()
    with patch("cohezion.inference.fleet.route", mock_route):
        result = await extend_claude("test", claude_model="this-model-does-not-exist-at-all")

    if mock_route.await_count != 0:
        _fail(
            "C", f"route() was called {mock_route.await_count} times; should be 0 on unknown model"
        )
        return False
    if not result.error or "this-model-does-not-exist-at-all" not in result.error:
        _fail("C", f"expected error mentioning model name; got {result.error!r}")
        return False
    _pass("C", f"route() not called; error={result.error[:80]!r}")
    return True


def verify_claim_d() -> bool:
    _header("Claim D — Claude CLI probe uses -p/--max-budget-usd, not --version")
    import httpx

    from cohezion.inference.health import check_fleet

    class FakeCompleted:
        returncode = 0
        stdout = "pong"
        stderr = ""

    captured_argv = []

    def capture(argv, *args, **kwargs):
        captured_argv.append(list(argv))
        return FakeCompleted()

    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("subprocess.run", side_effect=capture):
                check_fleet(force=True)

    claude_invocations = [a for a in captured_argv if a and "claude" in a[0]]
    if not claude_invocations:
        _fail("D", "no claude subprocess was spawned")
        return False

    argv = claude_invocations[0]
    if argv[1] != "-p":
        _fail("D", f"expected argv[1] == '-p', got {argv!r}")
        return False
    if "--max-budget-usd" not in argv:
        _fail("D", f"expected --max-budget-usd in argv, got {argv!r}")
        return False
    if "--version" in argv:
        _fail("D", f"probe should not use --version (too weak), got {argv!r}")
        return False
    _pass("D", f"argv={argv}")
    return True


async def _amain() -> int:
    results = []
    results.append(await verify_claim_b())
    results.append(await verify_claim_c())
    results.append(verify_claim_d())

    print("\n=== Summary ===")
    labels = ["B", "C", "D"]
    for label, ok in zip(labels, results):
        print(f"  {label}: {'PASS' if ok else 'FAIL'}")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_amain()))
