#!/usr/bin/env python3
"""Active Kaggle Competitions Discussion Miner
==============================================
Mines, parses, and synthesizes discussion forums across all active Kaggle competitions:
1. rsna-knee-abnormality-detection
2. arc-prize-2026-arc-agi-2
3. arc-prize-2026-arc-agi-3
4. enveda-CASMI26-molecule-id-mass-spectra
5. name-that-llm
6. gemma-4-developer-agent

Adheres strictly to the Active Competition Reporting Filter:
- Excludes closed/archived benchmarks and excluded tracks.
- Synthesizes findings with first-principles rigor and Systems Engineering V-Model depth.
"""

from __future__ import annotations

import html
import json
import logging
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("discussion_miner")

ACTIVE_COMPETITIONS = [
    {
        "slug": "rsna-knee-abnormality-detection",
        "name": "RSNA Knee Abnormality Detection",
        "domain": "Medical Imaging / 3D MRI / Radiomics",
    },
    {
        "slug": "arc-prize-2026-arc-agi-2",
        "name": "ARC Prize 2026 - ARC-AGI-2",
        "domain": "AGI / Program Synthesis / Discrete Topology",
    },
    {
        "slug": "arc-prize-2026-arc-agi-3",
        "name": "ARC Prize 2026 - ARC-AGI-3 (Interactive)",
        "domain": "Interactive AGI / Exploration / Affordance Discovery",
    },
    {
        "slug": "enveda-CASMI26-molecule-id-mass-spectra",
        "name": "Enveda CASMI26 Molecule ID",
        "domain": "Computational Chemistry / High-Res Mass Spectrometry",
    },
    {
        "slug": "name-that-llm",
        "name": "Name That LLM",
        "domain": "NLP / Stylometry / Generative Model Attribution",
    },
    {
        "slug": "gemma-4-developer-agent",
        "name": "Gemma-4 Developer Agent",
        "domain": "Agentic Coding / AST Code Synthesis / Autonomous Systems",
    },
]

OUTPUT_DIR = Path("data/kaggle_discussions")
DOCS_FILE = Path("docs/kaggle/ACTIVE_COMPETITIONS_DISCUSSION_MINING.md")
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "02-Research"


