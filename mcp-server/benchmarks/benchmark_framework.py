#!/usr/bin/env python3
"""
Comprehensive Performance Benchmarking Framework for Kyutai MCP Server and Obsidian Plugin.

This framework captures baselines for:
1. MCP tool latencies (ms)
2. System resource usage (CPU, memory, I/O)
3. Throughput under concurrent load
4. Network performance (HTTP, WebSocket)
5. End-to-end workflow timings
"""

import asyncio
import json
import logging
import os
import platform
import psutil
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from statistics import mean, median, stdev

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Single benchmark measurement result."""
    test_name: str
    duration_ms: float
    timestamp: str
    environment: str
    status: str  # 'success' or 'error'
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'test_name': self.test_name,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp,
            'environment': self.environment,
            'status': self.status,
            'error_message': self.error_message,
            'metadata': self.metadata or {},
        }


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics."""
    test_name: str
    runs: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    stddev_ms: float
    p95_ms: float
    p99_ms: float


class SystemProfiler:
    """Capture system resource usage."""

    def __init__(self):
        self.baseline_memory_mb = None
        self.baseline_cpu_percent = None
        self.process = psutil.Process()

    def capture_baseline(self) -> Dict[str, Any]:
        """Capture baseline system metrics."""
        self.baseline_memory_mb = self.process.memory_info().rss / 1024 / 1024
        self.baseline_cpu_percent = self.process.cpu_percent(interval=0.1)

        return {
            'baseline_memory_mb': self.baseline_memory_mb,
            'baseline_cpu_percent': self.baseline_cpu_percent,
            'process_pid': self.process.pid,
            'system_cpu_count': psutil.cpu_count(),
            'system_memory_mb': psutil.virtual_memory().total / 1024 / 1024,
        }

    def measure_resources(self) -> Dict[str, Any]:
        """Measure current resource usage."""
        memory_info = self.process.memory_info()
        current_memory_mb = memory_info.rss / 1024 / 1024
        current_cpu_percent = self.process.cpu_percent(interval=0.1)

        return {
            'memory_mb': current_memory_mb,
            'memory_delta_mb': current_memory_mb - (self.baseline_memory_mb or 0),
            'memory_rss_mb': memory_info.rss / 1024 / 1024,
            'memory_vms_mb': memory_info.vms / 1024 / 1024,
            'cpu_percent': current_cpu_percent,
            'num_threads': self.process.num_threads(),
            'num_fds': self.process.num_fds() if hasattr(self.process, 'num_fds') else None,
        }


class LatencyMeasurement:
    """Measure tool and operation latencies."""

    @staticmethod
    async def measure_http_latency(
        url: str,
        method: str = 'GET',
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Tuple[float, Optional[str]]:
        """Measure HTTP request latency."""
        import aiohttp

        start_time = time.perf_counter()
        error_msg = None

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                if method == 'GET':
                    async with session.get(url) as resp:
                        await resp.text()
                elif method == 'POST':
                    async with session.post(url, json=payload) as resp:
                        await resp.json()
        except Exception as e:
            error_msg = str(e)

        duration_ms = (time.perf_counter() - start_time) * 1000
        return duration_ms, error_msg

    @staticmethod
    def measure_operation_latency(
        operation_func,
        *args,
        **kwargs,
    ) -> Tuple[float, Any, Optional[str]]:
        """Measure synchronous operation latency."""
        start_time = time.perf_counter()
        result = None
        error_msg = None

        try:
            result = operation_func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)

        duration_ms = (time.perf_counter() - start_time) * 1000
        return duration_ms, result, error_msg


