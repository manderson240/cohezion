#!/usr/bin/env python3
"""
Experiential Learning Git Hook

This hook runs on post-commit (or pre-push) to automatically capture
experiential learning using local inference. It analyzes the recent
commit diff against the Systems Engineering V-Model and ARC lessons,
extracting a structured learning record that is stored via the
Compound MCP server.
"""

import os
import sys
import json
import subprocess
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
# Use a fast local model for the hook
MODEL_NAME = "qwen3.5:0.8b"
COMPOUND_SERVER_URL = "http://localhost:8379/mcp"
VAULT_URL = "http://localhost:8360"


def get_recent_diff():
    """Get the diff of the most recent commit."""
    try:
        # Get diff of the latest commit
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"], capture_type=True, text=True, check=True
        )
        return result.stdout
    except Exception as e:
        print(f"Error getting git diff: {e}")
        return ""


def get_commit_msg():
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "Unknown commit"


def analyze_diff_with_local_inference(diff: str, commit_msg: str):
    """Use local Ollama to extract experiential learning."""
    if not diff:
        return None

    prompt = f"""
You are the Cohezion Retrospection Engine. Analyze the following commit diff and message to extract an experiential learning record.

Context to cross-reference:
1. Systems Engineering V-Model: Classify this as Descending (Design), Apex (Implementation), or Ascending (Validation).
2. ARC Lessons: Ensure we favor symbolic reasoning over statistical matching, rely on vision for interactive environments, and emphasize experiential learning.

Commit Message: {commit_msg}

Diff (truncated to 2000 chars): {diff[:2000]}

Respond ONLY with a valid JSON object matching this schema:
{{
  "request": "A short summary of the task",
  "tokens_used": 0,
  "cache_hits": 0,
  "duration_seconds": 1,
  "coherence": 0.85,
  "success": true,
  "skill_used": "vmodel_synthesis",
  "lessons": [
    "Lesson 1...",
    "Lesson 2 relating to ARC or V-Model..."
  ]
}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        result_text = response.json().get("response", "{}")
        return json.loads(result_text)
    except Exception as e:
        print(f"Local inference failed: {e}")
        return None


def capture_learning_via_mcp(execution_result: dict):
    """Call the compound MCP server to persist the learning."""
    try:
        # Add src to path to import mcp_client
        sys.path.append(os.path.join(os.getcwd(), "src"))
        from cohezion.core.mcp_client import create_mcp_client
        import asyncio

        async def _do_capture():
            client = create_mcp_client(
                server_url="http://localhost:8379", api_key="cohezion-dev-key"
            )
            await client.connect()
            # Pass the execution result to the server
            response = await client._call_tool(
                "learning_process_execution",
                {"execution_result_json": json.dumps(execution_result), "server_url": VAULT_URL},
            )
            return response

        return asyncio.run(_do_capture())
    except Exception as e:
        print(f"MCP Capture failed: {e}")
        return None


def main():
    print("Running Experiential Learning Hook (Local Inference)...")

    diff = get_recent_diff()
    commit_msg = get_commit_msg()

    if not diff:
        print("No diff found, skipping learning capture.")
        return 0

    print("Analyzing commit against V-Model and ARC lessons using local LLM...")
    execution_result = analyze_diff_with_local_inference(diff, commit_msg)

    if execution_result:
        print(f"Extracted learning: {execution_result.get('request')}")
        print(f"Lessons: {execution_result.get('lessons', [])}")

        print("Capturing to Obsidian Vault and SurrealDB...")
        mcp_res = capture_learning_via_mcp(execution_result)
        if mcp_res:
            print("Capture complete!")
    else:
        print("Failed to extract learning structure.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
