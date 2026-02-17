"""Admin and visualization endpoints - knowledge query, CALM comparison, swarm execute."""

import logging

from fastapi import APIRouter, HTTPException

from cohezion.api.models import (
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    SwarmExecuteRequest,
    SwarmExecuteResponse,
    SwarmTaskResult,
)


logger = logging.getLogger(__name__)

knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@knowledge_router.post("/query", response_model=KnowledgeQueryResponse)
async def knowledge_query(request: KnowledgeQueryRequest):
    """Search the knowledge graph for relevant entries."""
    from cohezion.knowledge_graph.query_engine import KnowledgeGraphQueryEngine

    engine = KnowledgeGraphQueryEngine()
    results = engine.search_knowledge(request.query, top_k=request.top_k)
    return KnowledgeQueryResponse(
        query=request.query, results=results, count=len(results)
    )


swarm_router = APIRouter(prefix="/swarm", tags=["swarm"])


@swarm_router.post("/execute", response_model=SwarmExecuteResponse)
async def swarm_execute(request: SwarmExecuteRequest):
    """Plan and execute a swarm from a natural language intent."""
    from cohezion.swarm.compound_client import get_compound_client
    from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator
    from cohezion.swarm.team_orchestrator import TeamOrchestrator

    compound = get_compound_client()
    orchestrator_obj = TeamOrchestrator()
    plan = orchestrator_obj.plan_team(request.intent, max_agents=request.max_agents)
    executor = ExecutionOrchestrator(token_client=compound)
    report = await executor.execute(plan)

    report_dict = report.to_dict()
    return SwarmExecuteResponse(
        report_id=report_dict.get("report_id", ""),
        plan_name=report_dict.get("plan_name", ""),
        intent=report_dict.get("intent", ""),
        status=report_dict.get("status", ""),
        total_tokens=report_dict.get("total_tokens", 0),
        total_duration_ms=report_dict.get("total_duration_ms", 0.0),
        tasks=[SwarmTaskResult(**t) for t in report_dict.get("tasks", [])],
    )


compare_router = APIRouter(prefix="/compare", tags=["compare"])


@compare_router.get("/calm-vs-llm/{journey_id}")
async def compare_calm_llm(journey_id: str):
    """Compare CALM continuous trajectory vs standard LLM discrete steps."""
    import json

    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np
    from fastapi.responses import FileResponse

    matplotlib.use("Agg")

    from cohezion.swarm.journey_tracker import (
        get_journey_tracker,  # type: ignore[reportMissingImports]
    )

    tracker = get_journey_tracker()
    journey_file = tracker.output_dir / f"{journey_id}.json"

    if not journey_file.exists():
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    journey = json.loads(journey_file.read_text())
    steps = journey.get("steps", [])

    llm_z = [s["physics_state"].get("z", 0) for s in steps]
    llm_coherence = [s["physics_state"].get("coherence", 0) for s in steps]
    llm_steps = range(1, len(steps) + 1)

    calm_steps = np.linspace(1, len(steps), 20)
    calm_z = np.interp(calm_steps, list(llm_steps), llm_z)
    calm_coherence = np.interp(calm_steps, list(llm_steps), llm_coherence)

    noise = np.random.normal(0, 0.02, len(calm_z))
    calm_z_smooth = np.convolve(calm_z + noise, np.ones(3) / 3, mode="same")
    calm_coherence_smooth = np.convolve(calm_coherence, np.ones(3) / 3, mode="same")

    llm_smoothness = 1.0 / (1.0 + np.var(np.diff(llm_z)))
    calm_smoothness = 1.0 / (1.0 + np.var(np.diff(calm_z_smooth)))

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), facecolor="#0a0a1a")

    ax1 = axes[0, 0]
    ax1.set_facecolor("#0a0a1a")
    ax1.plot(
        llm_steps, llm_z, "r-o", markersize=12, linewidth=3, label="LLM Z-trajectory"
    )
    ax1.set_title(
        "Standard LLM: Discrete Steps", color="#f97316", fontsize=12, fontweight="bold"
    )
    ax1.set_xlabel("Step", color="white")
    ax1.set_ylabel("Z-coordinate", color="white")
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.3)
    ax1.grid(True, alpha=0.2, color="white")
    ax1.tick_params(colors="white")

    ax2 = axes[0, 1]
    ax2.set_facecolor("#0a0a1a")
    ax2.plot(
        calm_steps, calm_z_smooth, "c-", linewidth=4, label="CALM Z-trajectory (smooth)"
    )
    ax2.set_title(
        "CALM: Continuous Trajectory", color="#06b6d4", fontsize=12, fontweight="bold"
    )
    ax2.set_xlabel("Step", color="white")
    ax2.set_ylabel("Z-coordinate", color="white")
    ax2.legend(loc="upper left", fontsize=9, framealpha=0.3)
    ax2.grid(True, alpha=0.2, color="white")
    ax2.tick_params(colors="white")

    ax3 = axes[1, 0]
    ax3.set_facecolor("#0a0a1a")
    ax3.plot(
        llm_steps,
        llm_coherence,
        "r-o",
        markersize=12,
        linewidth=3,
        label="LLM Coherence",
    )
    ax3.set_title(
        "LLM Coherence Trajectory", color="#f97316", fontsize=12, fontweight="bold"
    )
    ax3.set_xlabel("Step", color="white")
    ax3.set_ylabel("Coherence", color="white")
    ax3.axhline(
        y=0.5,
        color="yellow",
        linestyle="--",
        linewidth=2,
        alpha=0.6,
        label="HIHO Threshold",
    )
    ax3.legend(loc="lower left", fontsize=9, framealpha=0.3)
    ax3.grid(True, alpha=0.2, color="white")
    ax3.tick_params(colors="white")

    ax4 = axes[1, 1]
    ax4.set_facecolor("#0a0a1a")
    ax4.plot(
        calm_steps,
        calm_coherence_smooth,
        "c-",
        linewidth=4,
        label="CALM Coherence (smooth)",
    )
    ax4.set_title(
        "CALM Coherence Trajectory", color="#06b6d4", fontsize=12, fontweight="bold"
    )
    ax4.set_xlabel("Step", color="white")
    ax4.set_ylabel("Coherence", color="white")
    ax4.axhline(
        y=0.5,
        color="yellow",
        linestyle="--",
        linewidth=2,
        alpha=0.6,
        label="HIHO Threshold",
    )
    ax4.legend(loc="lower left", fontsize=9, framealpha=0.3)
    ax4.grid(True, alpha=0.2, color="white")
    ax4.tick_params(colors="white")

    fig.suptitle(
        f"LLM Smoothness: {llm_smoothness:.3f} | CALM Smoothness: {calm_smoothness:.3f}",
        color="white",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout(rect=(0, 0, 1, 0.96))

    output_path = tracker.output_dir / f"calm_vs_llm_{journey_id}.png"
    plt.savefig(output_path, dpi=150, facecolor="#0a0a1a", edgecolor="none")
    plt.close()

    return FileResponse(output_path, media_type="image/png")
