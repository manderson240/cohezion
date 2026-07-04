#!/usr/bin/env python3
"""Daily ollama-cloud quota check.

ollama.com does NOT expose a public API for usage/quota. The only way to
get the % used is to scrape the logged-in web view at
https://ollama.com/settings/billing (or wherever the dashboard lives).

Strategy: load a session cookie (paste it once, stored in
~/.cohezion-research/secrets/ollama_session.txt with 0600 perms), then
curl the dashboard, grep the percentage, append a JSONL record with
timestamp. The user runs this once a day from cron; alerting is
done by the cron job's own output (or a wrapper that exits non-zero
when above threshold).

Falls back to a manual-paste mode if no cookie is stored.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

COOKIE_PATH = Path.home() / ".cohezion-research" / "secrets" / "ollama_session.txt"
LOG_PATH    = Path.home() / ".cohezion-research" / "logs" / "ollama_quota.jsonl"
DASHBOARD   = "https://ollama.com/settings/billing"  # fallback URL
ALT_URLS    = [
    "https://ollama.com/settings/billing",
    "https://ollama.com/settings/usage",
    "https://ollama.com/billing",
]

PCT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")

def read_cookie() -> str | None:
    if not COOKIE_PATH.exists():
        return None
    return COOKIE_PATH.read_text().strip()

def fetch_pct_with_cookie(cookie: str) -> tuple[float | None, str]:
    """Return (percent_used, raw_body_excerpt)."""
    for url in ALT_URLS:
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) cohezion-quota-check",
                "Cookie": f"ollama_session={cookie}",
                "Accept": "text/html",
            })
            with urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            m = PCT_RE.search(body)
            if m:
                return float(m.group(1)), body[:200]
        except (URLError, HTTPError):
            continue
    return None, ""

def write_log(pct: float | None, mode: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "pct_used": pct,
        "mode": mode,
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=75.0,
                    help="warn (non-zero exit) when pct_used >= threshold (default 75)")
    ap.add_argument("--setup", action="store_true",
                    help="store a session cookie for future runs (paste from browser devtools)")
    args = ap.parse_args()

    if args.setup:
        cookie = input("Paste ollama_session cookie value: ").strip()
        if not cookie:
            print("empty cookie, aborting", file=sys.stderr)
            return 1
        COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_PATH.write_text(cookie + "\n")
        os.chmod(COOKIE_PATH, 0o600)
        print(f"stored at {COOKIE_PATH} (mode 0600)")
        return 0

    cookie = read_cookie()
    if not cookie:
        print(f"No cookie at {COOKIE_PATH}.")
        print("Run: ollama_quota_check.py --setup   (paste ollama_session cookie from browser)")
        print("Or:  ollama_quota_check.py --manual  (then paste the % from the web UI)")
        return 2

    pct, excerpt = fetch_pct_with_cookie(cookie)
    if pct is None:
        print(f"could not extract % from {DASHBOARD}; cookie may be stale")
        print("excerpt:", excerpt[:160])
        write_log(None, "fetch_failed")
        return 1

    write_log(pct, "auto")
    print(f"ollama-cloud usage: {pct:.1f}%  (threshold {args.threshold:.0f}%)")
    if pct >= args.threshold:
        print(f"WARNING: above threshold. Consider local routing.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
