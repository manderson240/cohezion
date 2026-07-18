"""Blessed Ollama Cloud client — the harnessed path for strategic cloud calls.

Cloud tokens are the METERED resource (Silicon Doctrine law 0): every call is
logged to a usage ledger so spend is visible, and callers should batch with
user-approved budgets. Local models stay the default; escalate to cloud only
when the task genuinely clears the feynman-weight bar (CC2) or a local lane is
blocked (e.g. graphify extraction pending the lemonade no-think profile).

Encodes the 2026-07-17 lessons so no call site re-learns them:
  - Use the OLLAMA HTTP API, never CLI capture (the CLI's thinking-stream TTY
    rendering garbles stdout beyond parsing).
  - Ollama honors per-request ``think: false`` (unlike lemonade, issue #1511) —
    default it off; enable only for genuinely hard multi-step work.
  - ``extract_json`` handles fenced / think-wrapped / plain JSON responses.
  - Never raises on transport errors — returns "" (keeps batch loops alive),
    mirroring the gauntlet ``_call_model`` contract.

Sibling of ``cohezion.inference.gauntlet._call_model`` (the blessed LOCAL
path); both are named in scripts/ci/check_local_llm_chokepoint.sh.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from pathlib import Path


logger = logging.getLogger(__name__)

OLLAMA_API = "http://localhost:11434/api/chat"
USAGE_LEDGER = Path.home() / ".cohezion" / "ollama_cloud_usage.jsonl"
DEFAULT_MODEL = "deepseek-v4-pro:cloud"

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def cloud_chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    think: bool = False,
    timeout_s: float = 300.0,
    purpose: str = "unspecified",
) -> str:
    """One chat completion against an Ollama Cloud model. Returns "" on error.

    ``purpose`` is recorded in the usage ledger — future budget reviews group
    spend by it, so name the workload (e.g. "graphify-extraction").
    """
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": think,
        }
    ).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(  # noqa: S310
            OLLAMA_API, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as r:  # noqa: S310
            d = json.load(r)
        text = str(d.get("message", {}).get("content", "") or "")
        _log_usage(model, purpose, prompt, text, d, time.time() - t0)
        return text
    except Exception as exc:
        logger.warning("ollama cloud_chat(%s) failed: %s", model, exc)
        _log_usage(model, purpose, prompt, "", {"error": str(exc)[:200]}, time.time() - t0)
        return ""


def extract_json(text: str) -> dict | None:
    """Parse a JSON object from a model response: fenced first, think-stripped,
    then widest brace slice. None if nothing parses (record as unparseable —
    never silently coerce; Minerva outcome discipline)."""
    t = _THINK_RE.sub("", text or "")
    for cand in [*_FENCE_RE.findall(t), t]:
        s = cand[cand.find("{") : cand.rfind("}") + 1]
        if not s:
            continue
        try:
            obj = json.loads(s)
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _log_usage(model: str, purpose: str, prompt: str, text: str, resp: dict, dur: float) -> None:
    try:
        USAGE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LEDGER.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "model": model,
                        "purpose": purpose,
                        "prompt_chars": len(prompt),
                        "response_chars": len(text),
                        "eval_count": resp.get("eval_count"),
                        "prompt_eval_count": resp.get("prompt_eval_count"),
                        "duration_s": round(dur, 1),
                        "error": resp.get("error"),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
