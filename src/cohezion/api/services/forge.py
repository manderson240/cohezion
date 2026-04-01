"""Forge API Service — Hardware telemetry and kernel benchmarks.

Exposes endpoints for real-time monitoring of the Strix Halo substrate
and submitting MXFP4 kernels via popcorn-cli.

Endpoints:
  GET  /forge/telemetry  — Real-time CPU/GPU/Memory metrics
  POST /forge/benchmark  — Run a popcorn-cli benchmark
  GET  /forge/leaderboard — Get local leaderboard of best kernels
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from cohezion.substrate import get_hardware_monitor, popcorn


logger = logging.getLogger(__name__)

forge_router = APIRouter(prefix="/forge", tags=["forge"])


# --- Request/Response Models ---

class HardwareTelemetry(BaseModel):
    cpu_temp: float = Field(..., description="CPU temperature in °C")
    gpu_temp: float = Field(..., description="GPU temperature in °C")
    cpu_power: float = Field(..., description="CPU power draw in Watts")
    gpu_power: float = Field(..., description="GPU power draw in Watts")
    memory_used_gb: float = Field(..., description="System memory used in GB")
    gpu_clock_mhz: float = Field(..., description="Current GPU clock speed")
    timestamp: float = Field(default_factory=time.time)


class BenchmarkRequest(BaseModel):
    kernel: str = Field(..., enum=["gemm", "moe", "mla"], description="Kernel type to benchmark")
    mode: str = Field("benchmark", enum=["test", "benchmark", "leaderboard"])


class BenchmarkResponse(BaseModel):
    passed: bool
    score_us: float
    kernel: str
    mode: str
    elapsed_s: float
    error: str | None = None
    stdout: str
    stderr: str


# --- Endpoints ---

@forge_router.get("/telemetry", response_model=HardwareTelemetry)
async def get_telemetry() -> HardwareTelemetry:
    """Get real-time hardware metrics from the Strix Halo substrate."""
    monitor = get_hardware_monitor()
    stats = monitor.get_stats()
    
    return HardwareTelemetry(
        cpu_temp=stats["current_cpu_temp_c"],
        gpu_temp=stats["current_gpu_temp_c"],
        cpu_power=stats["current_cpu_power_w"],
        gpu_power=stats["current_gpu_power_w"],
        memory_used_gb=stats["current_memory_used_gb"],
        gpu_clock_mhz=stats["gpu_clock_mhz"],
        timestamp=time.time()
    )


@forge_router.post("/benchmark", response_model=BenchmarkResponse)
async def run_benchmark(req: BenchmarkRequest) -> BenchmarkResponse:
    """Run an MXFP4 kernel benchmark on the local hardware."""
    # Find the submission file in the luma_speedrun directory
    # For now, we assume it's in a known location relative to the project root
    from pathlib import Path
    
    project_root = Path.cwd()
    luma_dir = project_root / "luma_speedrun"
    
    # Map kernel names to submission files
    submission_files = {
        "gemm": "amd-mxfp4-mm/submission.py",
        "moe": "amd-moe-mxfp4/submission.py",
        "mla": "amd-mixed-mla/submission.py",
    }
    
    submission_rel_path = submission_files.get(req.kernel)
    if not submission_rel_path:
        raise HTTPException(status_code=400, detail=f"Unsupported kernel: {req.kernel}")
        
    submission_path = luma_dir / submission_rel_path
    
    if not submission_path.exists():
        # Try finding it in the worktree if we're in a dev environment
        worktree_path = Path("/home/mike-anderson/dev/cohezion/.worktrees/spec-genesis-engine-395e48851")
        submission_path = worktree_path / "luma_speedrun" / submission_rel_path
        
    if not submission_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Submission file not found for {req.kernel} at {submission_path}"
        )

    logger.info(f"Running {req.mode} for {req.kernel} using {submission_path}")
    
    result = popcorn.submit(
        kernel=req.kernel,
        submission_path=submission_path,
        mode=req.mode
    )
    
    return BenchmarkResponse(
        passed=result.passed,
        score_us=result.score,
        kernel=result.kernel,
        mode=result.mode,
        elapsed_s=result.elapsed_s,
        error=result.error if not result.passed else None,
        stdout=result.stdout,
        stderr=result.stderr
    )


@forge_router.get("/leaderboard")
async def get_local_leaderboard(kernel: str = Query("gemm", enum=["gemm", "moe", "mla"])) -> list[dict[str, Any]]:
    """Get local benchmark history (mocked for now)."""
    # In a real implementation, this would query SurrealDB for past BenchmarkResponse objects
    return [
        {"timestamp": time.time() - 3600, "user": "mike-anderson", "score_us": 142.5, "passed": True},
        {"timestamp": time.time() - 7200, "user": "mike-anderson", "score_us": 145.2, "passed": True},
    ]
