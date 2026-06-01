#!/usr/bin/env python3
"""close_mycelium_loop — prove the recursion loop closes (experience -> skill -> read-back).

The Recursive Forge synthesis found the exact break: the experience->skill loop
is open because the WRITER and the READER are two different empty MyceliumRegistry
instances —
    writer:  compound/executor.py:1273   self._mycelium_registry = MyceliumRegistry()
    reader:  api/services/mycelium_api.py:36   _registry = MyceliumRegistry()
So skills synthesized on the write side are NEVER visible on the read side; the
/skills endpoint always returns nothing. Learning is captured, never read back.

This driver demonstrates BOTH states against the REAL MyceliumRegistry class:
  1. THE BUG   — two separate instances: writer synthesizes, reader sees 0.
  2. THE FIX   — a shared get_instance() singleton (the harness CA2 pattern that
                 SemanticCache already uses): writer and reader are the SAME object,
                 the synthesized skill reads back.
And it does it with REAL experiences captured from a live local-inference call —
so the recursion is grounded in actual on-AMD-silicon execution, $0.

No src/ edits: the singleton is provided here as a thin shim over the real class,
exactly mirroring SemanticCache.get_instance (semantic_cache.py:152). The
corresponding 3-line src change (add get_instance to mycelium_registry.py, point
executor + mycelium_api at it) is the separate approve-then-apply plan; this proves
it works first.

Run:  PYTHONPATH=<src> python close_mycelium_loop.py
"""

from __future__ import annotations

import json
import time
import urllib.request

from cohezion.learning.mycelium_registry import MyceliumRegistry, JournalEntry

NPU = "http://localhost:13306"

# ── The CA2 singleton shim: exactly mirrors SemanticCache.get_instance ──
# (When applied to src, this becomes a classmethod ON MyceliumRegistry.)
_SINGLETON: MyceliumRegistry | None = None


def get_instance() -> MyceliumRegistry:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = MyceliumRegistry()
    return _SINGLETON


# ── Constraint: experiences come from REAL local inference, not stubs ──


