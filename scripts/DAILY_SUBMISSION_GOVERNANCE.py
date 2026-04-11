#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SubmissionGovernance")


class SubmissionGovernor:
    """
    Monitors and enforces Kaggle submission limits across multiple competitions.
    """

    def __init__(self):
        self.api = KaggleApi()
        self.api.authenticate()
        self.log_file = Path(".gemini_security/submission_log.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def check_limit(self, competition_id: str, limit: int = 5):
        """
        Checks current daily submission count and logs it.
        """
        try:
            submissions = self.api.competition_submissions(competition_id)
            today = datetime.now().date()
            today_subs = [s for s in submissions if s.date.date() == today]
            count = len(today_subs)

            logger.info(f"Competition: {competition_id} | Today's Submissions: {count}/{limit}")

            # Log for historical tracking
            with open(self.log_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "competition_id": competition_id,
                            "count": count,
                            "limit": limit,
                        }
                    )
                    + "\n"
                )

            return count < limit
        except Exception as e:
            logger.error(f"Failed to check limits for {competition_id}: {e}")
            return False


if __name__ == "__main__":
    gov = SubmissionGovernor()
    competitions = [
        "nvidia-nemotron-model-reasoning-challenge",
        "ai-mathematical-olympiad-progress-prize-3",
        "arc-prize-2026",
        "birdclef-2026",
    ]

    all_clear = True
    for comp in competitions:
        if not gov.check_limit(comp):
            logger.warning(f"⚠️ Submission limit reached or error for {comp}")
            all_clear = False

    if all_clear:
        logger.info("✅ All systems clear for daily submissions.")
    else:
        sys.exit(1)
