#!/usr/bin/env python3
"""GPU Utilization Monitor for Lemonade Inference Optimization.

Uses AMD ROCm SMI to monitor GPU metrics during inference.

Usage:
    # Terminal 1: Start monitoring
    python monitor_gpu.py

    # Terminal 2: Run benchmark
    python benchmark_quick.py
"""

import subprocess
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class GPUMetrics:
    timestamp: float
    gpu_use: float
    vram_use: float
    power: float
    temperature: float

    @classmethod
    def from_rocm_smi(cls, smi_output: str) -> Optional["GPUMetrics"]:
        """Parse ROCm SMI output."""
        try:
            lines = smi_output.strip().split("\n")
            data_line = None
            for line in lines:
                if line.startswith("0") and "1" in line:  # Device 0, Node 1
                    data_line = line
                    break

            if not data_line:
                return None

            parts = data_line.split()
            return cls(
                timestamp=time.time(),
                gpu_use=float(parts[6]) if len(parts) > 6 else 0,
                vram_use=float(parts[11].rstrip("%")) if len(parts) > 11 else 0,
                power=float(parts[4].rstrip("W")) if len(parts) > 4 else 0,
                temperature=float(parts[3].rstrip("°C")) if len(parts) > 3 else 0,
            )
        except Exception:
            return None


def monitor_gpu(duration: int = 60, interval: float = 0.5):
    """Monitor GPU for specified duration."""
    print("=" * 70)
    print("GPU MONITOR (AMD ROCm)")
    print("=" * 70)
    print(f"Duration: {duration}s | Interval: {interval}s")
    print("-" * 70)
    print(f"{'Time':>6} {'GPU%':>6} {'VRAM%':>7} {'Power':>8} {'Temp':>6} {'Status':>10}")
    print("-" * 70)

    metrics_history = deque(maxlen=100)
    start_time = time.time()

    while time.time() - start_time < duration:
        try:
            # Get GPU metrics
            result = subprocess.run(["rocm-smi"], capture_output=True, text=True, timeout=2)

            metrics = GPUMetrics.from_rocm_smi(result.stdout)

            if metrics:
                metrics_history.append(metrics)

                # Determine status
                status = (
                    "IDLE"
                    if metrics.gpu_use < 10
                    else "LOW"
                    if metrics.gpu_use < 40
                    else "MODERATE"
                    if metrics.gpu_use < 70
                    else "HIGH"
                    if metrics.gpu_use < 90
                    else "SATURATED"
                )

                print(
                    f"{time.time() - start_time:>6.1f} "
                    f"{metrics.gpu_use:>6.1f} "
                    f"{metrics.vram_use:>7.1f} "
                    f"{metrics.power:>7.1f}W "
                    f"{metrics.temperature:>5.1f}°C "
                    f"{status:>10}"
                )
            else:
                print(f"{time.time() - start_time:>6.1f} [NO DATA]")

            time.sleep(interval)

        except subprocess.TimeoutExpired:
            print(f"{time.time() - start_time:>6.1f} [TIMEOUT]")
            time.sleep(interval)
        except KeyboardInterrupt:
            break

    # Summary
    if metrics_history:
        print("-" * 70)
        print("SUMMARY")
        print("-" * 70)
        avg_gpu = sum(m.gpu_use for m in metrics_history) / len(metrics_history)
        max_gpu = max(m.gpu_use for m in metrics_history)
        avg_power = sum(m.power for m in metrics_history) / len(metrics_history)

        print(f"Average GPU Util: {avg_gpu:.1f}%")
        print(f"Peak GPU Util:    {max_gpu:.1f}%")
        print(f"Average Power:    {avg_power:.1f}W")
        print(f"Samples:          {len(metrics_history)}")

        # Recommendation
        if max_gpu < 50:
            print(f"\n⚠️  UNDERUTILIZED: GPU peaked at {max_gpu:.1f}%")
            print("   Try increasing concurrency or batch size")
        elif max_gpu > 90:
            print(f"\n✅ SATURATED: GPU peaked at {max_gpu:.1f}%")
            print("   Good utilization, may be throughput limited by memory")
        else:
            print(f"\n✓ MODERATE: GPU peaked at {max_gpu:.1f}%")
            print("   Reasonable utilization for inference workload")

    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor GPU utilization")
    parser.add_argument(
        "-d", "--duration", type=int, default=60, help="Monitoring duration in seconds"
    )
    parser.add_argument(
        "-i", "--interval", type=float, default=0.5, help="Sample interval in seconds"
    )
    args = parser.parse_args()

    try:
        monitor_gpu(args.duration, args.interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
