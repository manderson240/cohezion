#!/usr/bin/env python3
"""
Fixed Ollama Load Tester - Pushes Ollama usage to limits before reset
Uses direct HTTP calls to Ollama API with proper error handling
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
        logging.FileHandler("/home/mike-anderson/dev/cohezion/logs/ollama_load_test_fixed.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
Path("/home/mike-anderson/dev/cohezion/logs").mkdir(exist_ok=True)


class OllamaLoadTesterFixed:
    """Fixed Ollama load tester to maximize usage before limits reset."""

    def __init__(self):
        self.base_url = "http://localhost:11434"
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
            "Hello",
            "Hi",
            # Medium prompts
            "Explain the difference between machine learning and deep learning.",
            "What are the ethical implications of artificial intelligence?",
            "Describe the process of photosynthesis in simple terms.",
            "What is the capital of France?",
            "Who wrote Romeo and Juliet?",
            # Longer prompts
            "Write a short essay about the impact of renewable energy on climate change, including solar, wind, and hydroelectric power.",
            "Explain how blockchain technology works and its potential applications beyond cryptocurrency.",
            "Compare and contrast renewable and non-renewable energy sources, discussing their environmental impacts.",
            "What are the main causes of climate change and what can individuals do to help?",
            "Explain the concept of supply and demand in economics with examples.",
        ]

        # Available models to rotate through - focusing on smaller models for faster response
        self.models = [
            "phi3:mini",
            "gemma3:4b",
            "qwen2.5-coder:7b",
            "mistral:7b",
            "deepseek-r1:7b",
        ]

    async def make_ollama_request(self, prompt: str, model: str) -> dict:
        """Make a single Ollama request with timing using direct HTTP."""
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 256,  # Limit response length for faster turnover
                    },
                }

                response = await client.post(f"{self.base_url}/api/generate", json=payload)

                end_time = time.perf_counter()
                latency = (end_time - start_time) * 1000  # Convert to milliseconds

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "response": data.get("response", ""),
                        "latency_ms": latency,
                        "model": model,
                        "prompt_length": len(prompt),
                        "response_length": len(data.get("response", "")),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "latency_ms": latency,
                        "model": model,
                        "prompt_length": len(prompt),
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
                if self.stats["total_requests"] % 5 == 0:
                    logger.info(
                        f"Worker {worker_id}: {self.stats['total_requests']} total requests "
                        f"({self.stats['successful_requests']} success, {self.stats['failed_requests']} failed)"
                    )

                # Brief pause to avoid overwhelming the system
                await asyncio.sleep(0.5)

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
            f"/home/mike-anderson/dev/cohezion/data/ollama_load_test_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        stats_file.parent.mkdir(exist_ok=True)
        stats_file.write_text(json.dumps(stats_summary, indent=2))
        logger.info(f"Statistics saved to {stats_file}")


async def main():
    """Main entry point."""
    import sys

    # Default to 4 hours to really push usage but not overload
    duration_hours = 4
    if len(sys.argv) > 1:
        try:
            duration_hours = float(sys.argv[1])
        except ValueError:
            logger.error("Invalid duration parameter. Using default of 4 hours.")

    tester = OllamaLoadTesterFixed()
    await tester.run_load_test(duration_minutes=int(duration_hours * 60))


if __name__ == "__main__":
    asyncio.run(main())
