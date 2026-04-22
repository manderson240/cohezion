"""Debug Gemma-4 response format."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
from model_dispatcher import ModelDispatcher

with open("/tmp/train.csv") as f:
    rows = list(csv.DictReader(f))

# Get an encryption example
enc_rows = [r for r in rows if "encryption" in r["prompt"].lower()]
r = enc_rows[0]

print(f"Prompt ({len(r['prompt'])} chars):")
print(r["prompt"][:300])
print(f"\nExpected answer: {r['answer']}")

dispatcher = ModelDispatcher()
result = dispatcher.generate(
    "You are a puzzle-solving expert. Given examples, infer the rule and apply it. Output ONLY the answer.",
    r["prompt"],
    max_tokens=128,
    temperature=0.0,
)
print(f"\nModel response: {repr(result.text)}")
print(f"Tokens used: {result.tokens_used}")
print(f"Duration: {result.duration_ms}ms")
