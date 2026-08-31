#!/usr/bin/env python3
"""Retrieval + Ollama-Cloud reasoning harness for the CAPELLA component hunt.

Reuses the existing durability and output-contract layers rather than re-implementing them:
  - durable_swarm_output.DurableRun  -> per-lane atomic writes onto ZFS (never tmpfs)
  - swarm_harness.extract / CONTRACT -> ===FINAL=== marker contract + rejection reasons

What is NEW here and not available elsewhere in the repo:
  1. cloud()  - an Ollama Cloud caller (swarm_harness speaks to lemonade, not :11434)
  2. cdx()    - Wayback CDX lookup that runs its OWN control query every call
  3. archived() - fetch a capture and strip it to text

Run `python scripts/capella_probe.py --self-test` first. The self-test is discriminating:
each check is proven able to FAIL before any of them is trusted.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from durable_swarm_output import DurableRun  # noqa: E402
from swarm_harness import CONTRACT, extract  # noqa: E402

OLLAMA = "http://localhost:11434/api/chat"
CDX = "http://web.archive.org/cdx/search/cdx"

# Verified on the included plan 2026-08-19. kimi-k3:cloud returns HTTP 402 (paid extra usage).
CLOUD_MODELS = (
    "qwen3.5:397b-cloud",  # frontier tier - hard reasoning / adjudication
    "glm-5.2:cloud",
    "deepseek-v4-flash:cloud",
    "gpt-oss:120b-cloud",
    "gemma4:31b-cloud",
    "minimax-m3:cloud",
)
BLOCKED_MODELS = ("kimi-k3:cloud",)  # 402: do not call, do not add funds

UA = "Mozilla/5.0 (X11; Linux x86_64)"


def _get(url: str, timeout: int = 60) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except Exception as e:  # noqa: BLE001 - network shapes vary; caller decides
        return 0, str(e).encode()


def cdx(url_pattern: str, limit: int = 20) -> dict:
    """Wayback CDX lookup. ALWAYS runs a control; a negative without a passing control is UNKNOWN.

    Returns {"captures": [...], "control_ok": bool, "verdict": "found"|"absent"|"instrument-failed"}
    """

    def _q(u: str, lim: int) -> list[dict]:
        q = f"{CDX}?url={urllib.parse.quote(u, safe='')}&output=json&collapse=digest&limit={lim}"
        code, body = _get(q)
        if code != 200 or not body.strip():
            return []
        try:
            rows = json.loads(body)
        except json.JSONDecodeError:
            return []
        if not rows or len(rows) < 2:
            return []
        return [dict(zip(rows[0], r)) for r in rows[1:]]

    caps = _q(url_pattern, limit)
    # Control: a URL that MUST have captures. If this is empty, the instrument is down.
    control = _q("example.com", 3)
    ok = bool(control)
    if not ok:
        verdict = "instrument-failed"
    elif caps:
        verdict = "found"
    else:
        verdict = "absent"
    return {
        "captures": caps,
        "control_ok": ok,
        "verdict": verdict,
        "queried": url_pattern,
        "n": len(caps),
    }


def archived(timestamp: str, url: str, limit_chars: int = 40000) -> str:
    """Fetch one Wayback capture and strip to text. Returns '' on failure (caller must not
    treat '' as 'the page was empty' - check the HTTP path via cdx() first)."""
    code, body = _get(f"http://web.archive.org/web/{timestamp}/{url}", timeout=90)
    if code != 200 or not body:
        return ""
    h = body.decode("utf-8", errors="replace")
    h = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<(p|div|h[1-6]|li|br|tr)[^>]*>", "\n", h)
    t = re.sub(r"(?s)<[^>]+>", " ", h)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#39;", "'")):
        t = t.replace(a, b)
    t = re.sub(r"[ \t]+", " ", t)
    t = "\n".join(ln.strip() for ln in t.split("\n") if len(ln.strip()) > 2)
    return t[:limit_chars]


def cloud(
    prompt: str,
    model: str = CLOUD_MODELS[0],
    *,
    required_fields: tuple[str, ...] = (),
    timeout: int = 600,
) -> dict:
    """Call an Ollama Cloud model under the ===FINAL=== output contract.

    Returns {"model","answer","rejected","raw_len","http"}. `rejected` carries a SPECIFIC
    reason (empty / no-marker / too-short / missing-fields / deliberation-leaked / http-NNN).
    """
    if model in BLOCKED_MODELS:
        return {
            "model": model,
            "answer": "",
            "rejected": "model-blocked-402",
            "raw_len": 0,
            "http": 402,
        }
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt + CONTRACT}],
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read()).get("error", "")[:80]
        except Exception:  # noqa: BLE001
            pass
        return {
            "model": model,
            "answer": "",
            "rejected": f"http-{e.code} {detail}",
            "raw_len": 0,
            "http": e.code,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "model": model,
            "answer": "",
            "rejected": f"transport {type(e).__name__}",
            "raw_len": 0,
            "http": 0,
        }
    text = (d.get("message") or {}).get("content") or ""
    answer, reason = extract(text, required_fields)
    return {"model": model, "answer": answer, "rejected": reason, "raw_len": len(text), "http": 200}


def self_test() -> None:
    """Discriminating: every check is shown able to FAIL before it is trusted."""
    fails: list[str] = []

    # 1. extract() must REJECT unmarked output, and ACCEPT marked output.
    bad, reason = extract("here is my reasoning with no marker at all")
    if bad or not reason:
        fails.append("extract accepted unmarked text (gate cannot fail -> worthless)")
    good, reason2 = extract("thinking...\n===FINAL===\n" + ("x" * 400))
    if not good or reason2:
        fails.append(f"extract rejected valid marked output: {reason2}")

    # 2. required_fields must actually be enforced.
    _, r3 = extract("===FINAL===\n" + ("y" * 400), required_fields=("TIER",))
    if "missing-required-fields" not in r3:
        fails.append("required_fields not enforced")

    # 3. cdx() control must pass, and a nonsense URL must come back 'absent' NOT 'found'.
    probe = cdx("example.com", 3)
    if not probe["control_ok"]:
        fails.append("cdx control failed -> archive instrument is down, negatives are UNKNOWN")
    nonsense = cdx("nonexistent-domain-zzq7x4.invalid/nothing", 3)
    if nonsense["verdict"] == "found":
        fails.append("cdx reports captures for a nonsense URL (cannot distinguish absent)")

    # 4. blocked model must be refused without a network call.
    b = cloud("hi", model="kimi-k3:cloud")
    if b["rejected"] != "model-blocked-402":
        fails.append("blocked model was not refused")

    print("SELF-TEST:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  !!", f)
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        print(__doc__)
        print("models:", ", ".join(CLOUD_MODELS))
        print("blocked:", ", ".join(BLOCKED_MODELS))
        print("DurableRun root:", DurableRun("probe-noop").dir.parent)
