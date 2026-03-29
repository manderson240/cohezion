# AIMO Sprint Troubleshooting Retrospective

## Context
During the overnight 4-hour and 8-hour autonomous research sprints for the AIMO Progress Prize 3 track, the Mathematical Reasoning Swarm repeatedly encountered stalling issues and failed to score above 0.0 accuracy on the local benchmark.

## Identified Issues & Root Causes

1.  **Ollama API Timeout & "Infinite Hang"**
    *   **Symptom**: The main research loop (`math_research_sprint.py`) would hang indefinitely without throwing an error, eventually causing the system load to skyrocket.
    *   **Root Cause**: Complex reasoning tasks (especially on local CPU or when falling back from a busy GPU) take longer than the default `requests.post` timeout. Without an explicit timeout, the Python `requests` library blocks forever waiting for a response from the Ollama server.
    *   **Fix**: Added an explicit `timeout=300` (5 minutes) to all `requests.post` calls in `BaseSpecialist`. Increased `num_thread` to 16 in the payload options to maximize local CPU utilization if the GPU is busy.

2.  **Silent Extraction Failures (Error-as-Answer)**
    *   **Symptom**: The extracted answer would sometimes be a completely unrelated number like `180`.
    *   **Root Cause**: When Ollama did timeout or throw an HTTP error, the `except` block returned the error string (e.g., `"Error calling Ollama: Read timed out. (read timeout=180)"`). The `extract_answer` method used a greedy regex (`\d+`) as a fallback, which caught the "180" from the error message and returned it as the math answer.
    *   **Fix**: Modified `extract_answer` to explicitly check for `response_text.startswith("Error")` and return `0` immediately, bypassing regex extraction on error tracebacks.

3.  **Dependency Desync & Silent Loop Failures (`pd` not defined)**
    *   **Symptom**: The LLM-driven `propose_mutation` logic was silently failing and repeatedly proposing a "Fallback: Basic refinement." mutation.
    *   **Root Cause**: The `pandas` library (`import pandas as pd`) was missing from the `math_research_harness.py` scope after a refactor, causing the LLM context-gathering block to throw a `NameError`. Because the script had a blanket `except Exception as e` that triggered the fallback, this critical error was buried.
    *   **Fix**: Migrated from `pandas` to `polars` across the entire AIMO subsystem (`mock_aimo_api.py`, `swarm_driver.py`, etc.) for higher performance and explicitly added `import polars as pl`. Fixed all data frame access logic.

4.  **Process Management & Zombie Swarms**
    *   **Symptom**: Multiple instances of the sprint script and Ollama models were running simultaneously, leading to an OOM (Out Of Memory) or near-OOM state (System load 24+).
    *   **Root Cause**: Hard-killing bash commands via `kill` without cleaning up child processes left `uv run` and `python` scripts orphaned.
    *   **Fix**: Centralized process management using `ps aux | grep ... | xargs kill -9` before starting any new sprint, ensuring a completely clean state.

## Prevention & Best Practices
- **Robustness**: All API calls must have explicit timeouts.
- **Fail-Safes**: Fallback logic must never mask `NameError` or `ImportError`.
- **Worktree Isolation**: Development of concurrent, high-intensity swarms should be isolated via Git Worktrees to prevent file state corruption when multiple agents or loops are active.
