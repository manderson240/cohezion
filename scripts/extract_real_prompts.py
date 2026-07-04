#!/usr/bin/env python3
"""
Extract Real Prompts (Task 2.1)

Parses execution_traces/ and queries SurrealDB database to extract
real-world prompt signals for classifier validation.
"""

import json
import os
import sys
from pathlib import Path

# Ensure import paths are set
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from cohezion.core.persistence.surreal_client import SurrealClient
except ImportError:
    SurrealClient = None


def extract_from_traces() -> list[str]:
    """Scan execution_traces/unified/ for prompts (or digests)."""
    trace_dir = Path("execution_traces/unified")
    prompts = []
    if not trace_dir.exists():
        return prompts

    for path in trace_dir.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # If there's a prompt or content, extract it
                if "prompt" in data:
                    prompts.append(data["prompt"])
                elif "content" in data:
                    prompts.append(data["content"])
                elif "prompt_digest" in data:
                    # Trace JSONs store digests, not the full prompt text due to storage optimization
                    pass
        except Exception:
            pass
    return prompts


async def extract_from_surreal() -> list[str]:
    """Query SurrealDB for document contents or agent thoughts."""
    prompts = []
    if not SurrealClient:
        return prompts

    os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"
    client = SurrealClient()
    try:
        await client.connect()
        # Query universe_nodes for document contents or metadata prompts
        res = await client.query(
            "SELECT content FROM universe_nodes WHERE node_type = 'document' LIMIT 50"
        )
        if res and isinstance(res, list):
            rows = []
            if len(res) > 0 and isinstance(res[0], dict) and "result" in res[0]:
                rows = res[0]["result"]
            else:
                rows = res
            for row in rows:
                if isinstance(row, dict):
                    content = row.get("content", "")
                    if content and len(content.strip()) > 50:
                        prompts.append(content.strip())
    except Exception as e:
        print(f"SurrealDB query failed: {e}", file=sys.stderr)
    return prompts


async def main():
    print("Extracting prompts from execution_traces/...")
    trace_prompts = extract_from_traces()
    print(f"Extracted {len(trace_prompts)} prompts from execution_traces.")

    print("Querying SurrealDB for prompts/documents...")
    db_prompts = await extract_from_surreal()
    print(f"Extracted {len(db_prompts)} prompts from SurrealDB.")

    all_prompts = list(set(trace_prompts + db_prompts))
    print(f"Total unique prompts extracted: {len(all_prompts)}")

    # Save to a structured file for Task 2.2 benchmark ingestion
    output_path = Path("execution_traces/extracted_prompts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_prompts, f, indent=2)
    print(f"Saved extracted prompts to {output_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
