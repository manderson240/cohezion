# ruff: noqa: B904  # raise pattern in HTTP/API handlers — explicit user-facing errors
"""Journey API - REST endpoints for journey retrieval and analysis.

Provides HTTP API for:
- List journeys with summary metadata
- Get full journey with trajectory
- Run analysis on selected journeys
- Get thermodynamic state for journey
- Get topological summary for journey

Architecture:
    GET /api/journeys → list_journeys()
    GET /api/journeys/{id} → get_journey()
    POST /api/journeys/analyze → analyze_journeys()
    GET /api/journeys/{id}/thermodynamics → journey_thermodynamics()
    GET /api/journeys/{id}/topology → journey_topology()

Integration:
    - Reads data/universe/*.json files
    - Calls JourneyAnalyzer for analysis
    - Calls JourneyTracker.compute_* methods
    - Returns JSON responses
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journeys", tags=["journeys"])

# Journey data directory
JOURNEY_DIR = Path("data/universe")


def load_journey(journey_id: str) -> dict[str, Any] | None:
    """Load single journey by ID.

    Args:
        journey_id: Journey ID (e.g., "journey_1773365054_936d9624")

    Returns:
        Journey dictionary or None
    """
    journey_file = JOURNEY_DIR / f"{journey_id}.json"
    if not journey_file.exists():
        return None

    with open(journey_file) as f:
        return json.load(f)


def load_all_journeys() -> list[dict[str, Any]]:
    """Load all journeys from data directory.

    Returns:
        List of journey dictionaries
    """
    if not JOURNEY_DIR.exists():
        logger.warning("Journey directory does not exist: %s", JOURNEY_DIR)
        return []

    journeys = []
    for json_file in JOURNEY_DIR.glob("journey_*.json"):
        try:
            with open(json_file) as f:
                journey = json.load(f)
                journeys.append(journey)
        except Exception as e:
            logger.error("Failed to load journey %s: %s", json_file.name, e)

    return journeys


@router.get("")
async def list_journeys(
    limit: int = Query(100, description="Maximum journeys to return"),
    status: str | None = Query(None, description="Filter by status"),
) -> list[dict[str, Any]]:
    """List all journeys with summary metadata.

    Args:
        limit: Maximum number of journeys to return
        status: Optional status filter ("active", "completed", "failed")

    Returns:
        List of journey summaries
    """
    all_journeys = load_all_journeys()

    # Filter by status if provided
    if status:
        all_journeys = [j for j in all_journeys if j.get("status") == status]

    # Limit and return summaries
    journeys = all_journeys[:limit]
    summaries = []
    for j in journeys:
        summary = {
            "id": j.get("id"),
            "agent_name": j.get("agent_name"),
            "intent": j.get("intent"),
            "status": j.get("status"),
            "final_coherence": j.get("final_coherence"),
            "final_phi_score": j.get("final_phi_score"),
            "trajectory_length": len(j.get("trajectory", [])),
        }
        summaries.append(summary)

    return summaries


@router.get("/{journey_id}")
async def get_journey(journey_id: str) -> dict[str, Any]:
    """Get full journey with trajectory.

    Args:
        journey_id: Journey ID

    Returns:
        Full journey with trajectory

    Raises:
        HTTPException: If journey not found
    """
    journey = load_journey(journey_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    return journey


@router.post("/analyze")
async def analyze_journeys(
    journey_ids: list[str],
    analysis_type: str = Query("all", description="Analysis type"),
) -> dict[str, Any]:
    """Run analysis on selected journeys.

    Args:
        journey_ids: List of journey IDs to analyze
        analysis_type: Type of analysis ("clustering", "thermodynamics", "topology", "all")

    Returns:
        Analysis results

    Raises:
        HTTPException: If analysis fails
    """
    try:
        from cohezion.compound.journey_analyzer import JourneyAnalyzer

        # Load selected journeys
        journeys = []
        for jid in journey_ids:
            journey = load_journey(jid)
            if journey:
                journeys.append(journey)

        if not journeys:
            raise HTTPException(status_code=404, detail="No journeys found")

        # Run analysis
        analyzer = JourneyAnalyzer()

        results: dict[str, Any] = {
            "n_journeys": len(journeys),
            "analysis_type": analysis_type,
        }

        if analysis_type in ("clustering", "all"):
            clustering = analyzer.cluster_journeys(journeys)
            results["clustering"] = {
                "n_clusters": clustering.n_clusters,
                "silhouette_score": clustering.silhouette_score,
                "algorithm": clustering.algorithm,
                "cluster_sizes": clustering.cluster_sizes,
            }

        if analysis_type in ("archetypes", "all"):
            archetypes = analyzer.compute_archetypes(journeys)
            results["archetypes"] = [
                {
                    "archetype": a.archetype.value,
                    "confidence": a.confidence,
                    "population_fraction": a.population_fraction,
                }
                for a in archetypes
            ]

        if analysis_type in ("thermodynamics", "all"):
            thermo_results = [analyzer.analyze_thermodynamics(j) for j in journeys]
            results["thermodynamics"] = {
                "mean_entropy_production": float(
                    sum(t.entropy_production_rate for t in thermo_results) / len(thermo_results)
                ),
                "mean_free_energy": float(
                    sum(t.free_energy for t in thermo_results) / len(thermo_results)
                ),
                "n_attractors": sum(1 for t in thermo_results if t.is_attractor),
            }

        if analysis_type in ("topology", "all"):
            topo_results = [analyzer.analyze_topology(j) for j in journeys]
            results["topology"] = {
                "mean_n_clusters": float(
                    sum(t.n_clusters for t in topo_results) / len(topo_results)
                ),
                "mean_n_loans": float(sum(t.n_loans for t in topo_results) / len(topo_results)),
            }

        return results

    except ImportError as e:
        logger.error("Analysis import failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e
    except Exception as e:
        logger.error("Analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@router.get("/{journey_id}/thermodynamics")
async def journey_thermodynamics(journey_id: str) -> dict[str, Any]:
    """Get thermodynamic state for journey.

    Args:
        journey_id: Journey ID

    Returns:
        Thermodynamic state

    Raises:
        HTTPException: If journey not found or analysis fails
    """
    journey = load_journey(journey_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    try:
        from cohezion.compound.journey_analyzer import JourneyAnalyzer

        analyzer = JourneyAnalyzer()
        thermo = analyzer.analyze_thermodynamics(journey)

        return {
            "journey_id": journey_id,
            "entropy_production_rate": thermo.entropy_production_rate,
            "free_energy": thermo.free_energy,
            "effective_temperature": thermo.effective_temperature,
            "susceptibility": thermo.susceptibility,
            "heat_capacity": thermo.heat_capacity,
            "is_attractor": thermo.is_attractor,
            "well_depth": thermo.well_depth,
            "basin_width": thermo.basin_width,
        }
    except Exception as e:
        logger.error("Thermodynamic analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@router.get("/{journey_id}/topology")
async def journey_topology(journey_id: str) -> dict[str, Any]:
    """Get topological summary for journey.

    Args:
        journey_id: Journey ID

    Returns:
        Topological summary

    Raises:
        HTTPException: If journey not found or analysis fails
    """
    journey = load_journey(journey_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    try:
        from cohezion.compound.journey_analyzer import JourneyAnalyzer

        analyzer = JourneyAnalyzer()
        topo = analyzer.analyze_topology(journey)

        return {
            "journey_id": journey_id,
            "n_clusters": topo.n_clusters,
            "n_loans": topo.n_loans,
            "persistence_entropy_h0": topo.persistence_entropy_h0,
            "persistence_entropy_h1": topo.persistence_entropy_h1,
            "topological_complexity": topo.topological_complexity,
        }
    except Exception as e:
        logger.error("Topological analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@router.get("/{journey_id}/anomaly")
async def journey_anomaly(journey_id: str) -> dict[str, Any]:
    """Get anomaly detection report for journey.

    Args:
        journey_id: Journey ID

    Returns:
        Anomaly report

    Raises:
        HTTPException: If journey not found or analysis fails
    """
    journey = load_journey(journey_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    try:
        from cohezion.compound.journey_analyzer import JourneyAnalyzer

        analyzer = JourneyAnalyzer()
        anomaly = analyzer.detect_anomalies(journey)

        return {
            "journey_id": journey_id,
            "anomaly_score": anomaly.anomaly_score,
            "is_anomaly": anomaly.is_anomaly,
            "anomaly_type": anomaly.anomaly_type,
            "severity": anomaly.severity,
            "contributing_factors": anomaly.contributing_factors,
        }
    except Exception as e:
        logger.error("Anomaly detection failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@router.get("/{journey_id}/archetype")
async def journey_archetype(journey_id: str) -> dict[str, Any]:
    """Get archetype classification for journey.

    Args:
        journey_id: Journey ID

    Returns:
        Archetype classification

    Raises:
        HTTPException: If journey not found or analysis fails
    """
    journey = load_journey(journey_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")

    try:
        from cohezion.compound.journey_analyzer import JourneyAnalyzer

        analyzer = JourneyAnalyzer()
        archetypes = analyzer.compute_archetypes([journey])

        if not archetypes:
            raise HTTPException(status_code=500, detail="Archetype analysis failed")

        archetype = archetypes[0]
        return {
            "journey_id": journey_id,
            "archetype": archetype.archetype.value,
            "confidence": archetype.confidence,
            "characteristics": archetype.characteristics,
            "population_fraction": archetype.population_fraction,
        }
    except Exception as e:
        logger.error("Archetype analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e
