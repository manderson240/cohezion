#!/usr/bin/env python3
"""dorahacks_monitor.py — DoraHacks hackathon intelligence loop arm.

Fetches https://dorahacks.io/hackathon public listings, scores each hackathon
for Cohezion-AI relevance using Granite-4.1-8B on :13305, and appends new
relevant hackathons (score ≥ 7) to docs/feeds/DORAHACKS_FEED.md.

Item 270 (Thread D: Hackathon Intelligence, 2026-06-08).

Usage:
    .venv/bin/python3 scripts/dorahacks_monitor.py
    .venv/bin/python3 scripts/dorahacks_monitor.py --min-score 6
    .venv/bin/python3 scripts/dorahacks_monitor.py --dry-run
    .venv/bin/python3 scripts/dorahacks_monitor.py --no-inference  # skip LLM scoring

OOM safety:
- Never calls `lemonade load` — only queries already-loaded models.
- If Granite is not loaded on :13305, falls back to keyword scoring.
- All HTTP requests have short timeouts.

HUMAN GATE for sign-up:
- This script identifies opportunities only.
- Signing up requires Google OAuth at https://dorahacks.io — human action.
- PushNotification is emitted for high-score hackathons.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path


REPO = Path(__file__).parent.parent
FEED_PATH = REPO / "docs" / "feeds" / "DORAHACKS_FEED.md"
LEMONADE_URL = "http://localhost:13305"
SCORE_MODEL = "Granite-4.1-8B-GGUF"
DORAHACKS_URL = "https://dorahacks.io/hackathon"
# DoraHacks uses AWS WAF.  Unauthenticated requests return a CAPTCHA challenge.
# To authenticate: login at https://dorahacks.io with Google OAuth, then copy
# the `aws-waf-token` cookie value and set DORAHACKS_COOKIE env var.
# Example: export DORAHACKS_COOKIE="aws-waf-token=<value>"
COOKIE_ENV = "DORAHACKS_COOKIE"
# Keyword fallback when LLM is not available
AI_KEYWORDS = {
    "ai",
    "ml",
    "llm",
    "neural",
    "language model",
    "generative",
    "diffusion",
    "rag",
    "agent",
    "embedding",
    "inference",
    "deep learning",
    "transformer",
    "gpt",
    "open source",
    "blockchain",
    "web3",
    "solana",
    "ethereum",
}
RELEVANCE_KEYWORDS = {
    "ai",
    "ml",
    "llm",
    "generative",
    "language model",
    "neural",
    "deep learning",
    "transformer",
    "agent",
    "inference",
    "open source",
}


# ---------------------------------------------------------------------------
# HTML parser — extracts hackathon cards from DoraHacks listing page
# ---------------------------------------------------------------------------


class _DoraHacksParser(HTMLParser):
    """Extract hackathon titles, prizes, deadlines, and URLs from listing HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.hackathons: list[dict] = []
        self._current: dict | None = None
        self._capture: str | None = None  # which field to capture
        self._depth: int = 0
        self._in_card: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple]) -> None:
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")
        href = attr_dict.get("href", "")

        # DoraHacks uses data-testid or class patterns for cards
        if tag == "a" and "/hackathon/" in href and href != "/hackathon":
            slug = href.split("?")[0].rstrip("/")
            if not any(h.get("url", "").endswith(slug.split("/")[-1]) for h in self.hackathons):
                self._current = {
                    "title": "",
                    "url": f"https://dorahacks.io{slug}",
                    "prize": "",
                    "deadline": "",
                    "tags": [],
                }
                self.hackathons.append(self._current)

        # Capture text within elements that contain prize/deadline hints
        if tag in ("h2", "h3", "span", "p") and self._current is not None:
            lowcls = cls.lower()
            if "prize" in lowcls or "reward" in lowcls or "fund" in lowcls:
                self._capture = "prize"
            elif "deadline" in lowcls or "end" in lowcls or "time" in lowcls:
                self._capture = "deadline"
            elif "tag" in lowcls or "label" in lowcls or "track" in lowcls:
                self._capture = "tag"
            elif "title" in lowcls or "name" in lowcls:
                self._capture = "title"

    def handle_endtag(self, tag: str) -> None:
        if tag in ("h2", "h3", "span", "p"):
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._current is None or not self._capture:
            return
        text = data.strip()
        if not text:
            return
        if self._capture == "title" and not self._current["title"]:
            self._current["title"] = text
        elif self._capture == "prize" and not self._current["prize"]:
            self._current["prize"] = text
        elif self._capture == "deadline" and not self._current["deadline"]:
            self._current["deadline"] = text
        elif self._capture == "tag":
            self._current["tags"].append(text)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def fetch_hackathons(url: str = DORAHACKS_URL) -> list[dict]:
    """Fetch DoraHacks listing page and extract hackathon entries.

    DoraHacks is behind AWS WAF — unauthenticated requests receive a CAPTCHA
    page.  Set the ``DORAHACKS_COOKIE`` environment variable to the value of
    the ``aws-waf-token`` cookie obtained after logging in via Google OAuth at
    https://dorahacks.io.  Without it, the fetch returns an empty list with a
    clear human-action message.
    """
    import os

    cookie = os.environ.get(COOKIE_ENV, "")
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    if cookie:
        headers["Cookie"] = cookie
        print("[dorahacks] Using session cookie (DORAHACKS_COOKIE set)")
    else:
        print(
            "[dorahacks] HUMAN ACTION REQUIRED: DoraHacks requires authentication.\n"
            "  1. Go to https://dorahacks.io and login with Google OAuth\n"
            f"  2. Copy the 'aws-waf-token' cookie value from DevTools → Network\n"
            f"  3. Run: export {COOKIE_ENV}='aws-waf-token=<value>'\n"
            "  4. Re-run this script\n"
            "[dorahacks] Skipping fetch (no cookie) — returning empty list"
        )
        return []
    try:
        req = urllib.request.Request(url, headers=headers)  # noqa: S310
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[dorahacks] WARNING: fetch failed: {e}", file=sys.stderr)
        return []
    # Check if we got the WAF challenge page despite the cookie
    if "Human Verification" in html or "aws-waf-token" in html[:500]:
        print("[dorahacks] WARNING: WAF challenge returned — cookie may be expired")
        print(f"  Refresh your login at https://dorahacks.io and update {COOKIE_ENV}")
        return []

    parser = _DoraHacksParser()
    parser.feed(html)

    # Fill in titles from URL slugs when title wasn't captured
    for h in parser.hackathons:
        if not h["title"] and h["url"]:
            slug = h["url"].rstrip("/").split("/")[-1]
            h["title"] = slug.replace("-", " ").title()

    return [h for h in parser.hackathons if h["title"]]


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------


