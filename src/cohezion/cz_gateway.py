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
    import base64
    import math
    import urllib.request

    def _embed(text: str) -> list[float]:
        req = urllib.request.Request(
            "http://localhost:13305/v1/embeddings",
            data=json.dumps(
                {"model": "nomic-embed-text-v2-moe-GGUF", "input": text[:500]}
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return json.loads(r.read())["data"][0]["embedding"]

    def _sql(q: str) -> list:
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=q.encode(),
            headers={
                "surreal-ns": "cohezion",
                "surreal-db": "corpus",
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return json.loads(r.read())

    def _cos(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    try:
        qv = _embed(query)
        rows = _sql("SELECT title, topic, summary, embedding FROM adp_pattern;")[0]["result"]
        scored = [(_cos(qv, r["embedding"]), r) for r in rows if r.get("embedding")]
        scored.sort(key=lambda t: t[0], reverse=True)
        chunks = [
            {
                "title": r["title"],
                "topic": r["topic"],
                "summary": r["summary"],
                "score": round(s, 3),
            }
            for s, r in scored[:5]
        ]
        return {"ok": True, "chunks": chunks, "count": len(chunks)}
    except Exception as exc:  # fail-soft — vault RAG is best-effort
        return {"ok": False, "chunks": [], "count": 0, "error": str(exc)}


def journey(task: str, context: str = "") -> dict:
    """Run a task through the cascade AND capture its agentic journey in FLUME latent space.

    Surfaces the deep Cohezion substrate to cz through REAL consumers (not decoration):
      - AGENTS: the triune NPU→iGPU→CPU cascade (make_local_execute_fn)
      - WORLD MODEL: the observer world-model records the tier flow (local_inference:211)
      - FLUME VAE + LATENT SPACE: text_to_latent → nomic-backed manifold encode (LC2/G16)
      - AGENTIC JOURNEY: JourneyTracker positions the (task,output) as a trajectory point

    Fail-soft — the bridge must never crash the CLI.
    """
    try:
        import numpy as np

        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.compound.local_inference import make_local_execute_fn

        fn = make_local_execute_fn(task_description=task, context_prefix=context)
        output, metrics = fn("")  # cascade + world-model observer record fire here
        jt = JourneyTracker()
        arr = np.asarray(
            jt.text_to_latent(f"{task}\n{output}"), dtype=float
        ).ravel()  # FLUME encode
        return {
            "ok": True,
            "result": output,
            "tier": metrics.get("tier_used", "unknown"),
            "journey": {
                "flume_dim": int(arr.size),
                "flume_norm": round(float(np.linalg.norm(arr)), 4),
                "flume_head": [round(float(x), 4) for x in arr[:6].tolist()],
                "encoder": "flume/lemonade-embed"
                if jt._flume_encoder is not None
                else "hash-fallback",
            },
            "subsystems": [
                "agents:triune",
                "world-model:observer",
                "flume-vae",
                "latent-space",
                "journey-tracker",
            ],
        }
    except Exception as exc:  # fail-soft
        return {"ok": False, "result": "", "error": str(exc)}


def _main(argv: list[str]) -> dict:
    usage = {"ok": False, "error": "usage: cz_gateway {execute|rag|journey} <arg> [context]"}
    if len(argv) < 3:
        return usage
    verb, arg = argv[1], argv[2]
    if verb == "execute":
        return execute(arg, argv[3] if len(argv) > 3 else "")
    if verb == "rag":
        return rag(arg)
    if verb == "journey":
        return journey(arg, argv[3] if len(argv) > 3 else "")
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
        try:  # noqa: SIM105 — flush best-effort during fd-restore cleanup
            sys.stdout.flush()
        except Exception:
            pass
        os.dup2(_saved_fd, 1)
        os.close(_saved_fd)
    print(json.dumps(_result, default=str))
