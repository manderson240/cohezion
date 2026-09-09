"""Does a lane hide its reasoning in a separate channel? If so, char-based cost metrics lie.

WHY THIS EXISTS (2026-08-16): lane_termination_benchmark.py measures cost in CHARACTERS of the
text the adapter returns. That is `message.content`. Some models also return
`message.reasoning_content` -- a separate field holding the chain of thought -- which the adapter
DROPS. For those lanes every char-based column measures post-strip output and is not comparable
to a lane that emits its reasoning inline.

The symptom that exposed it: Nemotron-3-Nano-30B took 13.3s to return 173 chars at
max_tokens=4000, but 8.0s to return 2209 chars at max_tokens=512 -- same prompt, same warm model.
A larger cap cannot slow generation down. It was generating far more than it returned.

`usage.completion_tokens` is the honest measure: the backend counts every token generated,
reasoning included, and it cannot be stripped. This probe reports it next to the visible
character count so the gap is explicit.

Reads:
  gen_tokens      usage.completion_tokens -- TRUE generation volume, the real cost
  visible_chars   len(message.content) -- what the caller actually receives
  hidden_chars    len(message.reasoning_content) -- dropped by the adapter, still paid for
  hidden_frac     hidden / (hidden + visible), by character. >0 means char metrics understate
                  this lane's cost and it must not be char-compared against an inline lane.

Only probes RESIDENT models by default: loading evicts peers and this box hard-hung twice on
2026-08-15. Pass --load to opt into loading, one at a time, checking memory between.

Usage:
  .venv/bin/python scripts/experiments/reasoning_channel_probe.py --models gpt-oss-20b,...
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


ENDPOINT = "http://localhost:13305/api/v1/chat/completions"

# Evaluative, matching the termination benchmark's prompt class: reasoning models only diverge
# from non-reasoning ones on judgement, so a factual prompt would show no hidden channel at all.
PROMPT = (
    "A team proposes replacing a well-tested 200-line module with a 40-line rewrite that passes "
    "the same test suite. The tests were written against the OLD module's behaviour. Is passing "
    "the existing suite sufficient evidence that the rewrite is safe? Argue one side in two "
    "sentences."
)


def _guarded(model: str) -> bool:
    """Would build_gaia_llm_tier send this model reasoning_format="none"?

    Imported from the adapter rather than reimplemented: a local copy of the marker tuple would
    silently drift from the one that actually decides, which is the exact failure this probe
    exists to detect. Falls back to None-ish False if the import is unavailable.
    """
    try:
        sys.path.insert(0, "src")
        from cohezion.inference.gaia_adapter import _is_llamacpp_thinking_model
        return bool(_is_llamacpp_thinking_model(model))
    except Exception:  # probe must survive an unimportable adapter
        return False


def probe(model: str, max_tokens: int, timeout: int) -> dict:
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": PROMPT}],
    }).encode()
    # S310: ENDPOINT is a module-level http:// localhost constant, never caller-supplied, so
    # there is no file:/custom-scheme surface for a URL audit to protect against.
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            d = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        # A dead lane is a RESULT, not an abort -- the point is to survey the roster.
        return {"model": model, "error": f"{type(exc).__name__}",
                "secs": round(time.time() - t0, 1)}

    msg = d.get("choices", [{}])[0].get("message", {}) or {}
    # NOTE: this probe hits the server DIRECTLY, so it sees the split channel even for models
    # the adapter would have guarded -- reasoning_format="none" is applied by build_gaia_llm_tier,
    # not by the server. A raw hidden_frac is therefore NOT evidence that the benchmark
    # mismeasured that lane; only an UNGUARDED lane is mismeasured. Reporting the guard status
    # alongside is the whole point: reading raw hidden_frac as "the benchmark missed this" cost a
    # wrong hypothesis on 2026-08-16.
    visible = msg.get("content") or ""
    hidden = msg.get("reasoning_content") or msg.get("reasoning") or ""
    gen = (d.get("usage") or {}).get("completion_tokens", 0)
    total_chars = len(visible) + len(hidden)
    return {
        "model": model,
        "guarded": _guarded(model),
        "secs": round(time.time() - t0, 1),
        "gen_tokens": gen,
        "visible_chars": len(visible),
        "hidden_chars": len(hidden),
        "hidden_frac": round(len(hidden) / total_chars, 2) if total_chars else 0.0,
        # ~4 chars/token on this fleet. If the backend generated far more tokens than the
        # returned text accounts for, reasoning is hidden somewhere this probe cannot see
        # either -- a stronger warning than a populated reasoning_content field.
        "unaccounted_tokens": max(0, gen - round(total_chars / 4)),
        "error": "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="comma-separated; RESIDENT models only")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"{'model':<32} {'guard':>6} {'secs':>6} {'gen_tok':>8} {'visible':>8} {'hidden':>7} "
          f"{'hid_frac':>9}")
    print("-" * 84)
    verdicts = []
    for m in models:
        r = probe(m, args.max_tokens, args.timeout)
        if r.get("error"):
            print(f"{m:<32} {'-':>6} {r['secs']:>6} {'-':>8} {'-':>8} {'-':>7} {'-':>9}  "
                  f"{r['error']}")
            continue
        print(f"{m:<32} {('yes' if r['guarded'] else 'NO'):>6} {r['secs']:>6} "
              f"{r['gen_tokens']:>8} {r['visible_chars']:>8} {r['hidden_chars']:>7} "
              f"{r['hidden_frac']:>9.2f}")
        verdicts.append(r)

    print()
    # The actionable set is UNGUARDED lanes that actually stream to a hidden channel. A guarded
    # lane shows a hidden channel here too (this probe bypasses the adapter) but is measured
    # correctly by the benchmark, so flagging it would be a false positive.
    at_risk = [r for r in verdicts
               if not r["guarded"] and (r["hidden_chars"] > 0 or r["unaccounted_tokens"] > 50)]
    if at_risk:
        print("MISMEASURED LANES -- reasoning model NOT covered by _THINKING_MODEL_MARKERS:")
        for r in at_risk:
            print(f"  {r['model']}: {r['hidden_chars']} chars stream to reasoning_content and "
                  f"are DROPPED by the adapter (gaia_adapter.py:269)")
        print("Consequences: (1) char-based cost columns understate these lanes and must not be")
        print("    compared against guarded ones -- use usage.completion_tokens (gen_tok);")
        print("(2) defect 4dd925b0081f is live for them -- a structured prompt at a low budget")
        print("    returns raw chain-of-thought instead of the answer. See kanban t_903e8d2e.")
    else:
        print("No UNGUARDED lane streams to a hidden channel. Char-based cost columns are")
        print("comparable across the probed set (guarded lanes keep reasoning inline).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
