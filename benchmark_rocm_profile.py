#!/usr/bin/env python3
"""Profile Lemonade inference using AMD ROCm profiler.

Uses rocprof to gather GPU utilization, memory bandwidth, and kernel performance.
Requires ROCm 7.2.1+ to be installed.
"""

import asyncio
import subprocess
from pathlib import Path


async def run_with_profiling():
    """Run inference with ROCm profiling enabled."""

    print("=" * 70)
    print("ROCm PROFILING ANALYSIS - Lemonade Inference")
    print("=" * 70)

    # Create profile file for rocprof
    profile_cfg = """
pmc:
  # GPU Utilization
  - GPUBusy
  - VALUUtilization
  
  # Memory metrics
  - TCC_HIT_sum
  - TCC_MISS_sum
  - TCC_EA_RDREQ_32B_sum
  - TCC_EA_WRREQ_32B_sum
  
  # Shader engine
  - VALUInstCount
  - SALUInstCount
  - VFetchInstCount
  - VWriteInstCount
"""

    config_path = Path("/tmp/rocprof_cfg.txt")
    config_path.write_text(profile_cfg)

    # Create test script
    test_script = '''#!/usr/bin/env python3
import asyncio
import aiohttp
import time

async def main():
    connector = aiohttp.TCPConnector(limit=4)
    async with aiohttp.ClientSession(connector=connector) as session:
        prompts = ["Write haiku about ML " + str(i) for i in range(4)]
        tasks = []
        for p in prompts:
            payload = {
                "model": "DeepSeek-Qwen3-8B-GGUF",
                "messages": [{"role": "user", "content": p}],
                "max_tokens": 40,
                "temperature": 0.7,
            }
            tasks.append(session.post(
                "http://localhost:8002/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ))
        responses = await asyncio.gather(*tasks)
        for r in responses:
            await r.json()

asyncio.run(main())
'''

    script_path = Path("/tmp/inference_test.py")
    script_path.write_text(test_script)
    script_path.chmod(0o755)

    print("\nRunning rocprof... (this may take 30-60 seconds)")

    try:
        # Run rocprof
        result = subprocess.run(
            ["rocprof", "-i", str(config_path),
             "-o", "/tmp/rocprof_results.csv",
             "python3", str(script_path)],
            capture_output=True,
            text=True,
            timeout=120
        )

        print("\nROCm Profiling Complete")
        print("=" * 70)

        # Parse results
        results_csv = Path("/tmp/rocprof_results.csv")
        if results_csv.exists():
            lines = results_csv.read_text().strip().split('\n')
            print(f"\nCollected {len(lines)} profiling records")

            # Show header and first few lines
            if lines:
                print("\nMetrics collected:")
                print(lines[0])
                for line in lines[1:5]:
                    print(line)
                if len(lines) > 5:
                    print(f"... and {len(lines) - 5} more")

        print("\nROCm SMI Status:")
        smi_result = subprocess.run(
            ["rocm-smi"],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(smi_result.stdout[:1000] if smi_result.stdout else "N/A")

        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Profiling timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_with_profiling())
    exit(0 if success else 1)
