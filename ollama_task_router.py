#!/usr/bin/env python3
"""Ollama task router for Gemma4 offload."""

import subprocess
import sys

def query_ollama(prompt, model="gemma4"):
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.stdout
    except:
        return "[OLLAMA UNAVAILABLE]"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            prompt = f.read()
    else:
        prompt = sys.stdin.read()
    print(query_ollama(prompt))
