import time
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CompetitionRateLimiter:
    """
    Local rate limiter to enforce the 1-hour submission hard limit.
    Ensures we don't waste leaderboard slots or hit platform limits blindly.
    """
    
    def __init__(self, lock_file: str = ".submission_lock"):
        self.lock_path = Path(os.getcwd()) / lock_file
        self.limit_seconds = 3600 # 1 hour

    def _load_data(self) -> dict:
        if self.lock_path.exists():
            try:
                return json.loads(self.lock_path.read_text())
            except:
                return {}
        return {}

    def _save_data(self, data: dict):
        self.lock_path.write_text(json.dumps(data, indent=2))

    def can_submit(self, leaderboard_id: str) -> tuple[bool, float]:
        """
        Check if a submission is allowed for the given leaderboard.
        Returns (allowed, seconds_remaining).
        """
        data = self._load_data()
        last_submission = data.get(leaderboard_id, 0)
        now = time.time()
        
        elapsed = now - last_submission
        if elapsed < self.limit_seconds:
            remaining = self.limit_seconds - elapsed
            return False, remaining
        
        return True, 0

    def record_submission(self, leaderboard_id: str):
        """Record a successful submission attempt."""
        data = self._load_data()
        data[leaderboard_id] = time.time()
        self._save_data(data)
        logger.info(f"Recorded submission for {leaderboard_id}. Next slot in 1 hour.")

def check_rate_limit(leaderboard_id: str, lock_file: str = ".submission_lock"):
    """
    Helper function for submission scripts.
    Usage:
        if not check_rate_limit("amd-moe"):
            sys.exit(1)
    """
    limiter = CompetitionRateLimiter(lock_file=lock_file)
    allowed, remaining = limiter.can_submit(leaderboard_id)
    
    if not allowed:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        print(f"\n[!] RATE LIMITED: You must wait {minutes}m {seconds}s before submitting to '{leaderboard_id}' again.")
        print("[!] Refer to @RATE_LIMIT_EXPLANATION.md for details.")
        return False
    
    return True
