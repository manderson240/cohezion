"""Full state awareness for Cohezion compound engineering system.

Single function that returns complete system state — silicon, AUTODQA, autoresearch,
fractal health — suitable for post-compact hook injection, Telegram reports,
SurrealDB persistence, and cron job prompts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# N1: :13305 is the only inference port. The per-device servers (:13306 NPU,
# :13307 iGPU, :13309 CPU) are offline and redundant — probing them reports every
# device down regardless of true occupancy.
_OMNIROUTER_PORT = 13305
_PROBE_TIMEOUT_S = 8.0


def get_full_state() -> dict[str, object]:
    """Return complete Cohezion system state.

    All sub-queries are fail-safe: missing modules or offline services
    return None/False rather than raising exceptions.
    """
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "silicon": _silicon_state(),
        "autodqa": _autodqa_state(),
        "autoresearch": _autoresearch_state(),
        "lemonade": _lemonade_state(),
        "tokens": _token_state(),
    }


def format_state_for_context(state: dict[str, object] | None = None) -> str:
    """Format state as compact text suitable for post-compact hook injection."""
    s = state or get_full_state()
    si = s.get("silicon", {})
    dqa = s.get("autodqa", {})
    ar = s.get("autoresearch", {})

    tok = s.get("tokens", {})
    lines = [
        f"[state] Silicon: NPU={'UP' if si.get('npu_up') else 'DOWN'} | iGPU={'UP' if si.get('igpu_up') else 'DOWN'}",
        f"[state] AUTODQA: {dqa.get('session_results', 0)} evals | accept={dqa.get('accept_rate', 0.0):.0%} | FD={dqa.get('fd', '?')}",
        f"[state] Autoresearch: {ar.get('total_runs', 0)} runs | segment={ar.get('segment', '?')}",
        f"[state] Tokens: local={tok.get('local_tokens', 0):,} | cloud_cost=${tok.get('cloud_cost_usd', 0.0):.4f} | savings=${tok.get('cloud_savings_usd', 0.0):.4f}",
    ]
    return "\n".join(lines)


def _run_sync(coro: Any) -> Any:
    """Await ``coro`` from sync code, whether or not a loop is already running.

    ``_silicon_state`` is called from hooks, cron prompts and Telegram reports — some
    inside a running loop, some not. ``asyncio.run`` raises in the former case, so fall
    back to a dedicated thread with its own loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}

    def _worker() -> None:
        result["value"] = asyncio.run(coro)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=_PROBE_TIMEOUT_S)
    return result.get("value")


def _silicon_state() -> dict[str, object]:
    """Device occupancy for the tri-device fleet, read from the :13305 oracle.

    Reads ``lemonade_health.probe_lemonade`` — the single verified source of fleet
    truth — rather than probing per-device ports. :13306/:13307 are offline under
    invariant N1, so the previous direct-probe implementation reported every device
    down unconditionally while the NPU and iGPU were both serving models.

    ``probe_ok`` distinguishes "I could not ask" from "nothing is running"; failing
    closed to empty occupancy makes those two states indistinguishable and silently
    degrades every downstream gate.
    """
    unknown: dict[str, object] = {
        "npu_up": False,
        "igpu_up": False,
        "npu_models": [],
        "igpu_models": 0,
        "probe_ok": False,
    }
    try:
        from cohezion.inference import lemonade_health

        health = _run_sync(lemonade_health.probe_lemonade(port=_OMNIROUTER_PORT))
    except Exception as exc:
        logger.debug("silicon_state probe failed: %s", exc)
        return unknown

    if health is None or not getattr(health, "reachable", False):
        return unknown

    return {
        "npu_up": health.npu_up,
        "igpu_up": health.igpu_up,
        "npu_models": health.npu_models,
        "igpu_models": len(health.igpu_models),
        "probe_ok": True,
    }


def _autodqa_state() -> dict[str, object]:
    try:
        # Try to access a module-level AutoDQA instance if one was registered
        import sys

        from cohezion.compound.autodqa import AutoDQA  # noqa: F401

        dqa_mod = sys.modules.get("cohezion.compound.autodqa")
        if dqa_mod and hasattr(dqa_mod, "_session_dqa"):
            dqa = dqa_mod._session_dqa
            summary = dqa.session_summary()
            health = dqa.fractal_health()
            return {
                "session_results": summary.get("total", 0),
                "accept_rate": summary.get("accept_rate", 0.0),
                "fd": health.get("fd"),
                "hiho_engaged": health.get("hiho_engaged"),
                "interpretation": health.get("interpretation", ""),
            }
    except Exception as exc:
        logger.debug("autodqa_state failed: %s", exc)
    return {"session_results": 0, "accept_rate": 0.0, "fd": None, "hiho_engaged": None}


def _autoresearch_state() -> dict[str, object]:
    try:
        ar_path = Path("/home/mike-anderson/dev/cohezion/autoresearch.jsonl")
        if not ar_path.exists():
            return {"total_runs": 0, "segment": None}
        lines = ar_path.read_text().splitlines()
        valid = [l for l in lines if l.strip()]
        last = json.loads(valid[-1]) if valid else {}
        return {
            "total_runs": len(valid),
            "segment": last.get("segment"),
            "last_run": last.get("run"),
        }
    except Exception as exc:
        logger.debug("autoresearch_state failed: %s", exc)
        return {"total_runs": 0, "segment": None}


def _token_state() -> dict[str, object]:
    """Return session token usage from the singleton TokenUsageRecord."""
    try:
        from cohezion.compound.local_inference import get_session_token_record

        r = get_session_token_record()
        return {
            "local_tokens": r.local_tokens,
            "cloud_tokens_input": r.cloud_tokens_input,
            "cloud_tokens_output": r.cloud_tokens_output,
            "cloud_cost_usd": round(r.cloud_cost_usd, 6),
            "cloud_savings_usd": round(r.cloud_savings_usd, 4),
            "local_fraction": round(r.local_fraction, 3),
            "total_tokens": r.total_tokens,
        }
    except Exception as exc:
        logger.debug("token_state failed: %s", exc)
        return {"local_tokens": 0, "cloud_cost_usd": 0.0, "cloud_savings_usd": 0.0}


def _lemonade_state() -> dict[str, object]:
    try:
        from cohezion.compound.local_inference import lemonade_available

        return {
            "available": lemonade_available(),
            "npu_ttft_ms_nominal": 24,
            "igpu_ttft_ms_nominal": 200,
        }
    except Exception:
        return {"available": False}
