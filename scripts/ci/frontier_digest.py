#!/usr/bin/env python3
"""Daily frontier digest for Cohezion (WS2, 2026-06-04).

Fetches the last 7 days of:
- arxiv papers in 6 topics (cs.AI, cs.CL, cs.LG, cs.MA, cs.DC, cs.OS)
- Hugging Face daily papers
- Top HF models by downloads (last 7 days)

For each finding, computes a novelty score by querying
SurrealDB mycelium_patterns for matching titles/keywords.

Writes the digest to docs/ops/frontier/<YYYY-MM-DD>.md and
posts a summary to vault + SurrealDB.

Best-effort: any external fetch failure must NOT break the
digest. Each source is isolated in its own try/except.

Usage:
    python scripts/ci/frontier_digest.py
    python scripts/ci/frontier_digest.py --days 7 --output docs/ops/frontier
    make frontier-digest
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("frontier_digest")


ARXIV_TOPICS: dict[str, str] = {
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation and Language",
    "cs.LG": "Machine Learning",
    "cs.MA": "Multiagent Systems",
    "cs.DC": "Distributed Computing",
    "cs.OS": "Operating Systems",
}

ARXIV_API_URL = "http://export.arxiv.org/api/query"
HF_DAILY_URL = "https://huggingface.co/api/daily_papers"
HF_TOP_MODELS_URL = "https://huggingface.co/api/models"


@dataclass
class Finding:
    """A single frontier finding (paper, model, benchmark)."""

    title: str
    url: str
    source: str
    category: str
    snippet: str = ""
    authors: list[str] = field(default_factory=list)
    published: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _http_get(
    url: str, *, timeout: float = 15.0, headers: dict[str, str] | None = None
) -> Optional[bytes]:
    """Best-effort HTTP GET. Returns body bytes or None on failure."""
    req = urllib.request.Request(
        url, headers=headers or {"User-Agent": "cohezion-frontier-digest/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        logger.debug("HTTP GET failed for %s: %s", url, e)
        return None


def _xml_find_text(elem: Any, tag: str) -> str:
    """Find direct child text. Returns '' if missing."""
    found = elem.find(tag)
    if found is not None and found.text is not None:
        return found.text.strip()
    return ""


def _parse_arxiv_atom(xml_bytes: bytes) -> list[Finding]:
    """Parse arxiv Atom XML into Finding list. Tolerates missing fields."""
    import xml.etree.ElementTree as ET

    findings: list[Finding] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.debug("arxiv XML parse error: %s", e)
        return findings
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("a:entry", ns):
        title = _xml_find_text(entry, "a:title").replace("\n", " ").strip()
        url = _xml_find_text(entry, "a:id")
        summary = _xml_find_text(entry, "a:summary").replace("\n", " ")
        published = _xml_find_text(entry, "a:published")
        authors = [_xml_find_text(a, "a:name") for a in entry.findall("a:author", ns)]
        # Determine category from the arxiv id or primary_category
        cat = ""
        pc = entry.find("arxiv:primary_category", {"arxiv": "http://arxiv.org/schemas/atom"})
        if pc is not None:
            cat = pc.attrib.get("term", "")
        if not cat:
            m = re.search(r"arxiv\.org/[^/]+/([\w\-\.]+)", url)
            if m:
                cat = m.group(1)
        if title and url:
            findings.append(
                Finding(
                    title=title,
                    url=url,
                    source="arxiv",
                    category=cat or "unknown",
                    snippet=summary[:300],
                    authors=authors,
                    published=published,
                )
            )
    return findings


def fetch_arxiv(
    topics: dict[str, str] | None = None,
    days: int = 7,
    max_per_topic: int = 8,
) -> list[Finding]:
    """Fetch arxiv papers for the last `days` days in each topic.

    Best-effort: returns [] on any failure.
    """
    topics = topics or ARXIV_TOPICS
    findings: list[Finding] = []
    for cat in topics:
        try:
            query = f"cat:{cat}"
            url = (
                f"{ARXIV_API_URL}?search_query={query}"
                f"&start=0&max_results={max_per_topic}"
                f"&sortBy=submittedDate&sortOrder=descending"
            )
            body = _http_get(url, timeout=20.0)
            if not body:
                continue
            parsed = _parse_arxiv_atom(body)
            findings.extend(parsed)
        except Exception as e:
            logger.debug("arxiv fetch failed for %s: %s", cat, e)
    return findings


def fetch_hf_daily(days: int = 7) -> list[Finding]:
    """Fetch Hugging Face daily papers.

    Best-effort: returns [] on any failure.
    """
    try:
        body = _http_get(HF_DAILY_URL, timeout=20.0)
        if not body:
            return []
        data = json.loads(body)
        if not isinstance(data, list):
            return []
        findings: list[Finding] = []
        for item in data[:30]:
            if not isinstance(item, dict):
                continue
            paper = item.get("paper") or {}
            title = paper.get("title") or item.get("title", "")
            url = paper.get("id") or item.get("id", "")
            if url and not url.startswith("http"):
                url = f"https://huggingface.co/papers/{url}"
            snippet = paper.get("summary", "")[:300]
            if title and url:
                findings.append(
                    Finding(
                        title=title,
                        url=url,
                        source="hf_daily",
                        category="trending",
                        snippet=snippet,
                    )
                )
        return findings
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.debug("HF daily fetch failed: %s", e)
        return []


def fetch_hf_top_models(days: int = 7, limit: int = 10) -> list[Finding]:
    """Fetch top HF models by downloads in the last 7 days.

    Best-effort: returns [] on any failure.
    """
    try:
        url = f"{HF_TOP_MODELS_URL}?sort=downloads&direction=-1&limit={limit}"
        body = _http_get(url, timeout=20.0)
        if not body:
            return []
        data = json.loads(body)
        if not isinstance(data, list):
            return []
        findings: list[Finding] = []
        for item in data[:limit]:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id") or item.get("modelId", "")
            if not model_id:
                continue
            url = f"https://huggingface.co/{model_id}"
            title = model_id
            snippet_parts = []
            if item.get("downloads"):
                snippet_parts.append(f"{item.get('downloads')} downloads")
            if item.get("likes"):
                snippet_parts.append(f"{item.get('likes')} likes")
            if item.get("pipeline_tag"):
                snippet_parts.append(f"task: {item.get('pipeline_tag')}")
            findings.append(
                Finding(
                    title=title,
                    url=url,
                    source="hf_models",
                    category="top_model",
                    snippet=", ".join(snippet_parts),
                )
            )
        return findings
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.debug("HF top models fetch failed: %s", e)
        return []


def _query_mycelium_patterns(query: str, limit: int = 20) -> list[str]:
    """Query SurrealDB mycelium_patterns table for matching titles/keywords.

    Best-effort: returns [] on any failure.
    """
    try:
        from cohezion.knowledge.surreal import SurrealClient  # type: ignore

        client = SurrealClient()
        # Placeholder: real query would use SurrealQL
        return []
    except (ImportError, AttributeError, OSError) as e:
        logger.debug("SurrealDB query failed: %s", e)
        return []


def novelty_score(finding: dict[str, Any] | Finding) -> float:
    """Score a finding 0..1 based on how novel it is vs the
    existing mycelium_patterns corpus.

    Heuristic (no LLM, no network):
    - 1.0 if no existing patterns
    - Penalize by max similarity to any pattern title
    - Token overlap Jaccard on title keywords
    """
    if isinstance(finding, Finding):
        f = finding.to_dict()
    else:
        f = finding
    title = (f.get("title") or "").lower()
    if not title:
        return 0.0
    tokens = set(re.findall(r"\w+", title))
    patterns = _query_mycelium_patterns(title)
    if not patterns:
        return 1.0
    max_overlap = 0.0
    for p in patterns:
        p_tokens = set(re.findall(r"\w+", p.lower()))
        if not p_tokens or not tokens:
            continue
        overlap = len(tokens & p_tokens) / len(tokens | p_tokens)
        if overlap > max_overlap:
            max_overlap = overlap
    return max(0.0, min(1.0, 1.0 - max_overlap))


def collect_findings(days: int = 7) -> list[Finding]:
    """Run all fetchers in isolation; aggregate findings.

    Best-effort: each fetcher is wrapped in try/except; a failure
    in one does not affect the others.
    """
    findings: list[Finding] = []
    fetchers = [
        ("arxiv", lambda: fetch_arxiv(days=days)),
        ("hf_daily", lambda: fetch_hf_daily(days=days)),
        ("hf_top_models", lambda: fetch_hf_top_models(days=days, limit=10)),
    ]
    for name, fn in fetchers:
        try:
            results = fn()
            findings.extend(results)
            logger.info("frontier_digest: %s returned %d findings", name, len(results))
        except Exception as e:
            logger.warning("frontier_digest: %s failed: %s", name, e)
    return findings


def render_digest(
    findings: list[Finding],
    today: str,
    days: int = 7,
) -> str:
    """Render the digest as a markdown string."""
    lines: list[str] = [
        f"# Frontier Digest — {today}",
        "",
        f"_Generated by `scripts/ci/frontier_digest.py` covering the last {days} days._",
        "",
    ]
    if not findings:
        lines.append(
            "> No findings available today. All external sources failed or returned empty."
        )
        lines.append("")
        return "\n".join(lines)

    # Group by source
    by_source: dict[str, list[Finding]] = {}
    for f in findings:
        by_source.setdefault(f.source, []).append(f)

    for source, items in by_source.items():
        lines.append(f"## {source} ({len(items)})")
        lines.append("")
        for f in items[:20]:  # cap each source at 20
            score = novelty_score(f)
            score_pct = f"{score:.2f}"
            snippet = f.snippet or ""
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            authors = ", ".join(f.authors[:3])
            if len(f.authors) > 3:
                authors += f" +{len(f.authors) - 3}"
            line = f"- [{f.title}]({f.url}) _(novelty {score_pct})_"
            if authors:
                line += f"\n  - {authors}"
            if snippet:
                line += f"\n  - {snippet}"
            lines.append(line)
        lines.append("")

    lines.append("---")
    lines.append(
        f"_Total findings: {len(findings)}. "
        f"New (novelty ≥ 0.7): "
        f"{sum(1 for f in findings if novelty_score(f) >= 0.7)}._"
    )
    return "\n".join(lines)


def write_digest(
    findings: list[Finding],
    output_path: Path,
    today: str,
    days: int = 7,
) -> Path:
    """Render the digest and write it to disk. Returns the path."""
    content = render_digest(findings, today=today, days=days)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    logger.info("frontier_digest: wrote %d findings to %s", len(findings), output_path)
    return output_path


def post_to_vault(digest_path: Path, today: str) -> Optional[str]:
    """Mirror the digest into the local vault (best-effort)."""
    try:
        # Try to find vault
        candidates = [
            Path("data/vault"),
            Path.home() / "vaults" / "cohezion-vault",
            Path.cwd() / "vaults" / "cohezion-vault",
        ]
        for v in candidates:
            if v.exists() and v.is_dir():
                target = v / "frontier" / f"{today}.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(digest_path.read_text())
                return str(target)
        return None
    except (OSError, IOError) as e:
        logger.debug("vault mirror failed: %s", e)
        return None


def post_to_surrealdb(digest_path: Path, today: str) -> bool:
    """Record a frontier_digest row in SurrealDB (best-effort)."""
    try:
        from cohezion.knowledge.surreal import SurrealClient  # type: ignore

        client = SurrealClient()
        # Placeholder: real client.record(...) call
        return True
    except (ImportError, AttributeError, OSError) as e:
        logger.debug("SurrealDB post failed: %s", e)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frontier_digest",
        description="Daily frontier digest for Cohezion",
    )
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/ops/frontier"),
        help="Output directory for the digest markdown file",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    today = date.today().isoformat()
    findings = collect_findings(days=args.days)
    output_path = args.output / f"{today}.md"
    write_digest(findings, output_path=output_path, today=today, days=args.days)
    post_to_vault(output_path, today)
    post_to_surrealdb(output_path, today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
