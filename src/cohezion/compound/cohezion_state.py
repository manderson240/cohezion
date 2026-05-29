"""Full state awareness for Cohezion compound engineering system.

Single function that returns complete system state — silicon, AUTODQA, autoresearch,
fractal health — suitable for post-compact hook injection, Telegram reports,
SurrealDB persistence, and cron job prompts.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path


logger = logging.getLogger(__name__)


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


def _silicon_state() -> dict[str, object]:
    try:
        import httpx

        npu_up = _probe_lemonade(13306, httpx)
        igpu_up = _probe_lemonade(13307, httpx)
        igpu_models = _count_models(13307, httpx)
        npu_models = _list_flm_models(13306, httpx)
    except Exception as exc:
        logger.debug("silicon_state probe failed: %s", exc)
        return {"npu_up": False, "igpu_up": False, "igpu_models": 0, "npu_models": []}

    return {
        "npu_up": npu_up,
        "igpu_up": igpu_up,
        "npu_models": npu_models,
        "igpu_models": igpu_models,
    }


def _probe_lemonade(port: int, httpx_module: object) -> bool:
    try:
        resp = httpx_module.get(f"http://localhost:{port}/v1/models", timeout=1.5)
        return resp.status_code == 200
    except Exception:
        return False


def _count_models(port: int, httpx_module: object) -> int:
    try:
        resp = httpx_module.get(f"http://localhost:{port}/v1/models", timeout=1.5)
        return len(resp.json().get("data", []))
    except Exception:
        return 0


def _list_flm_models(port: int, httpx_module: object) -> list[str]:
    try:
        resp = httpx_module.get(f"http://localhost:{port}/v1/models", timeout=1.5)
        return [m["id"] for m in resp.json().get("data", []) if "FLM" in m.get("id", "")]
    except Exception:
        return []


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
