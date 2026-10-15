#!/usr/bin/env python3
"""Cohezion Kaggle Winner Solution Miner.
Queries official Kaggle discussions via kagglesdk/kaggle API to extract
first-principles winning patterns from past top finishes in:
- Medical Imaging: RSNA Lumbar Spine 2024, RSNA Abdominal 2023, RSNA Breast Cancer
- Spatio-temporal / Sports: NFL Big Data Bowl 2024, 2025, 2026
- Symbolic / AGI: ARC Prize 2024
"""

from __future__ import annotations

import logging

from scripts.kaggle.kagglesdk_bridge import KaggleSDKBridge


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("WinnerMiner")

TARGET_COMPS = [
    "rsna-2024-lumbar-spine-osteoarthritis-detection",
    "rsna-2023-abdominal-trauma-detection",
    "rsna-breast-cancer-detection",
    "nfl-big-data-bowl-2025",
    "nfl-big-data-bowl-2024",
    "arc-prize-2024",
    "rsna-knee-abnormality-detection",
    "nfl-big-data-bowl-2027",
]


def mine_top_solutions():
    bridge = KaggleSDKBridge()
    results = {}
    for comp in TARGET_COMPS:
        try:
            topics = bridge.get_competition_topics(comp, page_size=25)
            winning_topics = []
            for t in topics:
                title = t.get("title", "")
                title_lower = title.lower()
                keywords = [
                    "1st",
                    "2nd",
                    "3rd",
                    "4th",
                    "5th",
                    "winner",
                    "solution",
                    "summary",
                    "place",
                    "gold",
                ]
                if any(k in title_lower for k in keywords):
                    winning_topics.append(t)
            results[comp] = winning_topics
            logger.info("Found %d winning/solution topics for %s", len(winning_topics), comp)
            for w in winning_topics[:5]:
                logger.info("  [%s] %s (id=%s)", w.get("score"), w.get("title"), w.get("id"))
        except Exception as e:
            logger.warning("Could not query %s: %s", comp, e)
    return results


if __name__ == "__main__":
    mine_top_solutions()
