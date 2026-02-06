import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

import subprocess


class PrunerAgent:
    """
    Agent responsible for identifying low-density code (bloat) and suggesting pruning.
    Powered by local qwen2.5-coder.
    Includes Autonomous Git Health Monitoring.
    """

    def __init__(self, target_dir: str = ".", model: str = "qwen2.5-coder:7b"):
        self.target_dir = Path(target_dir).resolve()
        self.model = model
        self.wallet_path = Path("src/cohezion/knowledge_graph/wallet.json")
        self.excludes = {
            ".git",
            "__pycache__",
            "venv",
            ".venv",
            "node_modules",
            "logs",
            ".gemini",
            "site-packages",
            ".idea",
            ".vscode",
        }
        self.extensions = {".py", ".md", ".sh", ".json"}

    async def monitor_git_health(self) -> bool:
        """
        Check if the git index is bloated (>100k files).
        If critical, it can trigger the surgical_prune script.
        """
        try:
            # Check number of files in index
            result = subprocess.run(
                ["git", "ls-files", "|", "wc", "-l"],
                shell=True,
                capture_output=True,
                text=True,
            )
            count = int(result.stdout.strip())

            if count > 100_000:
                logger.warning(f"🚨 GIT INDEX BLOAT DETECTED: {count} files tracked.")
                return False

            logger.info(f"Git Index Healthy: {count} files.")
            return True
        except Exception as e:
            logger.error(f"Failed to check git health: {e}")
            return False

    def _should_scan(self, path: Path) -> bool:
        """Check if file should be scanned."""
        if any(part in self.excludes for part in path.parts):
            return False
        if path.suffix not in self.extensions:
            return False
        if path.stat().st_size > 100_000:  # Skip huge files
            return False
        return True

    async def scan_directory(self) -> list[Path]:
        """Recursively find all scanable files."""
        if self.target_dir.is_file():
            return [self.target_dir]

        files = []
        for root, dirs, filenames in os.walk(self.target_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.excludes]

            for name in filenames:
                file_path = Path(root) / name
                if self._should_scan(file_path):
                    files.append(file_path)
        return files

    async def analyze_file(self, file_path: Path) -> dict[str, Any]:
        """Ask LLM to scoring Information Density."""
        content = file_path.read_text(errors="ignore")
        if not content.strip():
            return {"file": str(file_path), "score": 0.0, "reason": "Empty file"}

        prompt = f"""
        ANALYZE CODE DENSITY
        
        File: {file_path.name}
        Content:
        ```
        {content[:2000]} 
        ```
        (Truncated for analysis)
        
        Rate the "Information Density" of this file on a scale of 0.0 to 1.0.
        - 0.1: Dead code, excessive comments, boilerplate, or deprecated.
        - 0.5: Average utility.
        - 0.9: Highly optimized, critical logic.
        
        Return ONLY a JSON object:
        {{
            "score": <float>,
            "reason": "<short explanation>",
            "action": "KEEP" | "PRUNE" | "REFACTOR"
        }}
        """

        try:
            # We use a synchronous request here for simplicity,
            # but in a real massive scan we'd use a semaphore/async client
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = json.loads(response.json()["response"])
                result["file"] = str(file_path)
                result["lines"] = len(content.splitlines())
                return result
            else:
                logger.error(f"Model error {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Analysis failed for {file_path}: {e}")
            return None

    async def run_pruning_cycle(self):
        """Main execution flow."""
        # 1. Check Hygiene
        is_healthy = await self.monitor_git_health()
        if not is_healthy:
            logger.warning(
                "System requires surgical pruning. Please run `scripts/maintenance/surgical_prune.py`."
            )

        # 2. Start Scan
        logger.info(f"🌿 Starting Pruning Scan on {self.target_dir}...")
        files = await self.scan_directory()
        logger.info(f"Found {len(files)} candidates.")

        candidates = []
        total_potential_credits = 0

        # Limit scanning for this demo to avoid taking hours
        scan_limit = 20

        for i, file_path in enumerate(files[:scan_limit]):
            logger.info(f"[{i + 1}/{scan_limit}] Analyzing {file_path.name}...")
            result = await self.analyze_file(file_path)

            if result and result.get("score", 1.0) < 0.4:
                # It's Bloat!
                credits = result["lines"] * (1.0 - result["score"]) * 10
                result["potential_credits"] = int(credits)
                candidates.append(result)
                total_potential_credits += credits
                logger.info(
                    f"✂️ CANDIDATE: {file_path.name} (Score: {result['score']}) - Value: {int(credits)} Credits"
                )

        # Write Report
        report = {
            "timestamp": str(asyncio.get_event_loop().time()),
            "candidates": candidates,
            "total_potential_credits": int(total_potential_credits),
        }

        output_path = Path("PRUNING_CANDIDATES.json")
        output_path.write_text(json.dumps(report, indent=2))

        print("\n------------------------------------------------")
        print("🗡️  PRUNING CYCLE COMPLETE")
        print(f"    Candidates Found: {len(candidates)}")
        print(f"    Potential Ascension Credits: {int(total_potential_credits)}")
        print(f"    Report: {output_path.absolute()}")
        print("------------------------------------------------\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="scripts", help="Directory to scan")
    args = parser.parse_args()

    agent = PrunerAgent(target_dir=args.target)
    asyncio.run(agent.run_pruning_cycle())
