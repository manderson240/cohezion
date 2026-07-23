"""cz ⇄ Cohezion gateway — a subprocess-callable JSON bridge.

Lets the lightweight `cz` CLI drive Cohezion's AMD-optimized GAIA triune cascade
(NPU→iGPU→CPU via :13305) and vault RAG **without importing torch** into cz: cz
subprocesses ``<repo>/.venv/bin/python -m cohezion.cz_gateway {execute|rag} <arg> [ctx]``
and reads the single JSON line printed to stdout.

(Named cz_gateway to avoid the existing ``cohezion.gateway`` package.)

STDOUT HYGIENE: logging is routed to stderr at import, so cohezion's noisy import-time
logs never pollute the JSON. The only stdout write is the final ``json.dumps(result)``.

Drafted by the local Coder (Qwen3-Coder-30B), hardened + verified on integration.
"""

from __future__ import annotations

import json
import logging
import sys

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)


def execute(task: str, context: str = "") -> dict:
    """Run a task through the AMD-optimized triune cascade (NPU→iGPU→CPU). Fail-soft."""
    try:
        from cohezion.compound.local_inference import make_local_execute_fn

        fn = make_local_execute_fn(task_description=task, context_prefix=context)
        output, metrics = fn("")  # execute_fn(guidance: str) -> tuple[str, dict]
        return {
            "ok": True,
            "result": output,
            "tier": metrics.get("tier_used", "unknown"),
            "metrics": metrics,
        }
    except Exception as exc:  # fail-soft — the bridge must never crash the CLI
        return {"ok": False, "result": "", "tier": "error", "error": str(exc)}


def rag(query: str) -> dict:
    """Best-effort vault RAG grounding. Fail-soft to empty chunks."""
    try:
        from cohezion.core.context_engineering import ContextEngineeringInfrastructure

        infra = ContextEngineeringInfrastructure()
        for meth in ("find_relevant_context", "retrieve", "search"):
            f = getattr(infra, meth, None)
            if callable(f):
                res = f(query)
                chunks = res if isinstance(res, list) else [res]
                return {"ok": True, "chunks": chunks, "count": len(chunks)}
        return {"ok": False, "chunks": [], "count": 0, "error": "no retrieval method found"}
    except Exception as exc:
        return {"ok": False, "chunks": [], "count": 0, "error": str(exc)}


def _main(argv: list[str]) -> dict:
    usage = {"ok": False, "error": "usage: cz_gateway {execute|rag} <arg> [context]"}
    if len(argv) < 3:
        return usage
    verb, arg = argv[1], argv[2]
    if verb == "execute":
        return execute(arg, argv[3] if len(argv) > 3 else "")
    if verb == "rag":
        return rag(arg)
    return usage


if __name__ == "__main__":
    import os

    # Bulletproof stdout hygiene: redirect fd 1 → fd 2 during the noisy cohezion
    # import + execution (kaggle/dotenv print to stdout, cohezion installs its own
    # stdout log handler — neither respects basicConfig). Only the final JSON line
    # reaches the real stdout, so cz can parse it.
    _saved_fd = os.dup(1)
    os.dup2(2, 1)
    try:
        _result = _main(sys.argv)
    finally:
        try:
            sys.stdout.flush()
        except Exception:
            pass
        os.dup2(_saved_fd, 1)
        os.close(_saved_fd)
    print(json.dumps(_result, default=str))
