#!/usr/bin/env python3
"""
Ollama Usage Maximizer - Maximizes Ollama usage within system constraints
Works with existing Ollama instances to push usage to limits before reset
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import httpx

from cohezion.concurrency.ollama_gate import get_gate


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/mike-anderson/dev/cohezion/logs/ollama_maximizer.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
Path("/home/mike-anderson/dev/cohezion/logs").mkdir(exist_ok=True)


class OllamaUsageMaximizer:
    """Maximizes Ollama usage while respecting system constraints."""

    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.gate = get_gate()  # Uses existing 4 concurrent limit
        self.running = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "start_time": None,
            "end_time": None,
            "models_used": {},
        }

        # Focus on smaller, more responsive models
        self.test_prompts = [
            "What is 2+2?",
            "Hello",
            "Hi",
            "Explain AI in one sentence.",
            "What is machine learning?",
            "List colors of rainbow.",
            "What is Python?",
            "Hello world",
            "Thanks",
            "Goodbye",
        ]

        # Prioritize smaller models that are likely to be more responsive
        self.models = [
            "phi3:mini",  # 3.8B - smallest and fastest
            "gemma3:4b",  # 4.3B
            "ministral-3:3b",  # 3.8B
            "qwen2.5-coder:7b",  # 7.6B
            "deepseek-r1:7b",  # 7.6B
            "mathstral:7b",  # 7.2B
            "qwen2-math:7b",  # 7.6B
        ]

    async def make_ollama_request(self, prompt: str, model: str) -> dict:
        """Make a single Ollama request with proper error handling."""
        start_time = time.perf_counter()

        try:
            # Create a new client for each request to avoid connection issues
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for faster, more deterministic responses
                        "num_predict": 64,  # Very short responses for maximum throughput
                    },
                }

                response = await client.post(f"{self.base_url}/api/generate", json=payload)

                end_time = time.perf_counter()
                latency = (end_time - start_time) * 1000  # Convert to milliseconds

                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")

                    # Update model usage stats
                    if model not in self.stats["models_used"]:
                        self.stats["models_used"][model] = 0
                    self.stats["models_used"][model] += 1

                    return {
                        "success": True,
                        "response": response_text,
                        "latency_ms": latency,
                        "model": model,
                        "prompt_length": len(prompt),
                        "response_length": len(response_text),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "latency_ms": latency,
                        "model": model,
                        "prompt_length": len(prompt),
                    }

        except Exception as e:
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000

            # Only log errors occasionally to avoid log spam
            if self.stats["total_requests"] % 50 == 0:
                logger.warning(f"Request failed ({model}): {str(e)[:100]}...")

            return {
                "success": False,
                "error": str(e)[:100],  # Truncate error message
                "latency_ms": latency,
                "model": model,
                "prompt_length": len(prompt),
            }

    async def worker(self, worker_id: int):
        """Worker that makes Ollama requests at a sustainable rate."""
        logger.info(f"Worker {worker_id} started")

        request_count = 0

        while self.running:
            # Respect the concurrency gate (max 4 concurrent requests)
            async with self.gate:
                # Select prompt and model - rotate through options
                import random

                prompt = random.choice(self.test_prompts)
                model = random.choice(self.models)

                # Make the request
                result = await self.make_ollama_request(prompt, model)

                # Update statistics
                self.stats["total_requests"] += 1
                if result["success"]:
                    self.stats["successful_requests"] += 1
                else:
                    self.stats["failed_requests"] += 1

                request_count += 1

                # Log progress periodically
                if request_count % 10 == 0:
                    logger.info(
                        f"Worker {worker_id}: {request_count} requests "
                        f"({self.stats['successful_requests']} success, {self.stats['failed_requests']} failed)"
                    )

                # Adaptive delay based on system pressure - shorter delay when successful
                if result["success"]:
                    await asyncio.sleep(0.1)  # Fast when working well
                else:
                    await asyncio.sleep(0.5)  # Slower when having issues

    async def run_maximization(self, duration_minutes: int = 60):
        """Run the usage maximization for specified duration."""
        logger.info(f"Starting Ollama usage maximization for {duration_minutes} minutes")

        self.running = True
        self.stats["start_time"] = datetime.now()

        # Start with fewer workers to avoid overwhelming the system
        # We can increase if we see the system handling it well
        workers = [
            asyncio.create_task(self.worker(i))
            for i in range(4)  # Start with 4 workers matching the gate limit
        ]

        # Run for specified duration
        await asyncio.sleep(duration_minutes * 60)

        # Stop all workers
        self.running = False
        self.stats["end_time"] = datetime.now()

        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)

        # Print final statistics
        await self.print_final_stats()

    async def print_final_stats(self):
        """Print and save final statistics."""
        duration = self.stats["end_time"] - self.stats["start_time"]
        hours = duration.total_seconds() / 3600

        # Calculate success rate
        success_rate = 0
        if self.stats["total_requests"] > 0:
            success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100

        stats_summary = {
            "test_duration_hours": hours,
            "total_requests": self.stats["total_requests"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "success_rate_percent": round(success_rate, 2),
            "requests_per_hour": round(self.stats["total_requests"] / max(hours, 0.01), 2),
            "models_used": self.stats["models_used"],
            "start_time": self.stats["start_time"].isoformat(),
            "end_time": self.stats["end_time"].isoformat(),
        }

        logger.info("=== OLLAMA USAGE MAXIMIZATION COMPLETE ===")
        logger.info(f"Duration: {hours:.2f} hours")
        logger.info(f"Total Requests: {stats_summary['total_requests']}")
        logger.info(f"Successful: {stats_summary['successful_requests']}")
        logger.info(f"Failed: {stats_summary['failed_requests']}")
        logger.info(f"Success Rate: {stats_summary['success_rate_percent']}%")
        logger.info(f"Requests/Hour: {stats_summary['requests_per_hour']}")
        logger.info(f"Models Used: {json.dumps(stats_summary['models_used'], indent=2)}")

        # Save stats to file
        stats_file = Path(
            f"/home/mike-anderson/dev/cohezion/data/ollama_maximization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        stats_file.parent.mkdir(exist_ok=True)
        stats_file.write_text(json.dumps(stats_summary, indent=2))
        logger.info(f"Statistics saved to {stats_file}")


async def main():
    """Main entry point."""
    import sys

    # Run for 6 hours by default (adjust based on remaining time)
    duration_hours = 6
    if len(sys.argv) > 1:
        try:
            duration_hours = float(sys.argv[1])
            # Cap at reasonable maximum to avoid running too long
            duration_hours = min(duration_hours, 12)
        except ValueError:
            logger.error("Invalid duration parameter. Using default of 6 hours.")

    maximizer = OllamaUsageMaximizer()
    await maximizer.run_maximization(duration_minutes=int(duration_hours * 60))


if __name__ == "__main__":
    asyncio.run(main())
