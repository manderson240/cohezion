#!/usr/bin/env python3
"""Kaggle Discussion Knowledge Extractor & Learner (Hardened Signal-Ranked Edition).
===================================================================================
Automated harvester that ingests, cleans, classifies, and extracts competitive intelligence,
tactical breakthroughs, pitfalls, and organizer clarifications from Kaggle discussion
threads across ACTIVE competitions.

Key Features:
- Strictly filters to ACTIVE, unexpired competitions (Mandate 8).
- Multi-mode harvesting: unions `sort_by="top"` (consensus SOTA) and `sort_by="active"` (breaking updates).
- Signal-to-noise scoring based on competitive keywords (CV/LB, leaks, bug alerts, weights).
- Automatic categorization: BUG_ALERT, METRIC_NUANCE, SOTA_RECIPE, DATA_LEAK_SHIFT, RULES_COMPLIANCE.
- Structured JSON and markdown reporting for downstream Ollama Cloud agent synthesis.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kaggle.api.kaggle_api_extended import KaggleApi

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("discussion_learner")

# Strictly filter to active, unexpired competitions per Mandate 8
TARGET_COMPETITIONS = [
    "arc-prize-2026-arc-agi-2",
    "arc-prize-2026-arc-agi-3",
    "arc-prize-2026-paper-track",
    "rsna-knee-abnormality-detection",
    "enveda-CASMI26-molecule-id-mass-spectra",
    "nfl-big-data-bowl-2027",
    "name-that-llm",
    "gemma-4-developer-agent",
]

HIGH_SIGNAL_KEYWORDS = [
    "cv", "lb", "leak", "validation", "correlation", "weights", "metric", "bug",
    "0.00", "timeout", "docker", "offline", "relink", "monotonicity", "log-loss",
    "baseline", "shakeup", "sota", "rules", "ineligible", "precursor", "formula",
    "affordance", "zobrist", "program synthesis", "raptor", "coatnet", "dinov2",
    "m/z", "ppm", "fragment", "sub-structure", "tanimoto", "auc", "roc", "calibration",
    "loss", "gradient", "lora", "sft", "ttt", "beam search", "heuristic", "post-process",
    "adduct", "neutral loss", "ms/ms", "ms2", "stylometry", "sinkhorn", "balanced accuracy",
    "markov", "n-gram", "temperature", "marginal", "de-anonymization", "perplexity"
]

LOW_SIGNAL_KEYWORDS = [
    "teammate", "team up", "looking for team", "whatsapp", "telegram", "beginner",
    "newbie", "intro", "upvote", "connection", "connect", "study group"
]


def clean_html(raw_html: str) -> str:
    """Strips HTML tags and unescapes entities."""
    if not raw_html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compute_signal_score(
    title: str, messages: List[Dict[str, Any]], votes: Any = 0, comments: Any = 0
) -> float:
    """Computes a quantitative signal-to-noise score for a discussion topic."""
    combined_text = (title + " " + " ".join(m.get("content", "") for m in messages)).lower()

    try:
        v_num = int(votes) if isinstance(votes, (int, float, str)) and str(votes).isdigit() else 0
    except Exception:
        v_num = 0

    try:
        c_num = int(comments) if isinstance(comments, (int, float, str)) and str(comments).isdigit() else 0
    except Exception:
        c_num = 0

    # Base score from community engagement
    base_score = math.log1p(max(0, v_num)) * 2.0 + math.log1p(max(0, c_num)) * 1.5

    # Keyword bonuses
    bonus = 0.0
    for kw in HIGH_SIGNAL_KEYWORDS:
        if kw in combined_text:
            bonus += 2.0

    # Social / spam penalty
    penalty = 0.0
    for kw in LOW_SIGNAL_KEYWORDS:
        if kw in combined_text:
            penalty += 4.0

    return max(0.0, base_score + bonus - penalty)


def classify_topic_category(title: str, messages: List[Dict[str, Any]]) -> str:
    """Categorizes the discussion thread into an actionable archetype."""
    text = (title + " " + " ".join(m.get("content", "") for m in messages)).lower()

    if any(k in text for k in ["0.00", "timeout", "bug", "crash", "oom", "fail", "docker", "offline"]):
        return "BUG_ALERT"
    if any(k in text for k in ["metric", "log-loss", "monotonicity", "auc", "roc", "calibration", "brier"]):
        return "METRIC_NUANCE"
    if any(k in text for k in ["rule", "ineligible", "commercial", "license", "api", "eligibility"]):
        return "RULES_COMPLIANCE"
    if any(k in text for k in ["leak", "distribution", "train.parquet", "missing", "shakeup", "split", "cv-lb"]):
        return "DATA_LEAK_SHIFT"
    if any(k in text for k in ["weights", "sota", "raptor", "coatnet", "dinov2", "baseline", "ttt", "sft", "architecture"]):
        return "SOTA_RECIPE"

    return "GENERAL_DISCUSSION"


class KaggleDiscussionLearner:
    """Harvester and knowledge ranker for Kaggle competition discussion threads."""

    def __init__(self, api: Optional[KaggleApi] = None):
        if api is not None:
            self.api = api
        else:
            self.api = KaggleApi()
            self.api.authenticate()

    def fetch_competition_discussions(
        self,
        comp_slug: str,
        max_topics_per_mode: int = 6,
        max_msgs_per_topic: int = 4,
        sort_modes: Tuple[str, ...] = ("top", "active"),
    ) -> List[Dict[str, Any]]:
        """Fetches active & top discussion topics, cleans them, and computes signal score."""
        logger.info("Fetching discussions for %s across modes %s...", comp_slug, sort_modes)
        topics_dict: Dict[int, Any] = {}

        for mode in sort_modes:
            try:
                resp = self.api.competition_list_topics(comp_slug, sort_by=mode)
                topics = getattr(resp, "topics", [])
                for t in topics[:max_topics_per_mode]:
                    topic_id = getattr(t, "id", None)
                    if topic_id and topic_id not in topics_dict:
                        topics_dict[topic_id] = t
            except Exception as e:
                logger.warning("  Failed to list topics for %s (mode=%s): %s", comp_slug, mode, e)

        collected_topics = []

        for topic_id, topic in topics_dict.items():
            title = getattr(topic, "title", "No Title")
            comment_count = getattr(topic, "comment_count", 0)
            url = getattr(topic, "topic_url", "")
            votes = getattr(topic, "votes", 0)

            logger.info("  Reading Topic [%d] %s (%d comments)...", topic_id, title, comment_count)
            messages_list = []

            try:
                msg_resp = self.api.competition_list_topic_messages(
                    comp_slug, topic_id, page_size=max_msgs_per_topic
                )
                raw_msgs = getattr(msg_resp, "messages", [])
                for m in raw_msgs:
                    content = clean_html(getattr(m, "content", ""))
                    author = getattr(m, "author_name", "")
                    post_date = str(getattr(m, "post_date", ""))
                    msg_votes = getattr(m, "votes", 0)
                    if content:
                        messages_list.append({
                            "author": author,
                            "date": post_date,
                            "votes": msg_votes,
                            "content": content,
                        })
            except Exception as e:
                logger.warning("  Failed to fetch messages for topic %d: %s", topic_id, e)

            signal_score = compute_signal_score(title, messages_list, votes, comment_count)
            category = classify_topic_category(title, messages_list)

            collected_topics.append({
                "id": topic_id,
                "title": title,
                "url": url,
                "comments": comment_count,
                "votes": votes,
                "signal_score": round(signal_score, 2),
                "category": category,
                "messages": messages_list,
            })

            # Polite rate limiting between topic requests
            time.sleep(0.3)

        # Sort topics by signal score descending
        collected_topics.sort(key=lambda x: x["signal_score"], reverse=True)
        return collected_topics

    def run_all(
        self,
        output_json: Path,
        output_md: Path,
        competitions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Harvests discussions across active competitions and compiles knowledge base."""
        target_comps = competitions or TARGET_COMPETITIONS
        all_results = {}
        for comp in target_comps:
            all_results[comp] = self.fetch_competition_discussions(comp)

        # Save raw structured JSON
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        logger.info("Saved structured discussion JSON to %s", output_json)

        # Generate synthesized markdown report
        self.generate_markdown_report(all_results, output_md)
        logger.info("Saved synthesized discussion report to %s", output_md)
        return all_results

    def generate_markdown_report(self, all_data: Dict[str, Any], output_path: Path):
        """Compiles clean, signal-ranked markdown report."""
        lines = [
            "# Kaggle Active Competitions Intelligence & Discussion Knowledge Base",
            f"\n**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "**Source**: Active competition forums union of `sort_by='top'` and `sort_by='active'`.",
            "**Filter**: Filtered to unexpired monetary competitions per Mandate 8.\n",
            "---\n",
        ]

        for comp, topics in all_data.items():
            lines.append(f"## Competition: `{comp}`\n")
            if not topics:
                lines.append("*No active topics retrieved or access restricted.*\n")
                continue

            for t in topics:
                cat_badge = f"`[{t['category']}]`"
                score_badge = f"`Signal: {t['signal_score']}`"
                lines.append(f"### {cat_badge} [{t['id']}] {t['title']} ({t['comments']} comments, {score_badge})")
                if t.get("url"):
                    lines.append(f"**URL**: https://www.kaggle.com{t['url']}")
                lines.append("")

                if not t["messages"]:
                    lines.append("*No message text retrieved.*")
                else:
                    for i, m in enumerate(t["messages"]):
                        author_str = f"**{m['author']}**" if m['author'] else "User"
                        date_str = f" ({m['date'][:10]})" if m['date'] else ""
                        lines.append(f"> **Message {i+1} by {author_str}{date_str}** [Votes: {m['votes']}]:")
                        quoted = "\n> ".join(m["content"].split("\n"))
                        lines.append(f"> {quoted}\n")

                lines.append("\n---\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Kaggle Discussion Knowledge Extractor")
    parser.add_argument("--json", type=Path, default=Path("docs/research/kaggle_discussions_raw.json"))
    parser.add_argument("--md", type=Path, default=Path("docs/research/kaggle_discussions_knowledge_base.md"))
    parser.add_argument("--competitions", nargs="+", default=None)
    args = parser.parse_args()

    learner = KaggleDiscussionLearner()
    learner.run_all(args.json, args.md, competitions=args.competitions)


if __name__ == "__main__":
    main()
