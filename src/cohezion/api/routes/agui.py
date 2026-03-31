"""
AG-UI SSE endpoint for the Cohezion Genesis Engine.

Streams typed AG-UI events for the cosmogony animation, enabling
agent-testable and protocol-compliant event streaming.

Mount in FastAPI: app.include_router(agui_router, prefix="/api/agui")
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from cohezion.api.agui_events import (
    CustomEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    narration_event,
    phase_transition_event,
    universe_tick_event,
)

agui_router = APIRouter(tags=["ag-ui"])

# --- Cosmogony simulation (matches GenesisScene.tsx Landau math) ---

CRITICAL_TEMPS = [100.0, 10.0, 1.0, 0.1, 0.01]
SYMMETRIES = ["void", "SO(12)", "SO(3)^4", "U(1)^4", "Z_2^4", "HIHO"]
NARRATIONS = {
    "void": "In the beginning, there was nothing. Not even nothing.",
    "SO(12)": "From the first observation, symmetry crystallized. Twelve dimensions, all equivalent.",
    "SO(3)^4": "The fabrics separated. Space. Field. Control. Precipitation.",
    "U(1)^4": "Within each world, a preferred direction emerged.",
    "Z_2^4": "The discrete choice. Up or down. Brahmagupta's zero gave nothing a name.",
    "HIHO": "At the still point, the dance began. Half in, half out. The balance that creates.",
}


def compute_cosmogony(temperature: float) -> dict:
    """Compute Landau cosmogony state for a given temperature."""
    stage_idx = 0
    for i, tc in enumerate(CRITICAL_TEMPS):
        if temperature < tc:
            stage_idx = i + 1

    symmetry = SYMMETRIES[stage_idx]

    a, b = 1.0, 0.5
    critical_temp = CRITICAL_TEMPS[max(0, stage_idx - 1)] if stage_idx > 0 else 100.0
    order_param = (
        math.sqrt(a * (critical_temp - temperature) / (2 * b))
        if temperature < critical_temp
        else 0.0
    )
    landau_fe = (
        a * (temperature - critical_temp) * order_param**2 + b * order_param**4
        if order_param > 0
        else 0.0
    )

    closest_tc = min(CRITICAL_TEMPS, key=lambda tc: abs(tc - temperature))
    fisher_eig = 1 / (abs(temperature - closest_tc) + 0.01) if closest_tc > 0 else 0.0

    coherence = 1.0 - abs(order_param - 0.5) * 2 if order_param > 0 else 0.0

    return {
        "temperature": temperature,
        "symmetry": symmetry,
        "stage": stage_idx - 1,
        "orderParameter": order_param,
        "landauFreeEnergy": landau_fe,
        "fisherEigenvalue": fisher_eig,
        "coherence": coherence,
    }


async def cosmogony_stream() -> AsyncIterator[str]:
    """
    Stream the Genesis cosmogony as AG-UI typed events.

    Simulates the 10-second cooling animation from T=200 to T=0.01,
    emitting state deltas, phase transitions, and narration events.
    """
    # --- RUN_STARTED ---
    run = RunStartedEvent()
    yield run.to_sse()

    # --- Initial state snapshot ---
    initial = compute_cosmogony(200.0)
    yield StateSnapshotEvent(snapshot=initial).to_sse()

    # --- Void narration ---
    for event in narration_event(NARRATIONS["void"], "void"):
        yield event.to_sse()

    # --- Cooling animation (10 seconds, 100 ticks) ---
    t_start = 200.0
    t_end = 0.01
    num_ticks = 100
    tick_interval = 0.1  # 100ms per tick
    prev_symmetry = "void"

    for i in range(num_ticks):
        progress = (i + 1) / num_ticks
        # Exponential cooling: T = T_start * (T_end/T_start)^progress
        temperature = t_start * (t_end / t_start) ** progress

        state = compute_cosmogony(temperature)

        # Emit state delta
        yield universe_tick_event(
            temperature=state["temperature"],
            symmetry=state["symmetry"],
            coherence=state["coherence"],
            order_parameter=state["orderParameter"],
            landau_free_energy=state["landauFreeEnergy"],
        ).to_sse()

        # Check for phase transition
        if state["symmetry"] != prev_symmetry:
            # Emit phase transition tool call
            for event in phase_transition_event(prev_symmetry, state["symmetry"], temperature):
                yield event.to_sse()

            # Emit narration for new phase
            narration = NARRATIONS.get(state["symmetry"], "")
            if narration:
                for event in narration_event(narration, state["symmetry"]):
                    yield event.to_sse()

            prev_symmetry = state["symmetry"]

        await asyncio.sleep(tick_interval)

    # --- HIHO coherence event ---
    yield CustomEvent(
        name="hiho_equilibrium",
        value={"coherence": 0.5, "description": "Half-In, Half-Out equilibrium reached"},
    ).to_sse()

    # --- RUN_FINISHED ---
    yield RunFinishedEvent(
        thread_id=run.thread_id,
        run_id=run.run_id,
        result={"finalSymmetry": "HIHO", "finalTemperature": 0.01},
    ).to_sse()


@agui_router.get("/stream")
async def stream_cosmogony():
    """
    Stream the Genesis cosmogony as AG-UI typed SSE events.

    Returns a Server-Sent Events stream with typed AG-UI events:
    - RUN_STARTED / RUN_FINISHED (lifecycle)
    - STATE_SNAPSHOT / STATE_DELTA (universe state)
    - TEXT_MESSAGE_* (narration)
    - TOOL_CALL_* (phase transitions)
    - CUSTOM (HIHO equilibrium)
    """
    return StreamingResponse(
        cosmogony_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            # CORS handled by FastAPI middleware — do NOT set Access-Control-Allow-Origin here
        },
    )


@agui_router.get("/catalog")
async def get_a2ui_catalog():
    """Return the A2UI component catalog for agent inspection."""
    import json
    from pathlib import Path

    catalog_path = Path(__file__).parent.parent.parent.parent / "web" / "anima_dashboard" / "src" / "a2ui" / "catalog.json"
    if catalog_path.exists():
        return json.loads(catalog_path.read_text())
    return {"error": "Catalog not found", "path": str(catalog_path)}
