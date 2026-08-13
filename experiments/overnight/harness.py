"""Overnight local-inference harness: policy-driven tier cascade over the task suite.

Uses the production components under test — ``build_gaia_llm_tier`` (thinking-model
and card-sampling fixes included) and ``task_classifier.classify`` (zero-model-call
routing) — but runs the cascade loop itself so experiments can gate escalation on
the task's own deterministic validator (an axis TieredOrchestrator's char-count
QualityGate cannot express).

Output: one ``METRIC name=value`` line per metric on stdout (autoresearch protocol).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tasks import TASKS  # noqa: E402

from cohezion.inference.gaia_adapter import build_gaia_llm_tier  # noqa: E402
from cohezion.inference.task_classifier import classify  # noqa: E402

POLICY_PATH = Path(__file__).parent / "policy.json"


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text())


async def run_task(task, tiers, policy, sem, stats) -> dict:
    entry = 0
    if policy.get("use_classifier_entry", True):
        decision = classify(task.prompt)
        entry = policy.get("entry_by_node", {}).get(decision.node, 0)
        gate_chars = decision.quality_gate_chars
    else:
        gate_chars = 0
    entry = max(0, min(entry, len(tiers) - 1))

    attempts = []
    passed = False
    text = ""
    async with sem:
        for idx in range(entry, len(tiers)):
            tier, tier_cfg = tiers[idx]
            t0 = time.perf_counter()
            try:
                tier_timeout = tier_cfg.get("timeout_s") or policy.get("per_task_timeout_s", 240)
                result = await asyncio.wait_for(tier.run(task.prompt), timeout=tier_timeout)
                text = result.text or ""
                err = result.error
            except TimeoutError:
                text, err = "", "timeout"
                stats["timeouts"] += 1
            except Exception as exc:  # noqa: BLE001 - harness must survive any tier failure
                text, err = "", f"{type(exc).__name__}: {exc}"
            dt = time.perf_counter() - t0

            ok_chars = bool(text.strip()) and (
                not policy.get("use_classifier_gate_chars", True) or len(text) >= gate_chars
            )
            min_chars = tier_cfg.get("gate_min_chars")
            if min_chars is not None and len(text) < min_chars:
                ok_chars = False
            ok_valid = task.validate(text) if text else False
            attempts.append(
                {"tier": idx, "model": tier_cfg["model"], "s": round(dt, 1),
                 "chars": len(text), "valid": ok_valid, "err": err}
            )
            stats["tier_calls"][idx] += 1

            gate_pass = ok_valid if policy.get("validator_gate", True) else ok_chars
            if gate_pass:
                passed = ok_valid
                break
        else:
            passed = task.validate(text) if text else False

    return {"task_id": task.task_id, "category": task.category, "passed": passed,
            "entry": entry, "escalations": max(0, len(attempts) - 1), "attempts": attempts}


async def main() -> None:
    policy = load_policy()
    tiers = [
        (build_gaia_llm_tier(model_id=cfg["model"], max_tokens=cfg["max_tokens"], silent=True), cfg)
        for cfg in policy["tiers"]
    ]
    sem = asyncio.Semaphore(policy.get("concurrency", 3))
    stats: dict = {"timeouts": 0, "tier_calls": Counter()}

    # Warm-up: serve one tiny call per tier model BEFORE the suite clock starts.
    # Run-start timeout clusters (5 of 8 runs) were tasks queueing behind a model
    # load/swap until their timeout expired — the load-readiness race, GGUF edition.
    for tier, cfg in tiers:
        t0 = time.perf_counter()
        try:
            await asyncio.wait_for(tier.run("Reply with the single word: ready"), timeout=600)
            print(f"WARMUP {cfg['model']} ok in {time.perf_counter() - t0:.1f}s")
        except Exception as exc:  # noqa: BLE001 - a cold tier is reported, not fatal
            print(f"WARMUP {cfg['model']} FAILED after {time.perf_counter() - t0:.1f}s: {exc}")

    suite_start = time.perf_counter()
    results = await asyncio.gather(*(run_task(t, tiers, policy, sem, stats) for t in TASKS))
    duration = time.perf_counter() - suite_start

    passed = sum(r["passed"] for r in results)
    escalations = sum(r["escalations"] for r in results)
    # routing_misses: attempts where the model RESPONDED (no error/timeout) but failed
    # the task validator — load-robust routing-quality signal (queue time can cause a
    # timeout, but it cannot make a returned answer wrong).
    routing_misses = sum(
        1
        for r in results
        for a in r["attempts"]
        if a["err"] is None and a["chars"] > 0 and not a["valid"]
    )
    by_cat: Counter = Counter()
    for r in results:
        if r["passed"]:
            by_cat[r["category"]] += 1

    for r in results:
        flag = "PASS" if r["passed"] else "FAIL"
        detail = " -> ".join(
            f"T{a['tier']}({a['s']}s,{a['chars']}c{',ERR:' + str(a['err'])[:40] if a['err'] else ''})"
            for a in r["attempts"]
        )
        print(f"[{flag}] {r['task_id']} entry=T{r['entry']} {detail}")

    print(f"CATEGORY {dict(by_cat)}")
    print(f"METRIC passed={passed}")
    print(f"METRIC pass_rate={passed / len(TASKS):.4f}")
    print(f"METRIC duration_s={duration:.1f}")
    print(f"METRIC escalations={escalations}")
    print(f"METRIC routing_misses={routing_misses}")
    print(f"METRIC timeouts={stats['timeouts']}")
    print(f"METRIC tier_calls={json.dumps(dict(stats['tier_calls']))}")


if __name__ == "__main__":
    asyncio.run(main())
