#!/usr/bin/env python3
"""Cohezion Kaggle SDK & KaggleHub Bridge (Comprehensive Edition).
================================================================
Unlocks native, typed programmatic access across the entire official
https://github.com/Kaggle ecosystem:
1. `kagglesdk.KaggleClient`: Typed RPCs for Competitions, Discussions, Benchmarks, and Agents.
2. `kagglehub`: Zero-copy asset downloads, model caching, and programmatic dataset publishing.
3. `kaggle_environments`: Simulation engines for RL and game environments.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import kagglehub
import kagglesdk
from kagglesdk.competitions.types.competition_api_service import (
    ApiGetLeaderboardRequest,
    ApiListSubmissionsRequest,
    ApiListCompetitionTopicsRequest,
)

logger = logging.getLogger("CohezionKaggleSDK")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")


class KaggleSDKBridge:
    """Unified bridge for Kaggle's official next-gen libraries (kagglesdk + kagglehub)."""

    def __init__(self) -> None:
        self.client = kagglesdk.KaggleClient()
        self.username = self.client.username or "manderson240"
        logger.info("Initialized KaggleSDKBridge for authenticated user '%s'", self.username)

    def whoami(self) -> Dict[str, Any]:
        """Validates credentials and returns active Kaggle identity."""
        return kagglehub.whoami()

    def get_leaderboard_podium(self, competition: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Retrieves top leaderboard entries using typed kagglesdk RPC."""
        req = ApiGetLeaderboardRequest()
        req.competition_name = competition
        req.page_size = top_n
        resp = self.client.competitions.competition_api_client.get_leaderboard(req)
        podium = []
        for i, s in enumerate(resp.submissions, 1):
            podium.append({
                "rank": i,
                "team_name": s.team_name,
                "team_id": s.team_id,
                "score": s.score,
                "date": str(s.submission_date),
            })
        return podium

    def get_competition_topics(self, competition: str, page_size: int = 15) -> List[Dict[str, Any]]:
        """Retrieves recent discussion topics for a competition via kagglesdk."""
        req = ApiListCompetitionTopicsRequest()
        req.competition_name = competition
        req.page = 1
        resp = self.client.competitions.competition_api_client.list_competition_topics(req)
        topics = []
        for t in getattr(resp, "topics", []):
            topics.append({
                "id": getattr(t, "id", None),
                "title": getattr(t, "title", ""),
                "score": getattr(t, "score", 0),
                "comments": getattr(t, "total_replies", 0),
            })
        return topics

    def download_competition_resource(self, competition: str, path: Optional[str] = None) -> str:
        """Downloads competition resources using kagglehub with automatic local caching."""
        logger.info("Downloading competition resource '%s' via kagglehub...", competition)
        target = kagglehub.competition_download(competition, path=path)
        logger.info("Resource ready at: %s", target)
        return str(target)

    def download_model(self, model_handle: str) -> str:
        """Downloads model artifacts with zero-token overhead."""
        logger.info("Resolving model '%s' via kagglehub...", model_handle)
        target = kagglehub.model_download(model_handle)
        logger.info("Model cached at: %s", target)
        return str(target)

    def upload_dataset(self, folder_path: str, handle: str) -> None:
        """Uploads or updates a Kaggle Dataset using kagglehub in one Python call."""
        logger.info("Publishing dataset '%s' from '%s' via kagglehub...", handle, folder_path)
        kagglehub.dataset_upload(handle, folder_path)
        logger.info("Dataset published successfully: https://www.kaggle.com/datasets/%s", handle)


def main() -> None:
    bridge = KaggleSDKBridge()
    identity = bridge.whoami()
    print(f"✓ Validated KaggleHub Identity: {identity}")

    print("\n--- Testing Native Typed Leaderboard via kagglesdk ---")
    podium = bridge.get_leaderboard_podium("rsna-knee-abnormality-detection", top_n=3)
    for p in podium:
        print(f"  Rank {p['rank']}: {p['team_name']} | Score: {p['score']}")

    print("\n--- Testing Discussion Topics via kagglesdk ---")
    topics = bridge.get_competition_topics("gemma-4-developer-agent", page_size=3)
    print(f"Retrieved {len(topics)} topics successfully.")


if __name__ == "__main__":
    main()
