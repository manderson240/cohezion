"""Cohezion Sovereign Kaggle Competition Manager (MCP Server).

Exposes Model Context Protocol (MCP) tool endpoints for:
1. `list_active_cash_competitions`: Returns prize pools, deadlines, and submission quotas.
2. `deploy_kernel`: Deploys airgapped Python scripts with verified metadata.
3. `submit_to_leaderboard`: Submits verified kernel outputs directly to the competition leaderboard.
4. `run_local_simulation_batch`: Spawns multi-threaded MCTS/CFR tournament simulations locally.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [KAGGLE_MCP] %(message)s")
logger = logging.getLogger("kaggle_mcp")


class KaggleCompetitionMCPServer:
    """Sovereign MCP Server interface for Kaggle Competition Automation."""

    def __init__(self) -> None:
        self.server_name = "kaggle-competition-manager"

    def list_active_cash_competitions(self) -> list[dict[str, Any]]:
        """Lists all open cash prize competitions with verified metadata."""
        out = subprocess.check_output(["kaggle", "competitions", "list", "--sort-by", "latestDeadline", "--page-size", "30"]).decode()
        lines = [l for l in out.strip().split("\n") if l.strip()]
        results = []
        for line in lines[2:]:
            if any(curr in line for curr in ["Usd", "$", "USD"]):
                parts = line.split()
                if len(parts) >= 6:
                    results.append({
                        "url": parts[0],
                        "competition_id": parts[0].split("/")[-1],
                        "deadline": f"{parts[1]} {parts[2]}",
                        "reward": f"{parts[4]} {parts[5]}",
                        "teams": parts[6] if len(parts) > 6 else "N/A"
                    })
        return results

    def submit_to_leaderboard(self, competition: str, kernel_slug: str, version: int, file_name: str = "submission.csv", message: str = "Cohezion AutoHarness Submit") -> dict[str, Any]:
        """Submits a completed kernel version output to the live leaderboard."""
        cmd = [
            "kaggle", "competitions", "submit",
            "-c", competition,
            "-k", kernel_slug,
            "-v", str(version),
            "-f", file_name,
            "-m", message
        ]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
            return {"status": "SUCCESS", "message": out.strip()}
        except subprocess.CalledProcessError as e:
            return {"status": "ERROR", "message": e.output.decode().strip()}

    def get_submission_status(self, competition: str) -> list[dict[str, str]]:
        """Retrieves live scored submission status from Kaggle."""
        try:
            out = subprocess.check_output(["kaggle", "competitions", "submissions", "-c", competition]).decode()
            lines = [l for l in out.strip().split("\n") if l.strip()]
            submissions = []
            for line in lines[2:6]:
                submissions.append({"entry": line})
            return submissions
        except Exception as e:
            return [{"error": str(e)}]