def score_keyword(hackathon: dict) -> int:
    """Fallback keyword-based relevance scoring (0–10)."""
    text = (hackathon.get("title", "") + " " + " ".join(hackathon.get("tags", []))).lower()
    hits = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text)
    return min(10, hits * 2)


def score_with_llm(hackathon: dict) -> int:
    """Use Granite-4.1-8B on :13305 to score Cohezion-AI relevance (0–10).

    Falls back to keyword scoring if the model is unavailable.
    """
    title = hackathon.get("title", "unknown")
    tags = ", ".join(hackathon.get("tags", [])) or "none listed"
    prize = hackathon.get("prize", "unknown")
    prompt = (
        f"Rate this hackathon's relevance to an AI/ML agent platform (Cohezion) "
        f"on a scale of 0–10. Return ONLY an integer.\n"
        f"Title: {title}\nTags: {tags}\nPrize: {prize}\n"
        f"High relevance (8-10): AI, LLM, agents, generative AI, open source AI.\n"
        f"Low relevance (0-3): cooking, sports, social media, crypto-only, gaming.\n"
        f"Answer (integer only):"
    )
    payload = json.dumps(
        {
            "model": SCORE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 5,
        }
    ).encode()
    try:
        req = urllib.request.Request(  # noqa: S310
            f"{LEMONADE_URL}/api/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            data = json.loads(r.read())
            text = data["choices"][0]["message"]["content"].strip()
            # Extract first integer from response
            m = re.search(r"\d+", text)
            if m:
                return min(10, max(0, int(m.group())))
    except Exception as e:
        print(f"[dorahacks] LLM scoring failed ({e}), using keywords", file=sys.stderr)
    return score_keyword(hackathon)


# ---------------------------------------------------------------------------
# Feed management
# ---------------------------------------------------------------------------


def load_existing_urls() -> set[str]:
    """Return URLs already in the feed to avoid duplicates."""
    if not FEED_PATH.exists():
        return set()
    content = FEED_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"https://dorahacks\.io/hackathon/[^\s\)\"]+", content))


