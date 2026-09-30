"""A real GAIA agent over the memory graph: deterministic tools, a local model, an oracle eval.

The model never sees the database; it can only call the tools below. Every question in the eval has
an answer computed directly from SurrealDB, so a wrong answer is a measured failure, and the same
questions run with tools disabled are the control (they should fail — the data is unknowable).

Usage: python scripts/ops/graph_agent.py [--n 6] [--model Qwen3.6-35B-A3B-MTP-GGUF] [--control]
Requires amd-gaia >= 0.24 (base Agent + @tool; ChatAgent/MCPAgent no longer exist).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from memory_entities import Resolver, build_resolver, surreal


BASE_URL = "http://localhost:13305/v1"
MODEL = (
    "Qwen3.6-35B-A3B-MTP-GGUF"  # ctx 32768 >= GAIA's 32768 minimum; Gemma-31B (16384) is too small
)


def who_mentions_impl(token: str, resolver: Resolver, db=surreal) -> dict:
    """Notes that mention ``token`` (file / module / skill / memory note), with counts."""
    hit = resolver.resolve(token)
    if not hit:
        return {"token": token, "resolved": False, "notes": [], "count": 0}
    from memory_entities import entity_id

    rows = db(f"SELECT in AS note FROM mem_mentions WHERE out = {entity_id(*hit)};")[0].get(
        "result", []
    )
    notes = sorted({str(r["note"]).removeprefix("memory:") for r in rows})
    return {
        "token": token,
        "resolved": True,
        "entity": hit[1],
        "count": len(notes),
        "notes": notes[:25],
    }


def entities_in_note_impl(note: str, db=surreal) -> dict:
    """Distinct entities (files, modules, skills) that one memory note mentions."""
    rid = re.sub(r"[^A-Za-z0-9_]", "_", note.strip())
    rows = db(f"SELECT out, kind FROM mem_mentions WHERE in = memory:{rid};")[0].get("result", [])
    ents = sorted({str(r["out"]) for r in rows})
    return {"note": note, "count": len(ents), "entities": [e.split(":", 1)[1] for e in ents][:25]}


def make_agent(resolver: Resolver, model: str = MODEL, with_tools: bool = True):
    from gaia.agents.base.agent import Agent
    from gaia.agents.base.tools import tool

    class GraphAgent(Agent):
        def _get_system_prompt(self) -> str:
            return (
                "You answer questions about a memory-note graph. The data is only reachable through "
                "your tools; never guess. Give a short final answer that states the number or the "
                "note name asked for."
            )

        def _register_tools(self) -> None:
            if not with_tools:
                return

            @tool
            def who_mentions(token: str) -> dict:
                """List the memory notes that mention a file, module or skill (e.g. 'hotswap.py')."""
                return who_mentions_impl(token, resolver)

            @tool
            def entities_in_note(note: str) -> dict:
                """List the files/modules/skills that one memory note mentions (note = its file stem)."""
                return entities_in_note_impl(note)

    return GraphAgent(
        base_url=BASE_URL, model_id=model, skip_lemonade=True, silent_mode=True, max_steps=6
    )


def build_questions(n: int, resolver: Resolver, db=surreal) -> list[dict]:
    """Oracle questions computed straight from the graph (deterministic, no LLM)."""
    canon = {
        str(r["id"]).split(":", 1)[1]: r["canonical"]
        for r in db("SELECT id, canonical, kind FROM graph_entity WHERE kind = 'file';")[0][
            "result"
        ]
    }
    rows = db("SELECT out, in FROM mem_mentions;")[0]["result"]
    by_ent: dict[str, set[str]] = {}
    by_note: dict[str, set[str]] = {}
    for r in rows:
        ent, note = str(r["out"]).split(":", 1)[1], str(r["in"]).removeprefix("memory:")
        by_ent.setdefault(ent, set()).add(note)
        by_note.setdefault(note, set()).add(ent)
    counts, notes = [], []
    for ent, ms in sorted(by_ent.items()):
        token = Path(canon[ent]).name if ent in canon else None
        if token and 2 <= len(ms) <= 12 and resolver.resolve(token) == ("file", canon[ent]):
            counts.append(
                {
                    "kind": "count",
                    "q": f"How many memory notes mention `{token}`?",
                    "expected": {str(len(ms))},
                }
            )
    for note, es in sorted(by_note.items()):
        if 2 <= len(es) <= 10:
            q = f"How many distinct files, modules or skills does the memory note `{note}` mention?"
            notes.append({"kind": "note", "q": q, "expected": {str(len(es))}})
    half = max(1, n // 2)
    return counts[:half] + notes[: n - half]


def score(answer: str, expected: set[str]) -> bool:
    """True iff the answer states an expected value as a standalone token (no substring luck)."""
    return any(re.search(rf"(?<![\w.]){re.escape(e)}(?![\w])", answer) for e in expected)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--control", action="store_true", help="run WITHOUT tools (must fail)")
    args = ap.parse_args(argv)
    resolver = build_resolver()
    qs = build_questions(args.n, resolver)
    agent = make_agent(resolver, args.model, with_tools=not args.control)
    ok = 0
    for q in qs:
        t = time.time()
        try:
            res = agent.process_query(q["q"])
            answer = str(res.get("result") or res.get("answer") or res)
        except Exception as exc:
            answer = f"ERROR {type(exc).__name__}: {exc}"
        used = len(getattr(agent, "_turn_tool_executions", []) or [])
        good = score(answer, q["expected"])
        ok += good
        print(
            f"{'PASS' if good else 'FAIL'} [{q['kind']}] tools={used} {time.time() - t:.0f}s expected={sorted(q['expected'])} :: {q['q'][:60]} -> {answer[:90]!r}",
            flush=True,
        )
    print(
        f"RESULT {'control (no tools)' if args.control else 'with tools'}: {ok}/{len(qs)} correct  model={args.model}"
    )
    print(json.dumps({"ok": ok, "n": len(qs), "control": args.control}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
