"""Journey visualization endpoints."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cohezion.compound.journey_tracker import get_journey_tracker


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journeys", tags=["journeys"])


class JourneyCreateRequest(BaseModel):
    """Request to create a journey."""

    task_description: str
    operation_type: str
    session_id: str | None = None


class JourneySearchRequest(BaseModel):
    """Request to search for similar journeys."""

    task_description: str | None = None
    limit: int = 5
    use_256d: bool = True


@router.get("/journeys")
async def list_journeys(operation_type: str | None = None, limit: int = 20):
    """List recent agent journeys."""

    tracker = get_journey_tracker()

    if tracker.use_surreal:
        journeys = await tracker.get_recent_journeys(
            operation_type=operation_type, limit=limit
        )
        return {
            "journeys": [
                {
                    "journey_id": j.journey_id,
                    "task_description": j.task_description[:50],
                    "operation_type": j.operation_type,
                    "phi_score": j.phi_score,
                    "coherence_at_start": j.coherence_at_start,
                    "coherence_at_end": j.coherence_at_end,
                    "final_success": j.final_success,
                    "has_embedding_2048d": j.embedding_2048d is not None,
                    "has_flume_latent_256d": j.flume_latent_256d is not None,
                    "has_trajectory_12d": j.trajectory_12d is not None,
                }
                for j in journeys
            ]
        }

    return {"journeys": [], "message": "SurrealDB not available, using legacy mode"}


@router.post("/journeys")
async def create_journey(request: JourneyCreateRequest):
    """Create a new unified journey with full trajectory."""
    from cohezion.compound.executor_types import ExecutionResult

    tracker = get_journey_tracker()

    mock_result = ExecutionResult(
        id=f"exec_{request.task_description[:8]}",
        success=True,
        output=f"Output for: {request.task_description}",
        duration_seconds=1.0,
        metrics={"coherence": 0.8},
        token_metrics={"cache_hit_rate": 0.7},
    )

    journey = await tracker.record_journey(
        execution_result=mock_result,
        task_description=request.task_description,
        operation_type=request.operation_type,
        session_id=request.session_id,
        coherence_at_start=0.5,
        decisions=[],
        actions=[],
        outcome="completed",
    )

    return {
        "journey_id": journey.journey_id,
        "execution_id": journey.execution_id,
        "phi_score": journey.phi_score,
        "embedding_2048d_dim": len(journey.embedding_2048d)
        if journey.embedding_2048d
        else 0,
        "flume_latent_256d_dim": len(journey.flume_latent_256d)
        if journey.flume_latent_256d
        else 0,
        "trajectory_12d_dim": len(journey.trajectory_12d)
        if journey.trajectory_12d
        else 0,
    }


@router.post("/journeys/search")
async def search_similar_journeys(request: JourneySearchRequest):
    """Search for similar journeys using vector similarity."""

    tracker = get_journey_tracker()

    if not tracker.use_surreal:
        return {"journeys": [], "message": "SurrealDB not available"}

    similar = await tracker.find_similar_journeys(
        task_description=request.task_description,
        limit=request.limit,
        use_256d=request.use_256d,
    )

    return {
        "journeys": [
            {
                "journey_id": j.get("journey_id"),
                "task_description": j.get("task_description", "")[:50],
                "operation_type": j.get("operation_type"),
                "phi_score": j.get("phi_score"),
                "score": j.get("score"),
            }
            for j in similar
        ]
    }


@router.get("/{journey_id}")
async def get_journey(journey_id: str):
    """Get a specific journey with full trajectory."""

    tracker = get_journey_tracker()

    if tracker.use_surreal:
        journey = await tracker.get_journey(journey_id)
        if journey:
            return {
                "journey_id": journey.journey_id,
                "execution_id": journey.execution_id,
                "session_id": journey.session_id,
                "task_description": journey.task_description,
                "operation_type": journey.operation_type,
                "coherence_at_start": journey.coherence_at_start,
                "coherence_at_end": journey.coherence_at_end,
                "phi_score": journey.phi_score,
                "final_success": journey.final_success,
                "embedding_2048d": journey.embedding_2048d,
                "flume_latent_256d": journey.flume_latent_256d,
                "trajectory_12d": journey.trajectory_12d,
                "decisions_made": journey.decisions_made,
                "actions_taken": journey.actions_taken,
                "outcome": journey.outcome,
                "metadata": journey.metadata,
            }

    raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")


@router.get("/{journey_id}/trajectory")
async def get_journey_trajectory(journey_id: str):
    """Get physics trajectory for visualization."""

    tracker = get_journey_tracker()
    trajectory = tracker.get_journey_trajectory(journey_id)
    if not trajectory:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")
    return {"trajectory": trajectory}


@router.post("/demo")
async def create_demo_journey():
    """Create a demo journey to showcase visualization."""
    import random

    from cohezion.compound.journey_tracker import AgentType

    tracker = get_journey_tracker()
    tracker.start_journey("What is the meaning of consciousness?")

    analyst_states = [
        {
            "x": random.uniform(-0.3, 0.1),
            "y": random.uniform(0.2, 0.5),
            "z": random.uniform(0.3, 0.5),
            "time": 0.1,
            "mass": random.uniform(0.7, 0.85),
            "sentiment": random.uniform(0.4, 0.6),
            "complexity": random.uniform(0.7, 0.9),
            "factuality": random.uniform(0.8, 0.95),
            "connectivity": random.uniform(0.3, 0.5),
            "stability": random.uniform(0.6, 0.8),
            "novelty": random.uniform(0.5, 0.7),
            "coherence": random.uniform(0.7, 0.85),
        },
        {
            "x": random.uniform(0.1, 0.4),
            "y": random.uniform(-0.3, 0.1),
            "z": random.uniform(0.4, 0.6),
            "time": 0.2,
            "mass": random.uniform(0.65, 0.8),
            "sentiment": random.uniform(0.5, 0.8),
            "complexity": random.uniform(0.5, 0.7),
            "factuality": random.uniform(0.6, 0.8),
            "connectivity": random.uniform(0.4, 0.6),
            "stability": random.uniform(0.5, 0.7),
            "novelty": random.uniform(0.6, 0.8),
            "coherence": random.uniform(0.65, 0.8),
        },
        {
            "x": random.uniform(-0.4, -0.1),
            "y": random.uniform(-0.2, 0.2),
            "z": random.uniform(0.35, 0.55),
            "time": 0.3,
            "mass": random.uniform(0.6, 0.75),
            "sentiment": random.uniform(0.3, 0.5),
            "complexity": random.uniform(0.6, 0.8),
            "factuality": random.uniform(0.7, 0.9),
            "connectivity": random.uniform(0.5, 0.7),
            "stability": random.uniform(0.7, 0.85),
            "novelty": random.uniform(0.3, 0.5),
            "coherence": random.uniform(0.7, 0.85),
        },
    ]

    for _i, (perspective, state) in enumerate(
        zip(["technical", "ethical", "historical"], analyst_states, strict=False)
    ):
        tracker.record_step(
            agent_type=AgentType.ANALYST,
            agent_name=f"analyst_{perspective}",
            perspective=perspective,
            input_text="What is the meaning of consciousness?",
            output_text=f"{perspective.title()} analysis of consciousness...",
            physics_state=state,
            duration_ms=random.uniform(200, 500),
            confidence=random.uniform(0.7, 0.9),
        )

    tracker.record_step(
        agent_type=AgentType.CRITIC,
        agent_name="critic_phi3",
        perspective=None,
        input_text="Three analyst perspectives on consciousness",
        output_text="Critique: Found 2 contradictions between perspectives...",
        physics_state={
            "x": 0.0,
            "y": 0.0,
            "z": 0.75,
            "time": 0.6,
            "mass": 0.9,
            "sentiment": 0.5,
            "complexity": 0.8,
            "factuality": 0.95,
            "connectivity": 0.8,
            "stability": 0.85,
            "novelty": 0.25,
            "coherence": 0.9,
        },
        duration_ms=350,
        confidence=0.88,
    )

    tracker.record_step(
        agent_type=AgentType.SYNTHESIZER,
        agent_name="synthesizer_mistral",
        perspective=None,
        input_text="Analyst outputs + critique",
        output_text="Synthesized understanding of consciousness integrating all perspectives...",
        physics_state={
            "x": 0.0,
            "y": 0.0,
            "z": 1.0,
            "time": 1.0,
            "mass": 1.0,
            "sentiment": 0.65,
            "complexity": 0.75,
            "factuality": 0.9,
            "connectivity": 0.95,
            "stability": 0.95,
            "novelty": 0.4,
            "coherence": 0.98,
        },
        duration_ms=400,
        confidence=0.92,
    )

    journey = tracker.end_journey(
        final_response="Consciousness is an emergent property...",
        final_confidence=0.92,
    )

    return {"journey_id": journey.journey_id, "steps": len(journey.steps)}


@router.get("/{journey_id}/visualize")
async def visualize_journey(journey_id: str):
    """Render an animated visualization of the journey trajectory."""

    from cohezion.compound.journey_tracker import get_journey_tracker
    from cohezion.viz.hypertools_renderer import HyperToolsViz

    tracker = get_journey_tracker()
    journey_file = tracker.output_dir / f"{journey_id}.json"

    if not journey_file.exists():
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    journey = json.loads(journey_file.read_text())

    trajectory_data = []
    for step in journey.get("steps", []):
        ps = step.get("physics_state", {})
        vec = [
            ps.get("x", 0),
            ps.get("y", 0),
            ps.get("z", 0),
            ps.get("mass", 0.5),
            ps.get("coherence", 0.5),
            ps.get("novelty", 0.5),
        ]
        trajectory_data.append(vec)

    if len(trajectory_data) < 2:
        raise HTTPException(
            status_code=400, detail="Journey needs at least 2 steps for visualization"
        )

    import numpy as np

    trajectory = np.array(trajectory_data)

    viz = HyperToolsViz(output_dir=Path("renders"))
    output_path = viz.animate_trajectory(
        trajectory,
        output_name=f"journey_{journey_id}",
        fps=2,
    )

    return FileResponse(
        output_path,
        media_type="image/gif",
        filename=f"{journey_id}_trajectory.gif",
    )


@router.get("/{journey_id}/plot")
async def plot_journey(journey_id: str):
    """Render a multi-panel 12D physics visualization of the journey."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from cohezion.compound.journey_tracker import get_journey_tracker

    tracker = get_journey_tracker()
    journey_file = tracker.output_dir / f"{journey_id}.json"

    if not journey_file.exists():
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    journey = json.loads(journey_file.read_text())
    steps = journey.get("steps", [])

    dims = [
        "x",
        "y",
        "z",
        "time",
        "mass",
        "sentiment",
        "complexity",
        "factuality",
        "connectivity",
        "stability",
        "novelty",
        "coherence",
    ]

    physics_data = {d: [s["physics_state"].get(d, 0) for s in steps] for d in dims}
    agent_types = [s.get("agent_type", "unknown") for s in steps]

    colors = {"analyst": "#818cf8", "critic": "#f97316", "synthesizer": "#22c55e"}
    point_colors = [colors.get(t, "#888888") for t in agent_types]

    fig = plt.figure(figsize=(16, 12), facecolor="#0a0a1a")

    ax3d = fig.add_subplot(2, 3, 1, projection="3d")
    ax3d.set_facecolor("#0a0a1a")
    ax3d.plot(
        physics_data["x"],
        physics_data["y"],
        physics_data["z"],
        "w-",
        alpha=0.4,
        linewidth=2,
    )
    for i, (x, y, z, c) in enumerate(
        zip(
            physics_data["x"],
            physics_data["y"],
            physics_data["z"],
            point_colors,
            strict=False,
        )
    ):
        ax3d.scatter(
            [x], [y], [z], c=c, s=150, alpha=0.9, edgecolors="white", linewidths=1
        )
        ax3d.text(x, y, z, f" {i + 1}", color="white", fontsize=8)
    ax3d.set_xlabel("X", color="white")
    ax3d.set_ylabel("Y", color="white")
    ax3d.set_zlabel("Z", color="white")
    ax3d.set_title("Spatial Trajectory (X,Y,Z)", color="white", fontsize=10)
    ax3d.tick_params(colors="white", labelsize=7)

    ax_mass = fig.add_subplot(2, 3, 2, facecolor="#0a0a1a")
    step_nums = range(1, len(steps) + 1)
    ax_mass.bar(
        step_nums, physics_data["mass"], color=point_colors, alpha=0.8, label="Mass"
    )
    ax_mass.plot(step_nums, physics_data["time"], "w-o", markersize=6, label="Time")
    ax_mass.set_xlabel("Step", color="white")
    ax_mass.set_ylabel("Value", color="white")
    ax_mass.set_title("Mass & Time Evolution", color="white", fontsize=10)
    ax_mass.legend(facecolor="#1a1a2e", labelcolor="white", fontsize=8)
    ax_mass.tick_params(colors="white")
    ax_mass.set_ylim(0, 1.1)

    ax_coh = fig.add_subplot(2, 3, 3, facecolor="#0a0a1a")
    ax_coh.fill_between(
        step_nums, physics_data["coherence"], alpha=0.3, color="#22c55e"
    )
    ax_coh.plot(
        step_nums,
        physics_data["coherence"],
        "g-o",
        markersize=8,
        label="Coherence",
        linewidth=2,
    )
    ax_coh.fill_between(
        step_nums, physics_data["stability"], alpha=0.2, color="#818cf8"
    )
    ax_coh.plot(
        step_nums, physics_data["stability"], "b-s", markersize=6, label="Stability"
    )
    ax_coh.set_xlabel("Step", color="white")
    ax_coh.set_ylabel("Value", color="white")
    ax_coh.set_title("Coherence & Stability", color="white", fontsize=10)
    ax_coh.legend(facecolor="#1a1a2e", labelcolor="white", fontsize=8)
    ax_coh.tick_params(colors="white")
    ax_coh.set_ylim(0, 1.1)

    ax_nov = fig.add_subplot(2, 3, 4, facecolor="#0a0a1a")
    ax_nov.plot(
        step_nums,
        physics_data["novelty"],
        "r-o",
        markersize=8,
        label="Novelty",
        linewidth=2,
    )
    ax_nov.plot(
        step_nums,
        physics_data["connectivity"],
        "c-^",
        markersize=6,
        label="Connectivity",
    )
    ax_nov.set_xlabel("Step", color="white")
    ax_nov.set_ylabel("Value", color="white")
    ax_nov.set_title("Novelty & Connectivity", color="white", fontsize=10)
    ax_nov.legend(facecolor="#1a1a2e", labelcolor="white", fontsize=8)
    ax_nov.tick_params(colors="white")
    ax_nov.set_ylim(0, 1.1)

    ax_sent = fig.add_subplot(2, 3, 5, facecolor="#0a0a1a")
    width = 0.25
    x = np.array(list(step_nums))
    ax_sent.bar(
        x - width,
        physics_data["sentiment"],
        width,
        label="Sentiment",
        color="#f97316",
        alpha=0.8,
    )
    ax_sent.bar(
        x,
        physics_data["complexity"],
        width,
        label="Complexity",
        color="#a78bfa",
        alpha=0.8,
    )
    ax_sent.bar(
        x + width,
        physics_data["factuality"],
        width,
        label="Factuality",
        color="#22d3ee",
        alpha=0.8,
    )
    ax_sent.set_xlabel("Step", color="white")
    ax_sent.set_ylabel("Value", color="white")
    ax_sent.set_title("Sentiment, Complexity, Factuality", color="white", fontsize=10)
    ax_sent.legend(facecolor="#1a1a2e", labelcolor="white", fontsize=7)
    ax_sent.tick_params(colors="white")
    ax_sent.set_ylim(0, 1.1)

    ax_heat = fig.add_subplot(2, 3, 6, facecolor="#0a0a1a")
    heatmap_data = np.array([physics_data[d] for d in dims])
    im = ax_heat.imshow(heatmap_data, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax_heat.set_yticks(range(len(dims)))
    ax_heat.set_yticklabels([d.capitalize() for d in dims], fontsize=8, color="white")
    ax_heat.set_xticks(range(len(steps)))
    ax_heat.set_xticklabels([f"{i + 1}" for i in range(len(steps))], color="white")
    ax_heat.set_xlabel("Step", color="white")
    ax_heat.set_title("12D Physics Heatmap", color="white", fontsize=10)
    cbar = plt.colorbar(im, ax=ax_heat, shrink=0.8)
    cbar.ax.yaxis.set_tick_params(color="white")
    cbar.ax.yaxis.set_ticklabels([f"{x:.1f}" for x in cbar.get_ticks()], color="white")

    fig.suptitle(
        f"12D Physics Journey: {journey['query'][:50]}...",
        color="white",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor=colors["analyst"], label="Analyst"),
        Patch(facecolor=colors["critic"], label="Critic"),
        Patch(facecolor=colors["synthesizer"], label="Synthesizer"),
    ]
    fig.legend(
        handles=legend_elements,
        loc="lower center",
        ncol=3,
        facecolor="#1a1a2e",
        labelcolor="white",
        fontsize=9,
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    output_dir = Path("renders")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"journey_{journey_id}_12d_plot.png"
    plt.savefig(output_path, dpi=150, facecolor="#0a0a1a", bbox_inches="tight")
    plt.close()

    return FileResponse(
        output_path,
        media_type="image/png",
        filename=f"{journey_id}_12d_plot.png",
    )
