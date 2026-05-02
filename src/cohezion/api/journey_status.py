"""API endpoints for 8-hour journey status.

Real-time journey status for dashboard integration.
Provides SSE streaming and REST endpoints for journey progress,
thermal status, and TDP budget.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from cohezion.compound.hardware_monitor import get_hardware_monitor


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/journey", tags=["journey"])


class JourneyStatusService:
    """Service for tracking 8-hour journey status."""

    def __init__(self):
        self.monitor = get_hardware_monitor()
        self.active_journeys: dict[str, dict] = {}

    def get_journey_status(self, journey_id: str) -> dict[str, Any]:
        """Get current status for a journey."""
        # Check for checkpoint file
        checkpoint_file = Path(f"data/thermal_checkpoints/{journey_id}.json")

        if checkpoint_file.exists():
            try:
                with open(checkpoint_file) as f:
                    checkpoint = json.load(f)

                # Get current thermal status
                metrics = self.monitor.get_current_metrics()

                return {
                    "journey_id": journey_id,
                    "exists": True,
                    "state": checkpoint.get("thermal_state", "unknown"),
                    "phase": checkpoint.get("phase", "unknown"),
                    "hypotheses_completed": checkpoint.get("hypotheses_completed", 0),
                    "total_hypotheses": checkpoint.get("total_hypotheses", 20),
                    "gpu_temp": metrics.gpu_temp_current,
                    "cpu_temp": metrics.cpu_temp_current,
                    "progress": checkpoint.get("progress", {}),
                    "last_updated": checkpoint.get("timestamp", time.time()),
                }
            except Exception as e:
                logger.error(f"Failed to read checkpoint: {e}")

        return {"journey_id": journey_id, "exists": False, "state": "not_found"}

    def list_active_journeys(self) -> list[dict[str, Any]]:
        """List all active journeys from checkpoints."""
        checkpoint_dir = Path("data/thermal_checkpoints")
        if not checkpoint_dir.exists():
            return []

        journeys = []
        for checkpoint_file in checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)

                journeys.append(
                    {
                        "journey_id": data.get("task_id", checkpoint_file.stem),
                        "phase": data.get("phase", "unknown"),
                        "hypotheses_completed": data.get("hypotheses_completed", 0),
                        "total_hypotheses": data.get("total_hypotheses", 0),
                        "state": data.get("thermal_state", "unknown"),
                        "last_updated": data.get("timestamp", 0),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read {checkpoint_file}: {e}")

        return journeys


# Singleton instance
journey_service = JourneyStatusService()


@router.get("/status/{journey_id}")
async def get_journey_status(journey_id: str) -> dict[str, Any]:
    """Get status for a specific journey."""
    return journey_service.get_journey_status(journey_id)


@router.get("/active")
async def list_active_journeys() -> list[dict[str, Any]]:
    """List all active journeys."""
    return journey_service.list_active_journeys()


@router.get("/stream/{journey_id}")
async def stream_journey_status(journey_id: str) -> StreamingResponse:
    """Stream real-time journey status via SSE."""

    async def event_generator():
        while True:
            try:
                status = journey_service.get_journey_status(journey_id)
                yield f"data: {json.dumps(status)}\n\n"

                # Sleep before next update
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"SSE error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/start")
async def start_journey(config: dict[str, Any]) -> dict[str, Any]:
    """Start a new 8-hour journey."""
    journey_id = f"8hr_{int(time.time())}"

    # Create initial checkpoint
    checkpoint_file = Path(f"data/thermal_checkpoints/{journey_id}.json")
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    initial_checkpoint = {
        "timestamp": time.time(),
        "task_id": journey_id,
        "phase": "starting",
        "progress": {},
        "thermal_state": "NORMAL",
        "hypotheses_completed": 0,
        "total_hypotheses": config.get("total_hypotheses", 20),
        "config": config,
    }

    async with aiofiles.open(checkpoint_file, "w") as f:
        await f.write(json.dumps(initial_checkpoint, indent=2))

    return {"journey_id": journey_id, "status": "started", "config": config}


@router.post("/pause/{journey_id}")
async def pause_journey(journey_id: str) -> dict[str, Any]:
    """Pause a running journey."""
    checkpoint_file = Path(f"data/thermal_checkpoints/{journey_id}.json")

    if not checkpoint_file.exists():
        raise HTTPException(status_code=404, detail="Journey not found")

    async with aiofiles.open(checkpoint_file) as f:
        data = json.loads(await f.read())

    data["thermal_state"] = "PAUSED"
    data["timestamp"] = time.time()

    async with aiofiles.open(checkpoint_file, "w") as f:
        await f.write(json.dumps(data, indent=2))

    return {"journey_id": journey_id, "status": "paused"}


@router.post("/resume/{journey_id}")
async def resume_journey(journey_id: str) -> dict[str, Any]:
    """Resume a paused journey."""
    checkpoint_file = Path(f"data/thermal_checkpoints/{journey_id}.json")

    if not checkpoint_file.exists():
        raise HTTPException(status_code=404, detail="Journey not found")

    async with aiofiles.open(checkpoint_file) as f:
        data = json.loads(await f.read())

    data["thermal_state"] = "NORMAL"
    data["timestamp"] = time.time()

    async with aiofiles.open(checkpoint_file, "w") as f:
        await f.write(json.dumps(data, indent=2))

    return {"journey_id": journey_id, "status": "resumed"}