class ThroughputTester:
    """Test throughput under concurrent load."""

    @staticmethod
    async def concurrent_requests(
        url: str,
        payload: Dict[str, Any],
        concurrent_count: int,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Execute concurrent requests."""
        import aiohttp

        durations = []
        errors = 0
        successful = 0

        async def make_request():
            nonlocal successful, errors
            try:
                duration, error = await LatencyMeasurement.measure_http_latency(
                    url, 'POST', payload, timeout
                )
                if error:
                    errors += 1
                else:
                    successful += 1
                    durations.append(duration)
            except Exception as e:
                errors += 1

        # Create concurrent tasks
        tasks = [make_request() for _ in range(concurrent_count)]
        await asyncio.gather(*tasks)

        if durations:
            durations_sorted = sorted(durations)
            p95_idx = int(len(durations_sorted) * 0.95)
            p99_idx = int(len(durations_sorted) * 0.99)

            return {
                'concurrent_count': concurrent_count,
                'successful': successful,
                'errors': errors,
                'error_rate': errors / concurrent_count if concurrent_count > 0 else 0,
                'latency': {
                    'min_ms': min(durations),
                    'max_ms': max(durations),
                    'mean_ms': mean(durations),
                    'median_ms': median(durations),
                    'p95_ms': durations_sorted[p95_idx] if p95_idx < len(durations_sorted) else 0,
                    'p99_ms': durations_sorted[p99_idx] if p99_idx < len(durations_sorted) else 0,
                },
                'throughput_req_per_sec': successful / (sum(durations) / 1000) if sum(durations) > 0 else 0,
            }
        else:
            return {
                'concurrent_count': concurrent_count,
                'successful': 0,
                'errors': concurrent_count,
                'error_rate': 1.0,
                'latency': {},
                'throughput_req_per_sec': 0,
            }


class BenchmarkSuite:
    """Orchestrate benchmark execution."""

    def __init__(self, mcp_server_url: str = 'http://localhost:8000'):
        self.mcp_server_url = mcp_server_url
        self.results: List[BenchmarkResult] = []
        self.profiler = SystemProfiler()
        self.environment_info = self._collect_environment_info()

    def _collect_environment_info(self) -> Dict[str, Any]:
        """Collect environment metadata."""
        return {
            'os': platform.system(),
            'os_version': platform.release(),
            'python_version': sys.version,
            'processor': platform.processor(),
            'hostname': platform.node(),
            'timestamp': datetime.now().isoformat(),
            'system_baseline': self.profiler.capture_baseline(),
        }

    async def run_server_latency_tests(self, runs: int = 10) -> Dict[str, PerformanceMetrics]:
        """Benchmark MCP server tool latencies."""
        logger.info(f"Starting server latency tests ({runs} runs each)...")

        tools = [
            ('health_check', {}),
            ('list_models', {'category': 'all'}),
            ('get_model_status', {}),
        ]

        results = {}

        for tool_name, params in tools:
            logger.info(f"  Testing {tool_name}...")
            durations = []

            for run in range(runs):
                try:
                    url = f"{self.mcp_server_url}/mcp/call"
                    payload = {'tool': tool_name, 'params': params}

                    start_time = time.perf_counter()
                    duration_ms, error = await LatencyMeasurement.measure_http_latency(
                        url, 'POST', payload
                    )

                    if error:
                        logger.warning(f"    Run {run+1}/{runs}: ERROR - {error}")
                    else:
                        durations.append(duration_ms)
                        logger.debug(f"    Run {run+1}/{runs}: {duration_ms:.2f}ms")

                except Exception as e:
                    logger.warning(f"    Run {run+1}/{runs}: EXCEPTION - {e}")

            if durations:
                durations_sorted = sorted(durations)
                p95_idx = int(len(durations_sorted) * 0.95)
                p99_idx = int(len(durations_sorted) * 0.99)

                metrics = PerformanceMetrics(
                    test_name=f'server_latency_{tool_name}',
                    runs=len(durations),
                    min_ms=min(durations),
                    max_ms=max(durations),
                    mean_ms=mean(durations),
                    median_ms=median(durations),
                    stddev_ms=stdev(durations) if len(durations) > 1 else 0,
                    p95_ms=durations_sorted[p95_idx] if p95_idx < len(durations_sorted) else 0,
                    p99_ms=durations_sorted[p99_idx] if p99_idx < len(durations_sorted) else 0,
                )
                results[tool_name] = metrics
                logger.info(f"  {tool_name}: {metrics.mean_ms:.2f}ms (median: {metrics.median_ms:.2f}ms)")

        return results

    async def run_throughput_tests(self) -> Dict[str, Any]:
        """Benchmark server throughput under concurrent load."""
        logger.info("Starting throughput tests...")

        url = f"{self.mcp_server_url}/mcp/call"
        payload = {'tool': 'list_models', 'params': {'category': 'all'}}

        concurrent_levels = [10, 50, 100]
        results = {}

        for level in concurrent_levels:
            logger.info(f"  Testing {level} concurrent requests...")
            try:
                result = await ThroughputTester.concurrent_requests(url, payload, level)
                results[f'concurrent_{level}'] = result
                logger.info(
                    f"    {level} concurrent: "
                    f"{result['successful']}/{level} successful, "
                    f"avg {result['latency'].get('mean_ms', 0):.2f}ms"
                )
            except Exception as e:
                logger.error(f"  Throughput test failed: {e}")

        return results

    async def run_memory_stability_test(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Test memory stability during repeated operations."""
        logger.info(f"Starting memory stability test ({duration_seconds}s)...")

        url = f"{self.mcp_server_url}/mcp/call"
        payload = {'tool': 'list_models', 'params': {'category': 'all'}}

        measurements = []
        start_time = time.perf_counter()
        request_count = 0

        while time.perf_counter() - start_time < duration_seconds:
            try:
                await LatencyMeasurement.measure_http_latency(url, 'POST', payload)
                request_count += 1

                if request_count % 10 == 0:
                    resources = self.profiler.measure_resources()
                    measurements.append(resources)
                    logger.debug(f"  Request {request_count}: Memory {resources['memory_mb']:.1f}MB")

                # Small delay to avoid overwhelming
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"Memory test request failed: {e}")

        if measurements:
            memory_values = [m['memory_mb'] for m in measurements]
            return {
                'duration_seconds': duration_seconds,
                'request_count': request_count,
                'measurements': len(measurements),
                'memory': {
                    'min_mb': min(memory_values),
                    'max_mb': max(memory_values),
                    'mean_mb': mean(memory_values),
                    'delta_mb': max(memory_values) - min(memory_values),
                },
                'stability': {
                    'memory_drift_mb': max(memory_values) - min(memory_values),
                    'is_stable': (max(memory_values) - min(memory_values)) < 50,  # < 50MB drift
                }
            }

        return {}

    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Execute all benchmark suites."""
        logger.info("=" * 80)
        logger.info("KYUTAI MCP SERVER PERFORMANCE BENCHMARKS")
        logger.info("=" * 80)

        all_results = {
            'environment': self.environment_info,
            'timestamp': datetime.now().isoformat(),
            'benchmarks': {}
        }

        # Run benchmark suites
        try:
            logger.info("\n[1/3] Server Latency Tests")
            all_results['benchmarks']['latency'] = await self.run_server_latency_tests()

            logger.info("\n[2/3] Throughput Tests")
            all_results['benchmarks']['throughput'] = await self.run_throughput_tests()

            logger.info("\n[3/3] Memory Stability Test")
            all_results['benchmarks']['memory_stability'] = await self.run_memory_stability_test()

        except Exception as e:
            logger.error(f"Benchmark execution failed: {e}")
            all_results['error'] = str(e)

        return all_results


async def main():
    """Main benchmark orchestration."""
    import argparse

    parser = argparse.ArgumentParser(description='Kyutai MCP Server Performance Benchmarks')
    parser.add_argument('--server-url', default='http://localhost:8000', help='MCP server URL')
    parser.add_argument('--output', default='/home/mike-anderson/vaults/cohezion-vault/benchmarks/metrics.json', help='Output file for metrics')
    parser.add_argument('--runs', type=int, default=10, help='Number of runs per test')

    args = parser.parse_args()

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    # Run benchmarks
    suite = BenchmarkSuite(mcp_server_url=args.server_url)
    results = await suite.run_all_benchmarks()

    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nResults saved to {args.output}")

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK SUMMARY")
    logger.info("=" * 80)

    if 'latency' in results['benchmarks']:
        logger.info("\nServer Latency:")
        for tool, metrics in results['benchmarks']['latency'].items():
            logger.info(
                f"  {tool}: mean={metrics.mean_ms:.2f}ms, "
                f"median={metrics.median_ms:.2f}ms, "
                f"p95={metrics.p95_ms:.2f}ms"
            )

    if 'throughput' in results['benchmarks']:
        logger.info("\nThroughput:")
        for level, metrics in results['benchmarks']['throughput'].items():
            logger.info(f"  {level}: {metrics['successful']}/{metrics['concurrent_count']} success")

    if 'memory_stability' in results['benchmarks']:
        mem = results['benchmarks']['memory_stability']
        if mem:
            logger.info(
                f"\nMemory Stability: "
                f"mean={mem['memory']['mean_mb']:.1f}MB, "
                f"drift={mem['memory']['delta_mb']:.1f}MB"
            )


if __name__ == '__main__':
    asyncio.run(main())
