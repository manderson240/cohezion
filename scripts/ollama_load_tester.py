#!/usr/bin/env python3
"""
Ollama Load Tester - Pushes Ollama usage to limits before reset
Maximizes concurrent requests within gate limits and runs continuously
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from cohezion.concurrency.ollama_gate import get_gate
from cohezion.swarm.ollama_resilience import ResilientOllamaClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/mike-anderson/dev/cohezion/logs/ollama_load_test.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
Path("/home/mike-anderson/dev/cohezion/logs").mkdir(exist_ok=True)


class OllamaLoadTester:
    """Intensive Ollama load tester to maximize usage before limits reset."""

    def __init__(self):
        self.client = ResilientOllamaClient()
        self.gate = get_gate()  # Respects the 4 concurrent limit
        self.running = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "start_time": None,
            "end_time": None,
        }

        # Mix of different prompt sizes and complexities
        self.test_prompts = [
            # Short prompts
            "What is 2+2?",
            "Explain quantum entanglement in one sentence.",
            "List three benefits of exercise.",
            # Medium prompts
            "Explain the difference between machine learning and deep learning.",
            "What are the ethical implications of artificial intelligence?",
            "Describe the process of photosynthesis in simple terms.",
            # Longer prompts
            "Write a short essay about the impact of renewable energy on climate change, including solar, wind, and hydroelectric power.",
            "Explain how blockchain technology works and its potential applications beyond cryptocurrency.",
            "Compare and contrast renewable and non-renewable energy sources, discussing their environmental impacts.",
            # Complex reasoning
            "If a train leaves Station A at 2:00 PM traveling at 60 mph toward Station B, which is 180 miles away, and another train leaves Station B at 3:00 PM traveling at 80 mph toward Station A, at what time will they meet?",
            "Analyze the causes and effects of the Industrial Revolution on modern society, focusing on technological, social, and economic changes.",
        ]

        # Available models to rotate through
        self.models = [
            "phi3:mini",
            "gemma3:4b",
            "qwen2.5-coder:7b",
            "mistral:7b",
            "deepseek-r1:7b",
            "nemotron-3-nano:30b",  # Largest local model
        ]

    async def make_ollama_request(self, prompt: str, model: str) -> dict:
        """Make a single Ollama request with timing."""
        start_time = time.perf_counter()

        try:
            # Use the resilient client which respects circuit breaker and retries
            response = await self.client.generate(
                prompt=prompt,
                model=model,
                temperature=0.7,
                num_predict=512,  # Limit response length for faster turnover
            )

            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds

            return {
                "success": True,
                "response": response,
                "latency_ms": latency,
                "model": model,
                "prompt_length": len(prompt),
                "response_length": len(response),
            }

        except Exception as e:
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000

            logger.warning(f"Request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": latency,
                "model": model,
                "prompt_length": len(prompt),
            }

    async def worker(self, worker_id: int):
        """Worker that continuously makes Ollama requests."""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            # Respect the concurrency gate (max 4 concurrent requests)
            async with self.gate:
                # Select random prompt and model
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

                # Log periodically
                if self.stats["total_requests"] % 10 == 0:
                    logger.info(
                        f"Worker {worker_id}: {self.stats['total_requests']} total requests "
                        f"({self.stats['successful_requests']} success, {self.stats['failed_requests']} failed)"
                    )

                # Brief pause to avoid overwhelming the system
                await asyncio.sleep(0.1)

    async def run_load_test(self, duration_minutes: int = 60):
        """Run the load test for specified duration."""
        logger.info(f"Starting Ollama load test for {duration_minutes} minutes")

        self.running = True
        self.stats["start_time"] = datetime.now()

        # Create and start multiple workers to maximize gate utilization
        # Using 8 workers to ensure we consistently hit the 4 concurrent limit
        workers = [asyncio.create_task(self.worker(i)) for i in range(8)]

        # Run for specified duration
        await asyncio.sleep(duration_minutes * 60)

        # Stop all workers
        self.running = False
        self.stats["end_time"] = datetime.now()

        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)

        # Close the client
        await self.client.close()

        # Print final statistics
        await self.print_final_stats()

    async def print_final_stats(self):
        """Print and save final statistics."""
        duration = self.stats["end_time"] - self.stats["start_time"]
        hours = duration.total_seconds() / 3600

        stats_summary = {
            "test_duration_hours": hours,
            "total_requests": self.stats["total_requests"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "success_rate": (
                self.stats["successful_requests"] / max(self.stats["total_requests"], 1)
            )
            * 100,
            "requests_per_hour": self.stats["total_requests"] / max(hours, 0.01),
            "start_time": self.stats["start_time"].isoformat(),
            "end_time": self.stats["end_time"].isoformat(),
        }

        logger.info("=== OLLAMA LOAD TEST COMPLETE ===")
        logger.info(f"Duration: {hours:.2f} hours")
        logger.info(f"Total Requests: {stats_summary['total_requests']}")
        logger.info(f"Successful: {stats_summary['successful_requests']}")
        logger.info(f"Failed: {stats_summary['failed_requests']}")
        logger.info(f"Success Rate: {stats_summary['success_rate']:.1f}%")
        logger.info(f"Requests/Hour: {stats_summary['requests_per_hour']:.0f}")

        # Save stats to file
        stats_file = Path(
            f"/home/mike-anderson/dev/cohezion/data/ollama_load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        stats_file.parent.mkdir(exist_ok=True)
        stats_file.write_text(json.dumps(stats_summary, indent=2))
        logger.info(f"Statistics saved to {stats_file}")


async def main():
    """Main entry point."""
    import sys

    # Default to 12 hours (half day) but can be overridden
    duration_hours = 12
    if len(sys.argv) > 1:
        try:
            duration_hours = float(sys.argv[1])
        except ValueError:
            logger.error("Invalid duration parameter. Using default of 12 hours.")

    tester = OllamaLoadTester()
    await tester.run_load_test(duration_minutes=int(duration_hours * 60))


if __name__ == "__main__":
    asyncio.run(main())