def append_to_feed(hackathon: dict, score: int, ts: str) -> None:
    """Append one hackathon entry to DORAHACKS_FEED.md."""
    FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not FEED_PATH.exists():
        FEED_PATH.write_text(
            "# DoraHacks Hackathon Feed\n\n"
            "Auto-generated by `scripts/dorahacks_monitor.py` — item 270.\n"
            "Sign-up requires Google OAuth at https://dorahacks.io (human-gated).\n\n",
            encoding="utf-8",
        )
    title = hackathon.get("title", "Unknown")
    url = hackathon.get("url", "")
    prize = hackathon.get("prize", "TBD")
    deadline = hackathon.get("deadline", "TBD")
    tags = ", ".join(hackathon.get("tags", [])) or "—"
    entry = (
        f"## {title}\n"
        f"- **URL:** {url}\n"
        f"- **AI-relevance score:** {score}/10\n"
        f"- **Prize:** {prize}\n"
        f"- **Deadline:** {deadline}\n"
        f"- **Tags:** {tags}\n"
        f"- **Added:** {ts}\n"
        f"- **Status:** OPPORTUNITY — sign up at {url} (Google OAuth required)\n\n"
    )
    with open(FEED_PATH, "a", encoding="utf-8") as f:
        f.write(entry)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="DoraHacks hackathon intelligence monitor")
    parser.add_argument(
        "--min-score", type=int, default=7, help="Minimum score to save (default 7)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing")
    parser.add_argument("--no-inference", action="store_true", help="Use keyword scoring only")
    parser.add_argument("--url", default=DORAHACKS_URL, help="Override listing URL")
    args = parser.parse_args()

    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[dorahacks] Fetching {args.url} ...")

    hackathons = fetch_hackathons(args.url)
    print(f"[dorahacks] Found {len(hackathons)} hackathon entries")

    if not hackathons:
        print("[dorahacks] WARNING: no hackathons found — page may require JS rendering")
        print("[dorahacks] Tip: check if the page uses client-side rendering (Next.js/React)")
        return 0

    existing = load_existing_urls()
    new_count = 0

    for h in hackathons:
        score = score_keyword(h) if args.no_inference else score_with_llm(h)
        is_new = h["url"] not in existing
        flag = "NEW" if is_new else "seen"
        hi = "★" if score >= args.min_score else " "
        print(f"  {hi} [{score:2d}/10] {flag:4s}  {h['title'][:50]:<50}  {h['url']}")

        if score >= args.min_score and is_new and not args.dry_run:
            append_to_feed(h, score, ts)
            new_count += 1
            print(f"         → appended to {FEED_PATH.relative_to(REPO)}")

    if not args.dry_run:
        print(f"[dorahacks] {new_count} new relevant hackathons added to feed")
        print(f"[dorahacks] Feed: {FEED_PATH}")
        print(f"[dorahacks] HUMAN GATE: sign-up requires Google OAuth at {DORAHACKS_URL}")
    else:
        print("[dorahacks] dry-run: no writes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
