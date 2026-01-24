import json
import logging
import time
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any, List
# Assuming cohezion has an email notifier
# from cohezion.reliability.email_notifier import send_email

logger = logging.getLogger(__name__)

class HourlyMissionLogger:
    """
    Tracks and reports mission progress hourly.
    """
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.log_path = Path(f"logs/multiverse_{mission_id}_hourly.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.start_time = time.time()
        self.last_report_time = self.start_time

    def log_snapshot(self,
                    vitals: Dict[str, Any],
                    results: List[Dict[str, Any]],
                    next_steps: str):
        """Logs a snapshot and prepares email content."""
        timestamp = datetime.now(UTC).isoformat()
        entry = {
            "timestamp": timestamp,
            "vitals": vitals,
            "results_summary": [
                {
                    "scenario": r["scenario_name"],
                    "stability": r["mean_stability"],
                    "bright_spots": r["bright_spot_count"]
                } for r in results
            ],
            "next_steps": next_steps
        }

        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Prepare email report (Internal Narration)
        report = f"""
# 🌌 Multiverse Mission Report: {self.mission_id}
**Time:** {timestamp}
**Uptime:** {(time.time() - self.start_time)/3600:.2f} hours

## 📊 Performance Summary
| Scenario | Stability | Bright Spots |
|---|---|---|
"""
        for r in entry["results_summary"]:
            report += f"| {r['scenario']} | {r['stability']:.4f} | {r['bright_spots']} |\n"

        report += f"\n## 🛡️ Resource Vitals\n- CPU: {vitals['cpu_percent']}%\n- RAM: {vitals['memory_percent']}%\n"
        report += f"\n## 🔮 Next Hour\n{next_steps}"

        logger.info(f"Hourly snapshot logged for {self.mission_id}")
        return report

# Example usage for integration
# logger = HourlyMissionLogger("nexus_v1")
# report = logger.log_snapshot(vitals, current_results, "Expanding to 'The Glitch' universe...")
