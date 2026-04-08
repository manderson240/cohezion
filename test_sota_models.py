#!/usr/bin/env python3
"""Quick benchmark of SOTA small models (Apr 2026+)."""

import subprocess
import json
import time


def test_model(model: str, prompt: str):
    """Test single model via Ollama CLI."""
    print(f"\nTesting {model}...")
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 128}
    }
    
    start = time.time()
    
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate",
             "-d", json.dumps(payload)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        elapsed = (time.time() - start) * 1000
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
            tps = tokens / (elapsed / 1000) if elapsed > 0 else 0
            
            print(f"  ✓ Latency: {elapsed:.0f}ms")
            print(f"  ✓ Tokens: {tokens}")
            print(f"  ✓ Throughput: {tps:.1f} t/s")
            print(f"  ✓ Response: {data.get('response', '')[:80]}...")
            
            return {
                "model": model,
                "latency_ms": elapsed,
                "tokens": tokens,
                "tps": tps,
                "success": True,
            }
        else:
            print(f"  ✗ Failed: {result.stderr}")
            return {"model": model, "success": False, "error": result.stderr}
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return {"model": model, "success": False, "error": str(e)}


def main():
    prompt = "What is the capital of France?"
    models = [
        "gemma3:1b",
        "gemma3:4b",
        "llama3.2:1b",
        "llama3.2:3b",
        "phi4",
        "deepseek-r1:1.5b",
    ]
    
    print("=" * 60)
    print("SOTA Small Models Quick Test (Apr 2026+)")
    print("=" * 60)
    
    results = []
    for model in models:
        result = test_model(model, prompt)
        results.append(result)
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for r in results:
        if r.get("success"):
            print(f"{r['model']:<20} {r['latency_ms']:.0f}ms  {r['tps']:.1f} t/s")
        else:
            print(f"{r['model']:<20} FAILED")


if __name__ == "__main__":
    main()
