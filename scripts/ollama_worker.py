#!/usr/bin/env python3
"""
Ollama Research Worker - Queries models continuously
Tests different SLMs on physics questions
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


worker_id = sys.argv[1] if len(sys.argv) > 1 else "1"
output_dir = Path(f"/home/mike-anderson/dev/cohezion/data/overnight/ollama_{worker_id}")
output_dir.mkdir(parents=True, exist_ok=True)

# Rotate through available models
models = ["mistral:7b", "gemma3:4b", "phi3:mini", "qwen3-coder:30b", "falcon3:7b"]

research_questions = [
    "What is the relationship between consciousness and quantum coherence?",
    "Explain the HIHO principle in physics.",
    "How do Exotic Vacuum Objects (EVOs) form?",
    "What is the role of spin in particle stability?",
    "Describe toroidal field structures in plasma physics.",
]

print(f"🤖 Ollama Worker {worker_id} starting at {datetime.now()}", flush=True)

iteration = 0
responses_log = []

while True:
    iteration += 1
    model = models[iteration % len(models)]
    question = research_questions[iteration % len(research_questions)]

    start = datetime.now()

    try:
        result = subprocess.run(
            ["ollama", "run", model, question],
            capture_output=True,
            text=True,
            timeout=60,
        )

        response = result.stdout[:500]  # First 500 chars
        success = result.returncode == 0

    except subprocess.TimeoutExpired:
        response = "TIMEOUT"
        success = False
    except Exception as e:
        response = f"ERROR: {e!s}"
        success = False

    end = datetime.now()
    duration = (end - start).total_seconds()

    log_entry = {
        "worker_id": worker_id,
        "iteration": iteration,
        "timestamp": start.isoformat(),
        "model": model,
        "question": question,
        "response_preview": response,
        "duration_seconds": duration,
        "success": success,
    }

    responses_log.append(log_entry)

    print(
        f"[Ollama {worker_id}] Iter {iteration}: {model} answered in {duration:.1f}s",
        flush=True,
    )

    # Save every 5 iterations
    if iteration % 5 == 0:
        (output_dir / "responses.json").write_text(json.dumps(responses_log, indent=2))

    time.sleep(10)  # Cooldown between queries