def clean_html(raw_html: str) -> str:
    """Convert HTML snippet to clean readable markdown text."""
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    # Convert paragraph breaks and line breaks
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p>", "", text, flags=re.IGNORECASE)
    # Convert headers
    text = re.sub(r"<h([1-6])>(.*?)</h\1>", r"\n\n### \2\n\n", text, flags=re.IGNORECASE)
    # Convert code blocks
    text = re.sub(
        r"<pre><code>(.*?)</code></pre>",
        r"\n```\n\1\n```\n",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL | re.IGNORECASE)
    # Convert bold / strong
    text = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", text, flags=re.IGNORECASE)
    # Convert links
    text = re.sub(
        r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>',
        r"[\2](\1)",
        text,
        flags=re.IGNORECASE,
    )
    # Strip any remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def run_kaggle_json(args: list[str]) -> list[dict[str, Any]]:
    """Execute kaggle CLI command and parse JSON output safely."""
    cmd = ["kaggle", *args, "--format", "json"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = [
            line
            for line in res.stdout.strip().split("\n")
            if not line.startswith("Warning:") and not line.startswith("Next")
        ]
        if not lines:
            return []
        parsed = json.loads("\n".join(lines))
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
        return []
    except subprocess.CalledProcessError as exc:
        logger.warning("Command %s failed: %s", " ".join(cmd), exc.stderr[:200])
        return []
    except Exception as exc:
        logger.warning("Parsing error on %s: %s", " ".join(cmd), exc)
        return []


def mine_competition(comp: dict[str, str], max_topics: int = 12) -> dict[str, Any]:
    """Mine discussion topics and top messages for a single competition."""
    slug = comp["slug"]
    logger.info("Mining discussions for: %s (%s)", comp["name"], slug)

    topics_dict: dict[int, dict[str, Any]] = {}

    for sort_mode in ["top", "hot", "new"]:
        raw_topics = run_kaggle_json(["competitions", "topics", "list", slug, "-s", sort_mode])
        for t in raw_topics:
            tid = t.get("id")
            if tid and tid not in topics_dict:
                t["discovered_via"] = sort_mode
                topics_dict[tid] = t
        time.sleep(0.3)

    # Sort topics by combined impact score: 2 * votes + commentCount
    sorted_topics = sorted(
        topics_dict.values(),
        key=lambda x: x.get("votes", 0) * 2 + x.get("commentCount", 0),
        reverse=True,
    )

    selected_topics = sorted_topics[:max_topics]
    mined_records = []

    for idx, t in enumerate(selected_topics):
        tid = t["id"]
        title = t.get("title", f"Topic {tid}")
        logger.info(
            "  [%d/%d] Fetching topic #%d: '%s' (V:%d, C:%d)",
            idx + 1,
            len(selected_topics),
            tid,
            title[:40],
            t.get("votes", 0),
            t.get("commentCount", 0),
        )

        messages = run_kaggle_json(["competitions", "topic-messages", slug, str(tid), "-s", "old"])
        time.sleep(0.2)

        if not messages:
            continue

        first_msg = messages[0]
        cleaned_body = clean_html(first_msg.get("content", ""))

        # Mine high-upvote comments (e.g. host clarifications, grandmaster replies)
        notable_replies = []
        for reply in messages[1:]:
            votes = reply.get("votes", 0)
            author = reply.get("authorName", "Participant")
            body = clean_html(reply.get("content", ""))
            if (votes >= 2 or len(body) > 250) and body:
                notable_replies.append(
                    {
                        "id": reply.get("id"),
                        "author": author,
                        "votes": votes,
                        "date": reply.get("postDate"),
                        "content": body[:1200],  # bounded to preserve quality
                    }
                )

        mined_records.append(
            {
                "topic_id": tid,
                "title": title,
                "votes": t.get("votes", 0),
                "comment_count": t.get("commentCount", 0),
                "post_date": t.get("postDate"),
                "discovered_via": t.get("discovered_via"),
                "original_post": cleaned_body,
                "notable_replies": notable_replies[:5],
            }
        )

    result = {
        "competition_slug": slug,
        "competition_name": comp["name"],
        "domain": comp["domain"],
        "mined_at": datetime.now(UTC).isoformat(),
        "total_topics_analyzed": len(topics_dict),
        "selected_topics_count": len(mined_records),
        "topics": mined_records,
    }

    # Save individual JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{slug}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    logger.info("Saved %d topics to %s", len(mined_records), out_file)

    return result


def generate_synthesis_markdown(all_results: list[dict[str, Any]]) -> str:
    """Synthesize mined forum discussions into a high-leverage strategic report."""
    md = []
    md.append("# Kaggle Active Competitions Discussion Intelligence Synthesis")
    md.append(f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    md.append("**Principle**: Quality Over Quantity — Deep Domain Invariant Extraction\n")
    md.append("---\n")

    for comp in all_results:
        slug = comp["competition_slug"]
        name = comp["competition_name"]
        domain = comp["domain"]
        topics = comp["topics"]

        md.append(f"## 🏆 {name} (`{slug}`)")
        md.append(f"**Domain**: {domain}")
        md.append(f"**Topics Mined**: {len(topics)} highest-impact discussions\n")

        for t in topics:
            tid = t["topic_id"]
            title = t["title"]
            votes = t["votes"]
            comments = t["comment_count"]
            date = t.get("post_date", "")[:10]
            body = t["original_post"]

            md.append(f"### [#{tid}] {title}")
            md.append(f"*Votes: {votes} | Comments: {comments} | Date: {date}*")
            md.append("\n**Key Findings & Context:**")

            # Format snippet concisely
            lines = [line.strip() for line in body.split("\n") if line.strip()]
            snippet = "\n\n".join(lines[:6]) if len(lines) > 6 else "\n\n".join(lines)
            md.append(f"> {snippet}\n" if snippet else "> *(No text content)*\n")

            if t["notable_replies"]:
                md.append("**Notable Follow-up Contributions & Clarifications:**")
                for r in t["notable_replies"]:
                    r_author = r.get("author") or "Community Member"
                    r_votes = r.get("votes", 0)
                    r_snippet = r["content"].replace("\n", " ")[:280]
                    md.append(f"- **{r_author}** (+{r_votes}): {r_snippet}...")
                md.append("")

        md.append("---\n")

    return "\n".join(md)


def main() -> None:
    all_results = []
    logger.info("Starting comprehensive discussion mining across 6 active competitions...")

    for comp in ACTIVE_COMPETITIONS:
        res = mine_competition(comp, max_topics=10)
        all_results.append(res)

    # Master JSON dump
    with open(OUTPUT_DIR / "all_active_discussions.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    # Master Markdown Report
    DOCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    report_md = generate_synthesis_markdown(all_results)
    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        f.write(report_md)
    logger.info("Generated master markdown dossier at %s", DOCS_FILE)

    # Obsidian Vault Sync
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        vault_file = (
            VAULT_DIR
            / f"{datetime.now(UTC).strftime('%Y-%m-%d')}-active-competitions-discussions.md"
        )
        with open(vault_file, "w", encoding="utf-8") as f:
            f.write(report_md)
        logger.info("Synchronized to Obsidian Vault at %s", vault_file)
    except Exception as exc:
        logger.warning("Obsidian vault export skipped: %s", exc)


if __name__ == "__main__":
    main()
