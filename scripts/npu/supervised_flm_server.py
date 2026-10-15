#!/usr/bin/env python3
"""Supervised FastFlowLM NPU Server Daemon.
========================================
Maintains continuous availability of FastFlowLM v1.0.8 on AMD XDNA 2 NPU (port 8006).
Features:
- Automatic crash recovery and clean respawn.
- Pre-flight port release to eliminate orphaned socket hangs.
- Zero UMA / zero ROCm RAM footprint.
"""

import argparse
import os
import signal
import subprocess
import sys
import time

FLM_BIN = "/var/cache/lemonade/bin/flm/npu/flm"
DEFAULT_PORT = 8005
DEFAULT_MODEL = "qwen3.5:4b"


def cleanup_existing():
    """Terminate any lingering flm-real processes."""
    try:
        out = subprocess.check_output(["pgrep", "-f", "flm-real"], text=True)
        for pid in out.strip().split():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except Exception:
                pass
        time.sleep(1.0)
    except Exception:
        pass


def run_supervisor(port: int = DEFAULT_PORT, model: str = DEFAULT_MODEL):
    print(f"[NPU Supervisor] Starting supervised FastFlowLM on port {port} with model {model}...")
    cleanup_existing()

    consecutive_crashes = 0
    while True:
        print(f"[NPU Supervisor] Launching {FLM_BIN} serve {model} --port {port} --socket 32 --q-len 32 --cors 1...")
        start_time = time.time()
        try:
            proc = subprocess.Popen(
                [
                    FLM_BIN,
                    "serve",
                    model,
                    "--port",
                    str(port),
                    "--pmode",
                    "performance",
                    "--socket",
                    "32",
                    "--q-len",
                    "32",
                    "--cors",
                    "1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Stream logs
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()

            proc.wait()
            ret = proc.returncode
            run_duration = time.time() - start_time
            print(f"[NPU Supervisor] FLM server exited with code {ret} after {run_duration:.1f}s.")

            if run_duration < 5.0:
                consecutive_crashes += 1
                sleep_time = min(2.0 * consecutive_crashes, 10.0)
            else:
                consecutive_crashes = 0
                sleep_time = 1.0

            print(f"[NPU Supervisor] Restarting in {sleep_time:.1f}s...")
            time.sleep(sleep_time)
            cleanup_existing()

        except KeyboardInterrupt:
            print("[NPU Supervisor] Shutting down supervisor cleanly.")
            break
        except Exception as e:
            print(f"[NPU Supervisor] Unexpected error: {e}. Retrying in 3s...")
            time.sleep(3.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supervised FastFlowLM Server Daemon")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to serve on")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model to serve")
    args = parser.parse_args()
    run_supervisor(port=args.port, model=args.model)