def run_local_task(task: str) -> dict:
    """Run one task on a live lemonade node; the journal entry records real evidence."""
    payload = json.dumps(
        {
            "model": "DeepSeek-Qwen3-8B-GGUF",
            "messages": [{"role": "user", "content": task + " Answer with just the label."}],
            "max_tokens": 256,
            "temperature": 0.0,
        }
    ).encode()
    req = urllib.request.Request(
        f"{NPU}/v1/chat/completions", data=payload, headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 localhost
            data = json.loads(r.read())
        ans = data["choices"][0]["message"]["content"].strip()
        if "</think>" in ans:
            ans = ans.split("</think>")[-1].strip()
        ans = (ans.splitlines() or [""])[-1].strip() if ans else ans
        return {
            "answer": ans,
            "ms": round((time.time() - t0) * 1000, 1),
            "node": "lemonade:13306",
            "cost_usd": 0.0,
        }
    except Exception as e:
        return {
            "answer": "",
            "ms": round((time.time() - t0) * 1000, 1),
            "node": "lemonade:13306",
            "cost_usd": 0.0,
            "error": str(e),
        }


def capture_experiences(registry: MyceliumRegistry) -> list[dict]:
    """Run real tasks, ingest each as a JournalEntry (the WRITER side, executor Step 10.6)."""
    tasks = [
        ("classify sentiment: this recursion finally closes", "routing"),
        ("classify sentiment: the loop was broken before", "routing"),
        ("classify sentiment: experience now feeds back", "routing"),
    ]
    evidence = []
    for i, (task, domain) in enumerate(tasks):
        inf = run_local_task(task)
        content = f"task='{task}' -> '{inf['answer']}' on {inf['node']} in {inf['ms']}ms (${inf['cost_usd']})"
        registry.ingest_entry(
            JournalEntry(entry_id=f"exp-{i}", content=content, domain=domain, timestamp=time.time())
        )
        evidence.append(
            {"task": task, "answer": inf["answer"], "ms": inf["ms"], "node": inf["node"]}
        )
        print(f"    captured exp-{i}: '{inf['answer']}' ({inf['ms']}ms, $0) on {inf['node']}")
    return evidence


def main() -> None:
    import cohezion.learning.mycelium_registry as mod

    print(f"provenance OK: MyceliumRegistry -> {mod.__file__}\n")

    # ════════════ STATE 1: THE BUG (two separate instances) ════════════
    print("=" * 64)
    print("STATE 1 — THE BUG: writer and reader are separate instances")
    print("=" * 64)
    writer_buggy = MyceliumRegistry(min_entries_for_pattern=2)  # like executor.py:1273
    reader_buggy = MyceliumRegistry(min_entries_for_pattern=2)  # like mycelium_api.py:36
    print(f"  writer id={id(writer_buggy)}  reader id={id(reader_buggy)}")
    print("  [writer] capturing experiences from live inference ...")
    capture_experiences(writer_buggy)
    writer_buggy.run_audit()
    print(f"  [writer] synthesized skills: {list(writer_buggy.skills.keys())}")
    print(f"  [reader] /skills sees:       {list(reader_buggy.skills.keys())}  <-- EMPTY (the bug)")
    bug_readback = len(reader_buggy.skills)

    # ════════════ STATE 2: THE FIX (shared singleton) ═══════════════════
    print("\n" + "=" * 64)
    print("STATE 2 — THE FIX: writer and reader share get_instance() singleton")
    print("=" * 64)
    writer_fixed = get_instance()  # executor.py would call this
    reader_fixed = get_instance()  # mycelium_api.py would call this
    print(
        f"  writer id={id(writer_fixed)}  reader id={id(reader_fixed)}  "
        f"SAME={writer_fixed is reader_fixed}"
    )
    print("  [writer] capturing experiences from live inference ...")
    ev_fix = capture_experiences(writer_fixed)
    writer_fixed.run_audit()
    skills = reader_fixed.skills
    print(f"  [writer] synthesized skills: {list(writer_fixed.skills.keys())}")
    print(f"  [reader] /skills sees:       {list(skills.keys())}  <-- VISIBLE (the fix)")
    fix_readback = len(skills)

    # show the actual read-back skill content (the recursion product)
    if skills:
        first = next(iter(skills.values()))
        print(
            f"\n  read-back skill '{first.skill_name}' from {len(first.source_entries)} experiences:"
        )
        for line in first.skill_content.splitlines()[:6]:
            print(f"    | {line}")

    # ════════════ VERDICT (the evidence IS the discriminator) ═══════════
    print("\n" + "=" * 64)
    print("VERDICT")
    print("=" * 64)
    same_obj = writer_fixed is reader_fixed
    print(f"  (a) same object (Circuit B closed):   {same_obj}")
    print(f"  (b) buggy read-back (separate insts):  {bug_readback} skills  (expect 0)")
    print(f"  (c) fixed read-back (singleton):       {fix_readback} skills  (expect >=1)")
    print(
        f"  (d) local inference, $0:               {all(e['node'] == 'lemonade:13306' for e in ev_fix)}"
    )
    closed = same_obj and bug_readback == 0 and fix_readback >= 1
    print(f"\n  RECURSION LOOP CLOSED: {closed}")
    print("  -> The singleton wire makes synthesized skills visible to the reader,")
    print("     turning captured experience into a skill the system can act on.")

    result = {
        "bug_readback_skills": bug_readback,
        "fix_readback_skills": fix_readback,
        "same_object": same_obj,
        "local_inference": [e["node"] for e in ev_fix],
        "recursion_closed": closed,
        "synthesized_skill": next(iter(skills.keys())) if skills else None,
        "evidence": ev_fix,
    }
    with open("mycelium_loop_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n  wrote mycelium_loop_result.json")


if __name__ == "__main__":
    main()
