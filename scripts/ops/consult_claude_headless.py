#!/usr/bin/env python3
"""Unified Headless Claude Code consultation utility.

Dispatches prompts directly through `claude -p` across the full model suite:
- haiku: ultra-fast screening, triage, text sanitization
- sonnet: complex architecture, deep code refactoring, AST verification
- opus: grandmaster synthesis, mathematical proofs, frontier reasoning
"""

import argparse
import json
import subprocess
import sys


def run_claude_headless(prompt: str, model: str = "sonnet", timeout: int = 180) -> str:
    cmd = ["claude", "-p", "--model", model, prompt]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error ({e.returncode}): {e.stderr}"
    except Exception as e:
        return f"Execution failed: {e}"


def main():
    parser = argparse.ArgumentParser(description="Query headless Claude models")
    parser.add_argument("prompt", help="Prompt to send")
    parser.add_argument("--model", choices=["haiku", "sonnet", "opus"], default="sonnet")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    out = run_claude_headless(args.prompt, model=args.model, timeout=args.timeout)
    print(out)


if __name__ == "__main__":
    main()
